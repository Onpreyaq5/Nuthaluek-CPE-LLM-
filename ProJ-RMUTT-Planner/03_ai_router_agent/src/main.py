"""main.py — FastAPI service: AI Router / Agent  (port 8100)

Endpoints:
  GET  /health      -> liveness probe (Docker HEALTHCHECK)
  POST /chat        -> SSE stream: intent classification + planner + context for Module 07
  POST /classify    -> debug: return classification result only (no tool calls)
"""
from __future__ import annotations
import json
import logging
import time
import uuid
from typing import AsyncGenerator

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from sse_starlette.sse import EventSourceResponse

from .config import settings
from .models import RouterRequest, SSEEvent
from .classifier import classify, missing_slots, SLOT_QUESTIONS
from .planner import run_planner

logging.basicConfig(
    level=settings.log_level,
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)
logger = logging.getLogger(__name__)

app = FastAPI(title="03_ai_router_agent", version="0.1.0")


# ──────────────────────────────────────────────────────────────
#  Health check
# ──────────────────────────────────────────────────────────────

@app.get("/health")
def health():
    return {"ok": True, "service": "03_ai_router_agent"}


# ──────────────────────────────────────────────────────────────
#  POST /chat  — main SSE endpoint
# ──────────────────────────────────────────────────────────────

@app.post("/chat")
async def chat(req: RouterRequest):
    """
    Stream SSE events back to Module 02 (API/Backend).
    Event types: tool_start | tool_end | sources | router_result | clarify | done | error

    FROM DL-06: decision + routing + logging per request.
    NOT IN DL-06: SSE streaming format, slot-asking, guardrails emitted as events.
    """
    request_id = str(uuid.uuid4())[:8]

    async def event_stream() -> AsyncGenerator[dict, None]:
        t0 = time.perf_counter()
        try:
            # ── Step 1: Intent Classification ─────────────────────────
            classification = classify(req.message, [m.model_dump() for m in req.history])

            yield _sse("router_result", {
                "request_id": request_id,
                "intent": classification.intent,
                "confidence": classification.confidence,
                "reasoning": classification.reasoning,
                "source": classification.source,
                "slots": classification.slots.model_dump(),
            })

            # ── Step 2: Slot check — ask back if required slot missing ─
            # NOT IN DL-06
            missing = missing_slots(classification.intent, classification.slots)
            if missing:
                question = SLOT_QUESTIONS.get(missing[0], "ช่วยระบุข้อมูลเพิ่มเติมได้ไหมครับ?")
                yield _sse("clarify", {"question": question, "missing_slots": missing})
                yield _sse("done", {"latency_ms": _ms(t0)})
                return

            # ── Step 3: Planner Loop (tool execution + guardrails) ─────
            router_resp, sse_events = await run_planner(req, classification)

            for event in sse_events:
                yield _sse(event.type, event.data)

            # ── Step 4: Forward assembled context to Module 07 ─────────
            # In the full system, Module 02 receives this and calls Module 07.
            # Here we emit the context package as a final event so Module 02
            # can forward it.
            yield _sse("context_ready", {
                "session_id": router_resp.session_id,
                "intent": router_resp.intent,
                "context": router_resp.context,
            })

            # ── Step 5: Observability log ──────────────────────────────
            # FROM DL-06: log intent, confidence, tools used, latency.
            # NOT IN DL-06: cost_est, token count.
            total_tokens = router_resp.context.get("token_count", 0)
            logger.info(
                "[router] request_id=%s intent=%s conf=%.2f tools=%s "
                "latency=%.0fms tokens=%d",
                request_id,
                router_resp.intent,
                router_resp.confidence,
                [tc.tool for tc in router_resp.tools_called],
                _ms(t0),
                total_tokens,
            )

            yield _sse("done", {"latency_ms": _ms(t0)})

        except Exception as exc:
            logger.exception("[router] request_id=%s unhandled error", request_id)
            yield _sse("error", {"message": str(exc), "request_id": request_id})

    return EventSourceResponse(event_stream())


# ──────────────────────────────────────────────────────────────
#  POST /classify  — debug endpoint (no tool calls)
# ──────────────────────────────────────────────────────────────

@app.post("/classify")
async def classify_only(req: RouterRequest):
    """Return classification result only — useful for testing classifier logic."""
    result = classify(req.message, [m.model_dump() for m in req.history])
    missing = missing_slots(result.intent, result.slots)
    return {
        "intent": result.intent,
        "confidence": result.confidence,
        "reasoning": result.reasoning,
        "source": result.source,
        "slots": result.slots.model_dump(),
        "missing_slots": missing,
    }


# ──────────────────────────────────────────────────────────────
#  Helpers
# ──────────────────────────────────────────────────────────────

def _sse(event_type: str, data: dict) -> dict:
    """Format an SSE event as { event, data } for sse-starlette."""
    return {"event": event_type, "data": json.dumps(data, ensure_ascii=False)}


def _ms(t0: float) -> float:
    return round((time.perf_counter() - t0) * 1000, 1)
