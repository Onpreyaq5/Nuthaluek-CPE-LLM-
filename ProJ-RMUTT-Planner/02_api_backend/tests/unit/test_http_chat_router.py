from __future__ import annotations

import json
from collections.abc import AsyncIterator

import httpx

from src.adapters.http.chat_router import HttpChatRouter
from src.schemas.chat import ChatHistoryItem, EnrichedChatRequest, EnrichedStudent, StudentPreferences


class _ChunkedAsyncByteStream(httpx.AsyncByteStream):
    def __init__(self, chunks: list[bytes]) -> None:
        self._chunks = chunks

    async def __aiter__(self) -> AsyncIterator[bytes]:
        for chunk in self._chunks:
            yield chunk

    async def aclose(self) -> None:
        return None


def _enriched(**overrides) -> EnrichedChatRequest:
    defaults = dict(
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
    defaults.update(overrides)
    return EnrichedChatRequest(**defaults)


def _sse_body(events: list[tuple[str, dict]], *, newline: str = "\n", ping: bool = False) -> bytes:
    """ประกอบ SSE body ให้ตรงกับรูปแบบจริงของ 03 (sse_starlette): event:<type>\\ndata:<json>\\n\\n
    ping=True แทรกบรรทัด comment (':') คั่นระหว่าง event เหมือนที่ sse_starlette ส่ง keep-alive จริง"""
    parts = []
    if ping:
        parts.append(f": ping{newline}{newline}")
    for event_type, data in events:
        payload = json.dumps(data, ensure_ascii=False)
        parts.append(f"event: {event_type}{newline}data: {payload}{newline}{newline}")
        if ping:
            parts.append(f": ping{newline}{newline}")
    return "".join(parts).encode()


def _router(events: list[tuple[str, dict]], *, newline: str = "\n", ping: bool = False) -> HttpChatRouter:
    body = _sse_body(events, newline=newline, ping=ping)

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, stream=_ChunkedAsyncByteStream([body]))

    return HttpChatRouter(transport=httpx.MockTransport(handler))


async def test_thai_text_split_mid_character_across_chunks_decodes_correctly() -> None:
    """จำลอง 03 ส่งบาง SSE line มาแบบตัด byte กลางตัวอักษรไทยพอดี (multi-byte UTF-8) ในรูปแบบ event: จริง
    ยืนยันว่า HttpChatRouter (ผ่าน httpx.aiter_lines ที่ decode แบบ incremental) ต่อกลับมาได้ถูกต้อง
    ไม่ใช่แค่ทดสอบผ่าน MockChatRouter ซึ่งไม่มีทางเจอบั๊กประเภทนี้เลยเพราะไม่ได้ผ่าน byte stream จริง"""
    full_line = (
        'event: token\ndata: {"text": "ทดสอบข้ามชิ้นส่วน"}\n\n'
    ).encode()

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


async def test_payload_sent_to_03_has_no_real_student_id() -> None:
    captured: dict = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured.update(json.loads(request.content))
        return httpx.Response(200, stream=_ChunkedAsyncByteStream([_sse_body([("done", {"latency_ms": 1})])]))

    router = HttpChatRouter(transport=httpx.MockTransport(handler))
    _ = [event async for event in router.stream(_enriched())]

    assert captured["student_id"] == "abc123"  # id_hash ไม่ใช่รหัสจริง
    assert captured["message"] == "ทดสอบ"
    assert captured["session_id"] == "1"
    assert captured["plan_draft"] is None
    assert "student" not in captured  # ไม่มี field แปลกปลอมของ 02 หลุดไป


async def test_payload_history_maps_role_and_content() -> None:
    captured: dict = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured.update(json.loads(request.content))
        return httpx.Response(200, stream=_ChunkedAsyncByteStream([_sse_body([("done", {"latency_ms": 1})])]))

    router = HttpChatRouter(transport=httpx.MockTransport(handler))
    enriched = _enriched(
        history=[
            ChatHistoryItem(role="user", content="เทอมนี้ผมติด F ฟิสิกส์"),
            ChatHistoryItem(role="assistant", content="รับทราบครับ"),
        ]
    )
    _ = [event async for event in router.stream(enriched)]

    assert captured["history"] == [
        {"role": "user", "content": "เทอมนี้ผมติด F ฟิสิกส์"},
        {"role": "assistant", "content": "รับทราบครับ"},
    ]


async def test_tool_start_and_tool_end_drop_extra_fields() -> None:
    router = _router(
        [
            ("tool_start", {"tool": "search_courses"}),
            ("tool_end", {"tool": "search_courses", "success": True, "latency_ms": 42.0}),
            ("done", {"latency_ms": 10}),
        ]
    )
    events = [event async for event in router.stream(_enriched())]

    assert events == [
        {"type": "tool_start", "tool": "search_courses"},
        {"type": "tool_end", "tool": "search_courses"},
        {"type": "done", "message_id": 0},
    ]


async def test_sources_event_maps_title_and_page_only_others_none() -> None:
    router = _router(
        [
            ("sources", {"sources": [{"title": "ข้อบังคับฯ", "page": 12}]}),
            ("done", {"latency_ms": 10}),
        ]
    )
    events = [event async for event in router.stream(_enriched())]

    assert events[0] == {
        "type": "sources",
        "items": [{"title": "ข้อบังคับฯ", "section": None, "page": 12, "document_id": None, "url": None}],
    }


async def test_clarify_becomes_token_with_question_text() -> None:
    router = _router(
        [
            ("clarify", {"question": "ช่วยระบุเทอมด้วยครับ", "missing_slots": ["term"]}),
            ("done", {"latency_ms": 5}),
        ]
    )
    events = [event async for event in router.stream(_enriched())]

    assert events == [
        {"type": "token", "text": "ช่วยระบุเทอมด้วยครับ"},
        {"type": "done", "message_id": 0},
    ]


async def test_done_with_answer_becomes_token_then_done() -> None:
    router = _router([("done", {"answer": "ขออภัย ไม่สามารถช่วยเรื่องนี้ได้"})])
    events = [event async for event in router.stream(_enriched())]

    assert events == [
        {"type": "token", "text": "ขออภัย ไม่สามารถช่วยเรื่องนี้ได้"},
        {"type": "done", "message_id": 0},
    ]


async def test_done_without_answer_is_plain_done() -> None:
    router = _router([("done", {"latency_ms": 123.4})])
    events = [event async for event in router.stream(_enriched())]

    assert events == [{"type": "done", "message_id": 0}]


async def test_error_event_never_forwards_raw_message_from_03() -> None:
    router = _router([("error", {"message": "Traceback (most recent call last): ...", "request_id": "abc"})])
    events = [event async for event in router.stream(_enriched())]

    assert events == [{"type": "error", "code": "UPSTREAM_502", "message": "ระบบ AI ขัดข้อง"}]
    joined = json.dumps(events)
    assert "Traceback" not in joined


async def test_router_result_and_context_ready_are_dropped() -> None:
    router = _router(
        [
            ("router_result", {"request_id": "r1", "intent": "COURSE_INFO", "confidence": 0.9}),
            ("tool_start", {"tool": "search_courses"}),
            ("tool_end", {"tool": "search_courses", "success": True}),
            ("context_ready", {"session_id": "1", "intent": "COURSE_INFO", "context": {}}),
            ("done", {"latency_ms": 1}),
        ]
    )
    events = [event async for event in router.stream(_enriched())]

    assert events == [
        {"type": "tool_start", "tool": "search_courses"},
        {"type": "tool_end", "tool": "search_courses"},
        {"type": "done", "message_id": 0},
    ]


async def test_unknown_event_type_is_dropped() -> None:
    router = _router([("some_future_event", {"foo": "bar"}), ("done", {"latency_ms": 1})])
    events = [event async for event in router.stream(_enriched())]

    assert events == [{"type": "done", "message_id": 0}]


async def test_ping_comment_lines_are_skipped() -> None:
    router = _router(
        [("tool_start", {"tool": "search_courses"}), ("done", {"latency_ms": 1})],
        ping=True,
    )
    events = [event async for event in router.stream(_enriched())]

    assert events == [
        {"type": "tool_start", "tool": "search_courses"},
        {"type": "done", "message_id": 0},
    ]


async def test_crlf_line_endings_are_supported() -> None:
    router = _router(
        [("tool_start", {"tool": "search_courses"}), ("done", {"latency_ms": 1})],
        newline="\r\n",
    )
    events = [event async for event in router.stream(_enriched())]

    assert events == [
        {"type": "tool_start", "tool": "search_courses"},
        {"type": "done", "message_id": 0},
    ]


async def test_data_that_is_not_valid_json_is_skipped_without_raising() -> None:
    body = b"event: token\ndata: {not-json\n\nevent: done\ndata: {\"latency_ms\": 1}\n\n"

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, stream=_ChunkedAsyncByteStream([body]))

    router = HttpChatRouter(transport=httpx.MockTransport(handler))
    events = [event async for event in router.stream(_enriched())]

    assert events == [{"type": "done", "message_id": 0}]


async def test_token_event_passes_through_when_03_sends_one() -> None:
    """03 ยังไม่ส่ง token จริง แต่ HttpChatRouter ต้องรองรับทันทีที่ 03 เริ่มส่ง (ตามสัญญา 6.2)"""
    router = _router([("token", {"text": "สวัสดีครับ"}), ("done", {"latency_ms": 1})])
    events = [event async for event in router.stream(_enriched())]

    assert events == [
        {"type": "token", "text": "สวัสดีครับ"},
        {"type": "done", "message_id": 0},
    ]
