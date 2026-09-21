from __future__ import annotations

import json
from collections.abc import AsyncIterator
from typing import Any

import httpx

from src.core.config import get_settings
from src.core.errors import Upstream502Error
from src.core.logging import get_logger
from src.schemas.chat import EnrichedChatRequest

from ..http_base import HttpAdapterClient

logger = get_logger(__name__)

# ยืนยันจากโค้ดจริงของ 03_ai_router_agent/src/main.py (@app.post("/chat"), EventSourceResponse)
PATH_STREAM = "/chat"


def _build_router_payload(enriched: EnrichedChatRequest) -> dict:
    """แปลง EnrichedChatRequest ของ 02 เป็น RouterRequest ของ 03 (src/models.py)
    ห้ามส่งรหัส/ชื่อนักศึกษาจริง — ใช้ id_hash เท่านั้น

    request_id/term/preferences เป็นสัญญาที่เสนอเพิ่มรอบนี้ — 03 (ยัง ณ ตอนที่เขียน) ยังไม่อ่าน field พวกนี้
    เลย (RouterRequest ปัจจุบันไม่มี field เหล่านี้ extra จะถูก 03 เพิกเฉยเพราะ pydantic default ไม่ใช้
    extra="forbid") ส่งไปก่อนเพื่อให้ 03 พร้อมอ่านได้ทันทีที่ทีม 03 เพิ่ม field รองรับ"""
    return {
        "request_id": enriched.request_id,
        "student_id": enriched.student.id_hash,
        "message": enriched.query,
        "session_id": str(enriched.session_id),
        "history": [{"role": h.role, "content": h.content} for h in enriched.history],
        "plan_draft": enriched.plan_draft,
        "term": enriched.term,
        "preferences": enriched.student.preferences.model_dump(mode="json"),
    }


class _Terminal(Exception):
    """ใช้ภายในเท่านั้นเพื่อหยุด async generator ทันทีหลังส่ง event จบรอบ (refusal/router_done/error)"""


def _translate_event(  # noqa: C901 - state machine อ่านง่ายกว่าถ้าอยู่รวมกัน
    event_name: str, data: dict[str, Any], state: dict[str, Any]
) -> list[dict]:
    """แปลง 1 raw SSE event จาก 03 เป็น 0 หรือหลาย "internal event" (key "kind" ไม่ใช่ "type" ของ
    public schema) — state เก็บสิ่งที่เจอมาก่อนหน้าในสตรีมเดียวกัน (clarify_seen/context_ready)
    เพื่อตัดสิน outcome ของ router_done เมื่อ 03 (ของจริงตอนนี้) ไม่ส่ง field "outcome" มาเอง"""
    if event_name == "tool_start":
        tool = data.get("tool")
        return [{"kind": "tool_start", "tool": tool}] if tool else []

    if event_name == "tool_end":
        tool = data.get("tool")
        return [{"kind": "tool_end", "tool": tool}] if tool else []

    if event_name == "sources":
        items = [
            {
                "title": src.get("title", ""),
                "section": src.get("section"),
                "page": src.get("page"),
                "document_id": src.get("document_id"),
                "url": src.get("url"),
            }
            for src in data.get("sources", [])
        ]
        return [{"kind": "sources", "items": items}]

    if event_name == "clarify":
        state["clarify_seen"] = True
        return [{"kind": "clarify", "question": data.get("question", "")}]

    if event_name == "context_ready":
        state["context_ready"] = {
            "intent": data.get("intent"),
            "context": data.get("context") or {},
            "question": data.get("question"),
        }
        return [dict(state["context_ready"], kind="context_ready")]

    if event_name == "done":
        # 03 ของจริงตอนนี้ยังไม่ส่ง "outcome" — ต้องอนุมานจาก event ก่อนหน้าในสตรีมเดียวกันนี้เท่านั้น
        # (ห้ามเดาข้าม request) ถ้ากำกวม (ไม่เจอ clarify/context_ready มาก่อนเลย) ให้ error แทนแกล้งสำเร็จ
        answer = data.get("answer")
        if answer:
            # กรณี guardrail ปฏิเสธ (03 ส่ง done{answer} แทน event "refusal" โดยตรง — ของจริงยังไม่มี
            # event ชนิด refusal ต่างหาก) ถือเป็นจบรอบทันที ไม่สนใจ event อื่นที่อาจตามมาอีก (03 ของจริง
            # มีบั๊กส่ง done ซ้ำสองครั้งในเคสนี้ — เราจบสตรีมของเราเองตั้งแต่ครั้งแรกที่เจอ)
            state["final_kind"] = "refusal"
            state["final_message"] = answer
            raise _Terminal
        outcome = data.get("outcome")
        if outcome is None:
            if state.get("clarify_seen"):
                outcome = "clarify"
            elif state.get("context_ready") is not None:
                outcome = "context_ready"
            # ไม่งั้นปล่อย outcome เป็น None -> orchestrator จะถือว่ากำกวมและ error
        state["final_outcome"] = outcome
        raise _Terminal

    if event_name == "refusal":
        state["final_kind"] = "refusal"
        state["final_message"] = data.get("message", "")
        raise _Terminal

    if event_name == "error":
        state["final_kind"] = "error"
        state["final_message"] = data.get("message", "")
        raise _Terminal

    # router_result: มี intent/confidence ให้ใช้ในอนาคต (เช่นบันทึกลง log) แต่ยังไม่มีที่เก็บฝั่ง 02 ที่
    # adapter ชั้นนี้เอื้อมถึงได้ (อยู่ใน orchestrator/chat.py) — ทิ้งไปก่อน
    # event อื่นที่ไม่รู้จัก (เช่น debug_log) -> ทิ้งเสมอ
    return []


class HttpChatRouter:
    def __init__(self, *, transport: httpx.AsyncBaseTransport | None = None) -> None:
        self._transport = transport

    async def stream(self, enriched: EnrichedChatRequest) -> AsyncIterator[dict]:
        settings = get_settings()
        client = HttpAdapterClient(
            base_url=settings.ROUTER_URL,
            module="03",
            timeout_policy=settings.timeouts.chat_total,
            transport=self._transport,
        )
        try:
            async with client.stream(
                "POST", PATH_STREAM, json=_build_router_payload(enriched)
            ) as response:
                if response.status_code >= 400:
                    raise Upstream502Error(
                        "โมดูล 03 ตอบสถานะผิดพลาด", details={"module": "03", "status": response.status_code}
                    )

                state: dict[str, Any] = {}
                event_name = "message"
                data_lines: list[str] = []

                try:
                    async for line in response.aiter_lines():
                        if line == "":
                            for translated in self._flush(event_name, data_lines, state):
                                yield translated
                            event_name = "message"
                            data_lines = []
                            continue
                        if line.startswith(":"):
                            continue  # SSE comment/ping — ข้าม
                        if line.startswith("event:"):
                            event_name = line[len("event:") :].strip()
                            continue
                        if line.startswith("data:"):
                            data_lines.append(line[len("data:") :].lstrip())
                            continue
                        # field อื่น (id:, retry:) ไม่ใช้ — ข้าม

                    # เผื่อ stream จบโดยไม่มีบรรทัดว่างปิดท้าย event สุดท้าย
                    for translated in self._flush(event_name, data_lines, state):
                        yield translated
                except _Terminal:
                    for terminal_event in self._finalize(state):
                        yield terminal_event
        finally:
            await client.aclose()

    def _flush(self, event_name: str, data_lines: list[str], state: dict[str, Any]) -> list[dict]:
        if not data_lines:
            return []
        raw = "\n".join(data_lines)
        try:
            data = json.loads(raw)
        except json.JSONDecodeError:
            logger.warning("chat_router_sse_data_not_json", sse_event_type=event_name)
            return []
        if not isinstance(data, dict):
            return []
        return _translate_event(event_name, data, state)

    def _finalize(self, state: dict[str, Any]) -> list[dict]:
        final_kind = state.get("final_kind")
        if final_kind == "refusal":
            return [{"kind": "refusal", "message": state.get("final_message", "")}]
        if final_kind == "error":
            return [{"kind": "error", "message": state.get("final_message", "")}]
        return [{"kind": "router_done", "outcome": state.get("final_outcome")}]
