"""planner.py — Planner Loop

NOT IN DL-06 (DL-06 had simple one-shot routing; main project uses a loop).

Design from 02_step.txt / 03_process.txt:
  while step < MAX_TOOL_STEPS:
      select tool -> call -> collect observation -> assess if enough
  -> send combined context to Module 07

Intent -> Tool Map (from 03_process.txt):
  SCHEDULE_CONFLICT  -> get_student_context, check_conflicts
  PLAN_GENERATE      -> get_student_context, search_courses, generate_plan
  COURSE_INFO        -> search_courses
  CURRICULUM_RULE    -> get_student_context, search_knowledge
  REGULATION_QA      -> search_knowledge
  GENERAL_CHAT       -> (direct pass to Module 07 answer_with_llm)
"""
from __future__ import annotations
import asyncio
import logging
from typing import AsyncGenerator

from .config import settings
from .models import (
    ClassificationResult, RouterRequest, RouterResponse,
    ToolCall, SSEEvent,
)
from .tools import execute_tool, execute_parallel
from .context_manager import build_context_package
from .guardrails import validate_tools_for_intent

logger = logging.getLogger(__name__)


# ──────────────────────────────────────────────────────────────
#  Intent -> Tool Plan
# ──────────────────────────────────────────────────────────────

def _build_tool_plan(
    intent: str,
    req: RouterRequest,
    classification: ClassificationResult,
) -> list[list[tuple[str, dict]]]:
    slots = classification.slots
    student_id = req.student_id
    term = slots.term
    course_codes = slots.course_codes

    if intent == "SCHEDULE_CONFLICT":
        return [
            [("get_student_context", {"student_id": student_id})],
            [("check_conflicts", {"sections": course_codes})],
        ]

    if intent == "PLAN_GENERATE":
        return [
            [("get_student_context", {"student_id": student_id})],
            [
                ("search_courses", {"q": "", "term": term}),
            ],
            [("generate_plan", {
                "student_id": student_id,
                "term": term,
                "preferences": req.preferences.model_dump(mode="json") if req.preferences else {},
            })],
        ]

    if intent == "COURSE_INFO":
        q = " ".join(course_codes) or req.message
        return [
            [("search_courses", {"q": q, "term": slots.term})],
        ]

    if intent == "CURRICULUM_RULE":
        return [
            [("get_student_context", {"student_id": student_id})],
            [("search_knowledge", {"query": req.message, "top_k": 6})],
        ]

    if intent == "REGULATION_QA":
        return [
            [("search_knowledge", {"query": req.message, "top_k": 6})],
        ]

    return []


# ──────────────────────────────────────────────────────────────
#  Planner loop
# ──────────────────────────────────────────────────────────────

async def run_planner(
    req: RouterRequest,
    classification: ClassificationResult,
) -> tuple[RouterResponse, list[SSEEvent]]:
    """
    Execute the tool plan for the classified intent.
    Returns (RouterResponse for Module 07, list of SSE events for streaming).

    NOT IN DL-06: staged parallel execution + SSE tool_start/tool_end events.
    """
    sse_events: list[SSEEvent] = []
    all_tool_calls: list[ToolCall] = []
    accumulated_context: dict = {}

    stages = _build_tool_plan(req.intent if hasattr(req, "intent") else classification.intent,
                              req, classification)
    step = 0

    for stage_idx, stage in enumerate(stages):
        if step >= settings.max_tool_steps:
            logger.warning("[planner] reached MAX_TOOL_STEPS=%d", settings.max_tool_steps)
            break

        # Emit tool_start events for each tool in the stage
        for tool_name, _ in stage:
            sse_events.append(SSEEvent(type="tool_start", data={"tool": tool_name}))

        # Execute this stage in parallel
        results: list[ToolCall] = await execute_parallel(stage)
        all_tool_calls.extend(results)
        step += len(stage)

        # Emit tool_end events and accumulate context
        for tc in results:
            sse_events.append(SSEEvent(type="tool_end", data={
                "tool": tc.tool,
                "success": tc.success,
                "latency_ms": tc.latency_ms,
            }))
            if tc.success and tc.result:
                accumulated_context[tc.tool] = tc.result

    # ── Guardrail check ──────────────────────────────────────
    ok, refusal_msg = validate_tools_for_intent(classification, all_tool_calls)
    if not ok:
        sse_events.append(SSEEvent(type="refusal", data={"message": refusal_msg}))

    # ── Build context package for Module 07 ─────────────────
    student_context = accumulated_context.get("get_student_context", {})
    ctx_package = build_context_package(
        history=req.history,
        student_context=student_context,
        plan_draft=req.plan_draft,
    )
    ctx_package["tool_results"] = accumulated_context
    ctx_package["guardrail_ok"] = ok
    ctx_package["guardrail_refusal"] = refusal_msg if not ok else None

    # Emit sources if RAG was called
    rag_result = accumulated_context.get("search_knowledge")
    if rag_result:
        chunks = rag_result.get("chunks", [])
        # chunk ของ 07 ใช้ title / section / doc_id (ไม่มี field "source")
        # เดิมอ่าน c["source"] หน้าเว็บจึงได้แหล่งอ้างอิงชื่อว่างทุกอัน
        sources = [
            {
                "title": c.get("title") or c.get("source", ""),
                "section": c.get("section") or None,
                "document_id": c.get("doc_id"),
                "page": c.get("page"),
            }
            for c in chunks
        ]
        sse_events.append(SSEEvent(type="sources", data={"sources": sources}))

    response = RouterResponse(
        session_id=req.session_id,
        student_id=req.student_id,
        original_query=req.message,
        intent=classification.intent,
        confidence=classification.confidence,
        reasoning=classification.reasoning,
        slots=classification.slots,
        tools_called=all_tool_calls,
        context=ctx_package,
        conversation_history=req.history,
    )

    return response, sse_events
