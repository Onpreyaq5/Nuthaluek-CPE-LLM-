from __future__ import annotations

import json
from collections.abc import AsyncIterator
from typing import Any

import httpx

from src.core.config import get_settings
from src.core.logging import get_logger
from src.schemas.chat import EnrichedChatRequest

from ..http_base import HttpAdapterClient

logger = get_logger(__name__)

# ยืนยันจากโค้ดจริงของ 03_ai_router_agent/src/main.py (@app.post("/chat"), EventSourceResponse)
PATH_STREAM = "/chat"

# DoneEvent ของ 02 (src/schemas/chat.py) บังคับ message_id: int แต่ 03 ไม่มีแนวคิดนี้เลย (ไม่ใช่ DB row
# ของ 02) — chat.py ไม่ได้ใช้ค่านี้จริง (ใช้ assistant_message.id จาก DB แทน) ใส่ placeholder ไว้ให้ผ่าน
# schema เท่านั้น ไม่งั้น sanitize_event จะทิ้ง event "done" ทั้งอันเงียบๆ เพราะ validate ไม่ผ่าน
_DONE_MESSAGE_ID_PLACEHOLDER = 0

_ERROR_MESSAGE = "ระบบ AI ขัดข้อง"


def _build_router_payload(enriched: EnrichedChatRequest) -> dict:
    """แปลง EnrichedChatRequest ของ 02 เป็น RouterRequest ของ 03 (src/models.py)
    ห้ามส่งรหัส/ชื่อนักศึกษาจริง — ใช้ id_hash เท่านั้น"""
    return {
        "student_id": enriched.student.id_hash,
        "message": enriched.query,
        "session_id": str(enriched.session_id),
        "history": [{"role": h.role, "content": h.content} for h in enriched.history],
        "plan_draft": enriched.plan_draft,
    }


def _translate_event(event_name: str, data: dict[str, Any]) -> list[dict]:
    """แปลง 1 event ดิบจาก 03 เป็น 0 หรือหลาย event ตามสัญญาของ 02 (src/schemas/chat.py)"""
    if event_name == "tool_start":
        tool = data.get("tool")
        return [{"type": "tool_start", "tool": tool}] if tool else []

    if event_name == "tool_end":
        tool = data.get("tool")
        return [{"type": "tool_end", "tool": tool}] if tool else []

    if event_name == "token":
        return [{"type": "token", "text": data.get("text", "")}]

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
        return [{"type": "sources", "items": items}]

    if event_name == "clarify":
        question = data.get("question", "")
        return [{"type": "token", "text": question}]

    if event_name == "done":
        answer = data.get("answer")
        events: list[dict] = []
        if answer:
            events.append({"type": "token", "text": answer})
        events.append({"type": "done", "message_id": _DONE_MESSAGE_ID_PLACEHOLDER})
        return events

    if event_name == "error":
        return [{"type": "error", "code": "UPSTREAM_502", "message": _ERROR_MESSAGE}]

    # router_result: ยังไม่มีที่เก็บ intent ฝั่ง 02 ที่ adapter ชั้นนี้เอื้อมไปบันทึกได้ (ต้องแก้ chat.py/
    # chat_service.py ซึ่งอยู่นอกขอบเขตงานนี้) — ทิ้งไปก่อน context_ready และ event อื่นที่ไม่รู้จัก: ทิ้งเสมอ
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
                event_name = "message"
                data_lines: list[str] = []

                async for line in response.aiter_lines():
                    if line == "":
                        for translated in self._flush(event_name, data_lines):
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
                for translated in self._flush(event_name, data_lines):
                    yield translated
        finally:
            await client.aclose()

    def _flush(self, event_name: str, data_lines: list[str]) -> list[dict]:
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
        return _translate_event(event_name, data)
