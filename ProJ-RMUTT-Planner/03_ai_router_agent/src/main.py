"""main.py — FastAPI service: AI Router / Agent  (port 8100)

Endpoints:
  GET  /health      -> liveness probe (Docker HEALTHCHECK)
  POST /chat        -> SSE stream: intent classification + planner + context for Module 07
  POST /classify    -> debug: return classification result only (no tool calls)
"""
from __future__ import annotations
import asyncio
import json
import logging
import time
import uuid
from typing import AsyncGenerator

from fastapi import FastAPI, Request
from prometheus_fastapi_instrumentator import Instrumentator
from fastapi.responses import JSONResponse
from sse_starlette.sse import EventSourceResponse

from .config import settings
from .models import RouterRequest, SSEEvent
from .classifier import classify, missing_slots, SLOT_QUESTIONS, resolve_term
from .planner import run_planner
from .ai_select import select_ai, backing_model
from .metrics import ROUTED, TOOL_CALLS

logging.basicConfig(
    level=settings.log_level,
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)
logger = logging.getLogger(__name__)

app = FastAPI(title="03_ai_router_agent", version="0.1.0")
# /metrics ให้ Prometheus (ช่อง Monitoring ในแผนภาพ) รวมตัวนับ ROUTED/TOOL_CALLS ด้วย
Instrumentator().instrument(app).expose(app, endpoint="/metrics", include_in_schema=False)


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
    """
    # Support backward compatibility for request_id
    request_id = req.request_id or str(uuid.uuid4())[:8]

    async def event_stream() -> AsyncGenerator[dict, None]:
        t0 = time.perf_counter()
        try:
            # ── Step 1: Intent Classification ─────────────────────────
            # รันใน thread: ถ้า keyword ไม่มั่นใจ classify จะเรียกโมเดล (Gemini/Ollama) แบบ sync
            # ถ้ารันตรงนี้ event loop จะค้าง request อื่นทั้ง service รอไปด้วย
            classification = await asyncio.to_thread(
                classify, req.message, [m.model_dump() for m in req.history]
            )
            ai_target = select_ai(classification.intent)
            ROUTED.labels(classification.intent, ai_target, classification.source).inc()
            
            # Resolve term and academic year
            resolved_term, resolved_year = resolve_term(classification.slots.term, req.term)
            classification.slots.term = resolved_term
            if resolved_year:
                classification.slots.academic_year = resolved_year

            yield _sse("router_result", {
                "request_id": request_id,
                "intent": classification.intent,
                "confidence": classification.confidence,
                "reasoning": classification.reasoning,
                "source": classification.source,
                "slots": classification.slots.model_dump(),
                # กล่อง 4 ในแผนภาพ: เลือก AI ตัวไหนตอบ และตัวนั้นใช้โมเดลอะไรจริง
                "ai_target": ai_target,
                "ai_model": backing_model(ai_target),
            })

            # ── Step 2: Slot check — ask back if required slot missing ─
            missing = missing_slots(classification.intent, classification.slots)
            if missing:
                question = SLOT_QUESTIONS.get(missing[0], "ช่วยระบุข้อมูลเพิ่มเติมได้ไหมครับ?")
                yield _sse("clarify", {"question": question, "missing_slots": missing})
                yield _sse("done", {"outcome": "clarify", "latency_ms": _ms(t0)})
                return

            # ── Step 3: Planner Loop (tool execution + guardrails) ─────
            router_resp, sse_events = await run_planner(req, classification)
            for tc in router_resp.tools_called:
                TOOL_CALLS.labels(tc.tool, str(tc.success).lower()).inc()
            router_resp.context["ai_target"] = ai_target
            router_resp.context["intent"] = router_resp.intent

            has_refusal = False
            for event in sse_events:
                yield _sse(event.type, event.data)
                if event.type == "refusal":
                    has_refusal = True
            
            if has_refusal:
                yield _sse("done", {"outcome": "refused", "latency_ms": _ms(t0)})
                return

            # ── Step 4: Forward assembled context to Module 07 ─────────
            yield _sse("context_ready", {
                "request_id": request_id,
                "session_id": router_resp.session_id,
                "question": req.message,
                "intent": router_resp.intent,
                "context": router_resp.context,
            })

            # ── Step 5: Observability log ──────────────────────────────
            total_tokens = router_resp.context.get("token_count", 0)
            logger.info(
                "[router] request_id=%s intent=%s conf=%.2f tools=%s latency=%.0fms tokens=%d",
                request_id,
                router_resp.intent,
                router_resp.confidence,
                [tc.tool for tc in router_resp.tools_called],
                _ms(t0),
                total_tokens,
            )

            yield _sse("done", {"outcome": "context_ready", "latency_ms": _ms(t0)})

        except Exception as exc:
            logger.exception("[router] request_id=%s unhandled error", request_id)
            yield _sse("error", {"code": "ROUTER_ERROR", "message": "ไม่สามารถประมวลผลคำขอได้"})

    return EventSourceResponse(event_stream())


# ──────────────────────────────────────────────────────────────
#  POST /classify  — debug endpoint (no tool calls)
# ──────────────────────────────────────────────────────────────

@app.post("/classify")
async def classify_only(req: RouterRequest):
    """Return classification result only — useful for testing classifier logic."""
    result = classify(req.message, [m.model_dump() for m in req.history])
    resolved_term, resolved_year = resolve_term(result.slots.term, req.term)
    result.slots.term = resolved_term
    if resolved_year:
        result.slots.academic_year = resolved_year

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
    # Data is sent as-is without embedding 'type' inside it for internal SSE
    return {"event": event_type, "data": json.dumps(data, ensure_ascii=False)}

def _ms(t0: float) -> float:
    return round((time.perf_counter() - t0) * 1000, 1)
