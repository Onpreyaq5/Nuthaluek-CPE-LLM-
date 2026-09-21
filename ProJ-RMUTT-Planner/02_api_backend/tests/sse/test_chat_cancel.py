from __future__ import annotations

import asyncio

import pytest

from src.adapters.mock.student_data import MockStudentData
from src.api.deps import CurrentUser
from src.api.v1.chat import chat as chat_endpoint
from src.core.config import get_settings
from src.core.masking import hash_student_id
from src.repositories import chat_repository
from src.schemas.chat import ChatRequest

pytestmark = pytest.mark.db


class _SlowChatRouter:
    """ไม่มีวันจบเอง ต้องถูกยกเลิกจากภายนอกเท่านั้น (จำลอง client ตัดการเชื่อมต่อ)"""

    async def stream(self, enriched):
        yield {"type": "session", "session_id": enriched.session_id}
        yield {"type": "token", "text": "กำลังพิมพ์"}
        while True:
            await asyncio.sleep(3600)
            yield {"type": "token", "text": "ไม่ควรมาถึงตรงนี้"}


async def test_client_disconnect_marks_message_cancelled(seeded_demo_student, db_session) -> None:
    settings = get_settings()
    user = CurrentUser(
        student_id=settings.DEMO_STUDENT_ID,
        username=settings.DEMO_USERNAME,
        role="student",
        id_hash=hash_student_id(settings.DEMO_STUDENT_ID),
    )
    payload = ChatRequest(session_id=None, message="ทดสอบยกเลิกกลางทาง", plan_draft=None)

    response = await chat_endpoint(
        payload,
        user=user,
        db=db_session,
        student_data=MockStudentData(),
        chat_router_adapter=_SlowChatRouter(),
    )

    gen = response.body_iterator
    first_chunk = await gen.__anext__()
    assert '"type": "session"' in first_chunk or '"type":"session"' in first_chunk
    await gen.__anext__()  # token event

    with pytest.raises(asyncio.CancelledError):
        await gen.athrow(asyncio.CancelledError())

    messages = await chat_repository.list_messages_by_session(
        db_session, session_id=_extract_session_id(first_chunk), offset=0, limit=10
    )
    assistant_messages = [m for m in messages[0] if m.role == "assistant"]
    assert len(assistant_messages) == 1
    assert assistant_messages[0].status == "cancelled"
    assert assistant_messages[0].content == "กำลังพิมพ์"


def _extract_session_id(sse_line: str) -> int:
    import json

    payload = json.loads(sse_line[len("data: ") :].strip())
    return payload["session_id"]
