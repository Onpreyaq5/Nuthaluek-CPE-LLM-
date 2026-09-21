"""tools.py — Tool Registry: 6 tools that the Planner can call

Each tool makes an async HTTP call to the appropriate downstream service.
With tenacity retry (1 retry) and a configurable timeout.

NOT IN DL-06:
  - Named tool registry with specific service endpoints
  - Tools are domain-specific (schedule conflict, course data, etc.)
  - asyncio.gather used for parallel tool execution
  - Retry via tenacity
"""
from __future__ import annotations
import asyncio
import logging
import time
from typing import Any

import httpx
from tenacity import retry, stop_after_attempt, wait_fixed

from .config import settings
from .models import ToolCall

logger = logging.getLogger(__name__)

_TIMEOUT = httpx.Timeout(settings.tool_timeout_s)


# ──────────────────────────────────────────────────────────────
#  Low-level HTTP helper with retry
# ──────────────────────────────────────────────────────────────

@retry(stop=stop_after_attempt(2), wait=wait_fixed(0.5))
async def _post(url: str, payload: dict) -> dict:
    async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
        resp = await client.post(url, json=payload)
        resp.raise_for_status()
        return resp.json()


@retry(stop=stop_after_attempt(2), wait=wait_fixed(0.5))
async def _get(url: str, params: dict | None = None) -> dict:
    async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
        resp = await client.get(url, params=params)
        resp.raise_for_status()
        return resp.json()


# ──────────────────────────────────────────────────────────────
#  Individual Tool Functions
# ──────────────────────────────────────────────────────────────

async def search_courses(
    q: str,
    term: str | None = None,
    filters: dict | None = None,
) -> dict:
    """
    Tool -> Module 04 (course_data_services).
    Find courses/sections matching query and optional filters.
    """
    payload = {"q": q, "term": term, "filters": filters or {}}
    return await _post(f"{settings.course_data_url}/courses/search", payload)


async def get_student_context(student_id: str) -> dict:
    """
    Tool -> Module 05 (data_integration).
    Return student profile, transcript summary, prereq status, preferences.
    """
    return await _get(f"{settings.data_integration_url}/context/{student_id}")


async def check_conflicts(sections: list[str]) -> dict:
    """
    Tool -> Module 06 (schedule_conflict_engine).
    Check C1-C6 conflict codes for the given list of section IDs.
    NOT IN DL-06: domain-specific conflict engine.
    """
    return await _post(f"{settings.schedule_engine_url}/conflicts/check",
                       {"sections": sections})


async def generate_plan(
    student_id: str,
    term: str,
    preferences: dict | None = None,
) -> dict:
    """
    Tool -> Module 06 (schedule_conflict_engine) auto-planner (CP-SAT).
    Returns 3-5 ranked schedule plans.
    NOT IN DL-06: constraint-solver based planning.
    """
    payload = {
        "student_id": student_id,
        "term": term,
        "preferences": preferences or {},
    }
    return await _post(f"{settings.schedule_engine_url}/plans/auto", payload)


async def search_knowledge(query: str, top_k: int = 6) -> dict:
    """
    Tool -> Module 07 (rag_llm_engine) RAG retrieval.
    BM25 + vector hybrid search over university regulations & curriculum.
    """
    return await _post(f"{settings.rag_llm_url}/knowledge/search",
                       {"query": query, "top_k": top_k})


async def answer_with_llm(context: dict, question: str) -> dict:
    """
    Tool -> Module 07 (rag_llm_engine) LLM generation.
    Send assembled context + question; receive streamed answer via SSE.
    (Caller handles the SSE stream; this triggers the generation endpoint.)
    """
    return await _post(f"{settings.rag_llm_url}/generate",
                       {"context": context, "question": question})


# ──────────────────────────────────────────────────────────────
#  Tool Registry  (name -> callable)
# ──────────────────────────────────────────────────────────────

TOOL_REGISTRY: dict[str, Any] = {
    "search_courses":      search_courses,
    "get_student_context": get_student_context,
    "check_conflicts":     check_conflicts,
    "generate_plan":       generate_plan,
    "search_knowledge":    search_knowledge,
    "answer_with_llm":     answer_with_llm,
}


# ──────────────────────────────────────────────────────────────
#  Execute a single tool and return a ToolCall record
# ──────────────────────────────────────────────────────────────

async def execute_tool(name: str, args: dict) -> ToolCall:
    fn = TOOL_REGISTRY.get(name)
    if fn is None:
        return ToolCall(tool=name, args=args, success=False,
                        error=f"Unknown tool: {name}")

    t0 = time.perf_counter()
    try:
        result = await fn(**args)
        latency = round((time.perf_counter() - t0) * 1000, 1)
        logger.info("[tool] %s OK latency=%.0fms", name, latency)
        return ToolCall(tool=name, args=args, result=result,
                        latency_ms=latency, success=True)
    except Exception as exc:
        latency = round((time.perf_counter() - t0) * 1000, 1)
        logger.error("[tool] %s FAILED latency=%.0fms err=%s", name, latency, exc)
        return ToolCall(tool=name, args=args, latency_ms=latency,
                        success=False, error=str(exc))


async def execute_parallel(calls: list[tuple[str, dict]]) -> list[ToolCall]:
    """Run multiple tools concurrently with asyncio.gather. NOT IN DL-06."""
    tasks = [execute_tool(name, args) for name, args in calls]
    return list(await asyncio.gather(*tasks))
