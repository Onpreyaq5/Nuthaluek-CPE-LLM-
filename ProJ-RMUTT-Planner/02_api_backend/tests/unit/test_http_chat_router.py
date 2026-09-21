from __future__ import annotations

from collections.abc import AsyncIterator

import httpx

from src.adapters.http.chat_router import HttpChatRouter
from src.schemas.chat import EnrichedChatRequest, EnrichedStudent, StudentPreferences


class _ChunkedAsyncByteStream(httpx.AsyncByteStream):
    def __init__(self, chunks: list[bytes]) -> None:
        self._chunks = chunks

    async def __aiter__(self) -> AsyncIterator[bytes]:
        for chunk in self._chunks:
            yield chunk

    async def aclose(self) -> None:
        return None


def _enriched() -> EnrichedChatRequest:
    return EnrichedChatRequest(
        request_id="req_test",
        session_id=1,
        query="ทดสอบ",
        student=EnrichedStudent(
            id_hash="abc123",
            program_id="CPE-2566",
            curriculum_year=2566,
            year_level=3,
            credits_earned=80,
            preferences=StudentPreferences(),
        ),
        history=[],
        plan_draft=None,
        term="1/2569",
    )


async def test_thai_text_split_mid_character_across_chunks_decodes_correctly() -> None:
    """จำลอง 03 ส่งบาง SSE line มาแบบตัด byte กลางตัวอักษรไทยพอดี (multi-byte UTF-8)
    ยืนยันว่า HttpChatRouter (ผ่าน httpx.aiter_lines ที่ decode แบบ incremental) ต่อกลับมาได้ถูกต้อง
    ไม่ใช่แค่ทดสอบผ่าน MockChatRouter ซึ่งไม่มีทางเจอบั๊กประเภทนี้เลยเพราะไม่ได้ผ่าน byte stream จริง
    """
    full_line = 'data: {"type": "token", "text": "ทดสอบข้ามชิ้นส่วน"}\n\n'.encode()

    split_at = None
    for i in range(1, len(full_line)):
        if 0x80 <= full_line[i] <= 0xBF:  # continuation byte ของ UTF-8 (อยู่กลางตัวอักษรหลาย byte)
            split_at = i
            break
    assert split_at is not None, "ต้องเจอจุดกึ่งกลาง multi-byte character อย่างน้อยหนึ่งจุด"

    chunk1, chunk2 = full_line[:split_at], full_line[split_at:]

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, stream=_ChunkedAsyncByteStream([chunk1, chunk2]))

    router = HttpChatRouter(transport=httpx.MockTransport(handler))
    events = [event async for event in router.stream(_enriched())]

    assert events == [{"type": "token", "text": "ทดสอบข้ามชิ้นส่วน"}]
