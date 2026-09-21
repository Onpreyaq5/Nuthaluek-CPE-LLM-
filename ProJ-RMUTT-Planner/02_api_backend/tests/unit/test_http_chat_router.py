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
            preferences=StudentPreferences(free_days=["FRI"], no_early_class=True, max_credits=18),
        ),
        history=[],
        plan_draft=None,
        term="2/2569",
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


def _router(
    events: list[tuple[str, dict]], *, newline: str = "\n", ping: bool = False, status: int = 200
) -> HttpChatRouter:
    body = _sse_body(events, newline=newline, ping=ping)

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(status, stream=_ChunkedAsyncByteStream([body]))

    return HttpChatRouter(transport=httpx.MockTransport(handler))


async def test_thai_text_split_mid_character_across_chunks_decodes_correctly() -> None:
    """จำลอง 03 ส่งบาง SSE line มาแบบตัด byte กลางตัวอักษรไทยพอดี (multi-byte UTF-8) ในรูปแบบ event: จริง
    ยืนยันว่า HttpChatRouter (ผ่าน httpx.aiter_lines ที่ decode แบบ incremental) ต่อกลับมาได้ถูกต้อง
    ไม่ใช่แค่ทดสอบผ่าน mock ซึ่งไม่มีทางเจอบั๊กประเภทนี้เลยเพราะไม่ได้ผ่าน byte stream จริง"""
    full_line = 'event: clarify\ndata: {"question": "ต้องการจัดตารางเทอมไหนครับ?"}\n\n'.encode()

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

    assert events[0] == {"kind": "clarify", "question": "ต้องการจัดตารางเทอมไหนครับ?"}


async def test_payload_includes_request_id_term_and_preferences() -> None:
    captured: dict = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured.update(json.loads(request.content))
        return httpx.Response(200, stream=_ChunkedAsyncByteStream([_sse_body([("done", {"latency_ms": 1})])]))

    router = HttpChatRouter(transport=httpx.MockTransport(handler))
    _ = [event async for event in router.stream(_enriched())]

    assert captured["request_id"] == "req_test"
    assert captured["term"] == "2/2569"
    assert captured["preferences"] == {"free_days": ["FRI"], "no_early_class": True, "max_credits": 18}


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


async def test_http_error_status_raises_upstream502() -> None:
    from src.core.errors import Upstream502Error

    router = _router([("done", {"latency_ms": 1})], status=500)
    try:
        _ = [event async for event in router.stream(_enriched())]
        raise AssertionError("ควร raise Upstream502Error")
    except Upstream502Error as exc:
        assert exc.details["module"] == "03"


async def test_tool_start_and_tool_end_pass_through_as_internal_events() -> None:
    router = _router(
        [
            ("tool_start", {"tool": "search_courses"}),
            ("tool_end", {"tool": "search_courses", "success": True, "latency_ms": 42.0}),
            ("done", {"latency_ms": 10}),
        ]
    )
    events = [event async for event in router.stream(_enriched())]

    assert events == [
        {"kind": "tool_start", "tool": "search_courses"},
        {"kind": "tool_end", "tool": "search_courses"},
        {"kind": "router_done", "outcome": None},
    ]


async def test_sources_event_maps_title_and_page_only_others_none() -> None:
    router = _router(
        [
            ("sources", {"sources": [{"title": "ข้อบังคับฯ", "page": 12}]}),
            ("context_ready", {"intent": "REGULATION_QA", "context": {}}),
            ("done", {"latency_ms": 10}),
        ]
    )
    events = [event async for event in router.stream(_enriched())]

    assert events[0] == {
        "kind": "sources",
        "items": [{"title": "ข้อบังคับฯ", "section": None, "page": 12, "document_id": None, "url": None}],
    }


async def test_clarify_then_done_becomes_router_done_outcome_clarify() -> None:
    router = _router(
        [
            ("clarify", {"question": "ช่วยระบุเทอมด้วยครับ", "missing_slots": ["term"]}),
            ("done", {"latency_ms": 5}),
        ]
    )
    events = [event async for event in router.stream(_enriched())]

    assert events == [
        {"kind": "clarify", "question": "ช่วยระบุเทอมด้วยครับ"},
        {"kind": "router_done", "outcome": "clarify"},
    ]


async def test_context_ready_then_done_becomes_router_done_outcome_context_ready() -> None:
    router = _router(
        [
            ("context_ready", {"intent": "PLAN_GENERATE", "context": {"a": 1}, "question": "q"}),
            ("done", {"latency_ms": 5}),
        ]
    )
    events = [event async for event in router.stream(_enriched())]

    assert events == [
        {"kind": "context_ready", "intent": "PLAN_GENERATE", "context": {"a": 1}, "question": "q"},
        {"kind": "router_done", "outcome": "context_ready"},
    ]


async def test_done_with_answer_becomes_refusal_and_ignores_further_events() -> None:
    """03 จริงมีบั๊กส่ง done ซ้ำ (ครั้งแรกมี answer, ครั้งสองไม่มี) + context_ready แทรกมาด้วย —
    ต้องจบสตรีมตั้งแต่ done ตัวแรกที่มี answer ไม่สนใจอะไรที่ตามมาอีกเลย"""
    router = _router(
        [
            ("done", {"answer": "ขออภัย ไม่สามารถช่วยเรื่องนี้ได้"}),
            ("context_ready", {"intent": "GENERAL_CHAT", "context": {}}),
            ("done", {"latency_ms": 999}),
        ]
    )
    events = [event async for event in router.stream(_enriched())]

    assert events == [{"kind": "refusal", "message": "ขออภัย ไม่สามารถช่วยเรื่องนี้ได้"}]


async def test_native_refusal_event_type() -> None:
    router = _router([("refusal", {"message": "ไม่พบข้อมูลอ้างอิงที่เพียงพอ"})])
    events = [event async for event in router.stream(_enriched())]

    assert events == [{"kind": "refusal", "message": "ไม่พบข้อมูลอ้างอิงที่เพียงพอ"}]


async def test_error_event_stops_stream_immediately() -> None:
    router = _router(
        [
            ("error", {"code": "ROUTER_ERROR", "message": "ไม่สามารถประมวลผลคำขอได้"}),
            ("done", {"latency_ms": 1}),
        ]
    )
    events = [event async for event in router.stream(_enriched())]

    assert events == [{"kind": "error", "message": "ไม่สามารถประมวลผลคำขอได้"}]


async def test_router_result_and_unknown_event_are_dropped() -> None:
    router = _router(
        [
            ("router_result", {"request_id": "r1", "intent": "COURSE_INFO", "confidence": 0.9}),
            ("debug_log", {"foo": "bar"}),
            ("tool_start", {"tool": "search_courses"}),
            ("done", {"latency_ms": 1}),
        ]
    )
    events = [event async for event in router.stream(_enriched())]

    assert events == [
        {"kind": "tool_start", "tool": "search_courses"},
        {"kind": "router_done", "outcome": None},
    ]


async def test_done_with_no_prior_clarify_or_context_ready_has_outcome_none() -> None:
    """กำกวม (ไม่เจอ clarify/context_ready มาก่อนเลย) -> outcome=None ให้ orchestrator ตัดสินใจ error เอง
    (adapter ชั้นนี้ไม่ error เอง แค่รายงาน outcome ตามจริง)"""
    router = _router([("done", {"latency_ms": 1})])
    events = [event async for event in router.stream(_enriched())]

    assert events == [{"kind": "router_done", "outcome": None}]


async def test_ping_comment_lines_are_skipped() -> None:
    router = _router(
        [("tool_start", {"tool": "search_courses"}), ("done", {"latency_ms": 1})],
        ping=True,
    )
    events = [event async for event in router.stream(_enriched())]

    assert events == [
        {"kind": "tool_start", "tool": "search_courses"},
        {"kind": "router_done", "outcome": None},
    ]


async def test_crlf_line_endings_are_supported() -> None:
    router = _router(
        [("tool_start", {"tool": "search_courses"}), ("done", {"latency_ms": 1})],
        newline="\r\n",
    )
    events = [event async for event in router.stream(_enriched())]

    assert events == [
        {"kind": "tool_start", "tool": "search_courses"},
        {"kind": "router_done", "outcome": None},
    ]


async def test_data_that_is_not_valid_json_is_skipped_without_raising() -> None:
    body = b"event: token\ndata: {not-json\n\nevent: done\ndata: {\"latency_ms\": 1}\n\n"

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, stream=_ChunkedAsyncByteStream([body]))

    router = HttpChatRouter(transport=httpx.MockTransport(handler))
    events = [event async for event in router.stream(_enriched())]

    assert events == [{"kind": "router_done", "outcome": None}]
