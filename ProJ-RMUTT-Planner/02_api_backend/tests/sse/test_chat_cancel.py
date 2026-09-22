from __future__ import annotations

import asyncio

import pytest

from src.adapters.interfaces import NotReadyAnswerGenerator
from src.adapters.mock.student_data import MockStudentData
from src.api.deps import CurrentUser
from src.api.v1.chat import chat as chat_endpoint
from src.core.config import get_settings
from src.core.masking import hash_student_id
from src.repositories import chat_repository
from src.schemas.chat import ChatRequest

pytestmark = pytest.mark.db


class _SlowAnswerGenerator:
    """ไม่มีวันจบเอง ต้องถูกยกเลิกจากภายนอกเท่านั้น (จำลอง client ตัดการเชื่อมต่อระหว่าง 07 กำลังสร้างคำตอบ)"""

    def __init__(self) -> None:
        self.closed = False

    async def generate(self, *, question: str, context: dict, history: list[dict]):
        try:
            yield {"type": "token", "text": "กำลังพิมพ์"}
            while True:
                await asyncio.sleep(3600)
                yield {"type": "token", "text": "ไม่ควรมาถึงตรงนี้"}
        finally:
            self.closed = True


class _ReachesContextReadyChatRouter:
    async def stream(self, enriched):
        yield {"kind": "context_ready", "intent": "GENERAL_CHAT", "context": {}, "question": None}
        yield {"kind": "router_done", "outcome": "context_ready"}


class _SlowRouterChatRouter:
    """ไม่มีวันจบเอง ตั้งแต่ก่อนถึง context_ready เลย (จำลอง client ตัดการเชื่อมต่อระหว่าง 03 กำลังเรียก tool)"""

    def __init__(self) -> None:
        self.closed = False

    async def stream(self, enriched):
        try:
            yield {"kind": "tool_start", "tool": "search_knowledge"}
            while True:
                await asyncio.sleep(3600)
        finally:
            self.closed = True


async def test_client_disconnect_during_answer_generation_marks_message_cancelled(
    seeded_demo_student, db_session
) -> None:
    """cancel ระหว่าง 07 (answer generator) กำลังสร้างคำตอบ — token ที่ส่งไปแล้วก่อน cancel ต้องถูกบันทึกไว้
    และ generator ต้องถูกปิดจริง (ไม่ใช่แค่ทิ้งค้างไว้)"""
    settings = get_settings()
    user = CurrentUser(
        student_id=settings.DEMO_STUDENT_ID,
        username=settings.DEMO_USERNAME,
        role="student",
        id_hash=hash_student_id(settings.DEMO_STUDENT_ID),
    )
    payload = ChatRequest(session_id=None, message="ทดสอบยกเลิกกลางทาง", plan_draft=None)
    slow_generator = _SlowAnswerGenerator()

    response = await chat_endpoint(
        payload,
        user=user,
        db=db_session,
        student_data=MockStudentData(),
        chat_router_adapter=_ReachesContextReadyChatRouter(),
        answer_generator=slow_generator,
    )

    gen = response.body_iterator
    first_chunk = await gen.__anext__()
    assert '"type": "session"' in first_chunk or '"type":"session"' in first_chunk
    await gen.__anext__()  # token event ("กำลังพิมพ์")

    with pytest.raises(asyncio.CancelledError):
        await gen.athrow(asyncio.CancelledError())

    messages = await chat_repository.list_messages_by_session(
        db_session, session_id=_extract_session_id(first_chunk), offset=0, limit=10
    )
    assistant_messages = [m for m in messages[0] if m.role == "assistant"]
    assert len(assistant_messages) == 1
    assert assistant_messages[0].status == "cancelled"
    assert assistant_messages[0].content == "กำลังพิมพ์"
    assert slow_generator.closed is True


async def test_client_disconnect_during_router_phase_closes_router_generator(
    seeded_demo_student, db_session
) -> None:
    """cancel ระหว่าง 03 (router) ยังไม่ถึง context_ready เลย — ต้องปิด router generator จริง"""
    settings = get_settings()
    user = CurrentUser(
        student_id=settings.DEMO_STUDENT_ID,
        username=settings.DEMO_USERNAME,
        role="student",
        id_hash=hash_student_id(settings.DEMO_STUDENT_ID),
    )
    payload = ChatRequest(session_id=None, message="ทดสอบยกเลิกช่วง router", plan_draft=None)
    slow_router = _SlowRouterChatRouter()

    response = await chat_endpoint(
        payload,
        user=user,
        db=db_session,
        student_data=MockStudentData(),
        chat_router_adapter=slow_router,
        answer_generator=NotReadyAnswerGenerator(),
    )

    gen = response.body_iterator
    first_chunk = await gen.__anext__()
    assert '"type": "session"' in first_chunk or '"type":"session"' in first_chunk
    await gen.__anext__()  # tool_start event

    with pytest.raises(asyncio.CancelledError):
        await gen.athrow(asyncio.CancelledError())

    messages = await chat_repository.list_messages_by_session(
        db_session, session_id=_extract_session_id(first_chunk), offset=0, limit=10
    )
    assistant_messages = [m for m in messages[0] if m.role == "assistant"]
    assert len(assistant_messages) == 1
    assert assistant_messages[0].status == "cancelled"
    assert slow_router.closed is True


def _extract_session_id(sse_line: str) -> int:
    import json

    payload = json.loads(sse_line[len("data: ") :].strip())
    return payload["session_id"]
