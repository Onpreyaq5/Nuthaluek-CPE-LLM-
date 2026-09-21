from __future__ import annotations

from collections.abc import AsyncIterator

from src.services import chat_orchestrator


async def _aiter(items: list[dict]) -> AsyncIterator[dict]:
    for item in items:
        yield item


class _FakeAnswerGenerator:
    def __init__(self, events: list[dict] | None = None) -> None:
        self._events = events if events is not None else [{"type": "token", "text": "คำตอบจริง"}]
        self.calls: list[dict] = []

    async def generate(self, *, question: str, context: dict, history: list[dict]) -> AsyncIterator[dict]:
        self.calls.append({"question": question, "context": context, "history": history})
        for event in self._events:
            yield event


class _NeverCalledAnswerGenerator:
    async def generate(self, *, question: str, context: dict, history: list[dict]) -> AsyncIterator[dict]:
        raise AssertionError("ไม่ควรเรียก answer_generator ในเคสนี้")
        yield  # pragma: no cover - ทำให้เป็น async generator function


async def _collect(agen: AsyncIterator[dict]) -> list[dict]:
    return [event async for event in agen]


async def test_clarify_sends_question_as_token_then_done_without_calling_generator() -> None:
    generator = _NeverCalledAnswerGenerator()
    router_events = _aiter(
        [
            {"kind": "clarify", "question": "ต้องการจัดตารางเทอมไหนครับ?"},
            {"kind": "router_done", "outcome": "clarify"},
        ]
    )

    events = await _collect(
        chat_orchestrator.run_chat_turn(router_events, generator, question="ช่วยจัดตาราง", history=[])
    )

    assert events == [
        {"type": "token", "text": "ต้องการจัดตารางเทอมไหนครับ?"},
        {"type": "done"},
    ]


async def test_refusal_sends_message_once_and_never_calls_generator() -> None:
    generator = _NeverCalledAnswerGenerator()
    router_events = _aiter([{"kind": "refusal", "message": "ไม่พบข้อมูลอ้างอิงที่เพียงพอ"}])

    events = await _collect(
        chat_orchestrator.run_chat_turn(router_events, generator, question="คำถาม", history=[])
    )

    assert events == [
        {"type": "token", "text": "ไม่พบข้อมูลอ้างอิงที่เพียงพอ"},
        {"type": "done"},
    ]


async def test_context_ready_calls_generator_exactly_once_and_streams_tokens_and_sources() -> None:
    generator = _FakeAnswerGenerator(
        events=[
            {"type": "token", "text": "สวัสดีครับ"},
            {"type": "token", "text": " ยินดีช่วยเหลือ"},
            {"type": "sources", "items": [{"title": "คู่มือ", "section": None, "page": None,
                                            "document_id": None, "url": None}]},
        ]
    )
    router_events = _aiter(
        [
            {"kind": "tool_start", "tool": "search_knowledge"},
            {"kind": "tool_end", "tool": "search_knowledge"},
            {"kind": "context_ready", "intent": "GENERAL_CHAT", "context": {"foo": "bar"}, "question": None},
            {"kind": "router_done", "outcome": "context_ready"},
        ]
    )

    events = await _collect(
        chat_orchestrator.run_chat_turn(
            router_events, generator, question="สวัสดี", history=[{"role": "user", "content": "hi"}]
        )
    )

    assert events == [
        {"type": "tool_start", "tool": "search_knowledge"},
        {"type": "tool_end", "tool": "search_knowledge"},
        {"type": "token", "text": "สวัสดีครับ"},
        {"type": "token", "text": " ยินดีช่วยเหลือ"},
        {
            "type": "sources",
            "items": [{"title": "คู่มือ", "section": None, "page": None, "document_id": None, "url": None}],
        },
        {"type": "done"},
    ]
    assert len(generator.calls) == 1
    assert generator.calls[0]["question"] == "สวัสดี"
    assert generator.calls[0]["context"] == {"foo": "bar"}
    assert generator.calls[0]["history"] == [{"role": "user", "content": "hi"}]


async def test_greeting_with_empty_context_still_gets_real_answer_not_empty_done() -> None:
    """เคสที่เคย fail: GENERAL_CHAT (คำทักทาย) context ว่างเปล่า แต่ยังต้องเรียก generator จริง ไม่ใช่ done เฉยๆ"""
    generator = _FakeAnswerGenerator(events=[{"type": "token", "text": "สวัสดีครับ มีอะไรให้ช่วยไหม"}])
    router_events = _aiter(
        [
            {"kind": "context_ready", "intent": "GENERAL_CHAT", "context": {}, "question": None},
            {"kind": "router_done", "outcome": "context_ready"},
        ]
    )

    events = await _collect(
        chat_orchestrator.run_chat_turn(router_events, generator, question="สวัสดีครับ", history=[])
    )

    assert events == [
        {"type": "token", "text": "สวัสดีครับ มีอะไรให้ช่วยไหม"},
        {"type": "done"},
    ]
    assert len(generator.calls) == 1


async def test_error_event_stops_immediately_without_done() -> None:
    generator = _NeverCalledAnswerGenerator()
    router_events = _aiter([{"kind": "error", "message": "internal traceback ไม่ควรหลุดออกไป"}])

    events = await _collect(
        chat_orchestrator.run_chat_turn(router_events, generator, question="คำถาม", history=[])
    )

    assert events == [{"type": "error", "code": "UPSTREAM_502", "message": "ระบบ AI ขัดข้อง"}]


async def test_ambiguous_outcome_none_becomes_error_not_empty_success() -> None:
    """router_done ที่ไม่มี clarify/context_ready มาก่อนเลย (outcome=None) ต้อง error ห้ามแกล้งสำเร็จ"""
    generator = _NeverCalledAnswerGenerator()
    router_events = _aiter([{"kind": "router_done", "outcome": None}])

    events = await _collect(
        chat_orchestrator.run_chat_turn(router_events, generator, question="คำถาม", history=[])
    )

    assert events == [{"type": "error", "code": "UPSTREAM_502", "message": "ระบบ AI ขัดข้อง"}]


async def test_context_ready_outcome_without_context_ready_event_is_error() -> None:
    """router_done{outcome=context_ready} แต่ไม่เคยมี context_ready event มาก่อนเลย -> ลำดับผิดปกติ ต้อง error"""
    generator = _NeverCalledAnswerGenerator()
    router_events = _aiter([{"kind": "router_done", "outcome": "context_ready"}])

    events = await _collect(
        chat_orchestrator.run_chat_turn(router_events, generator, question="คำถาม", history=[])
    )

    assert events == [{"type": "error", "code": "UPSTREAM_502", "message": "ระบบ AI ขัดข้อง"}]


async def test_sources_event_forwarded_immediately_before_context_ready() -> None:
    generator = _FakeAnswerGenerator(events=[])
    router_events = _aiter(
        [
            {"kind": "sources", "items": [{"title": "a", "section": None, "page": None,
                                            "document_id": None, "url": None}]},
            {"kind": "context_ready", "intent": "REGULATION_QA", "context": {}, "question": None},
            {"kind": "router_done", "outcome": "context_ready"},
        ]
    )

    events = await _collect(
        chat_orchestrator.run_chat_turn(router_events, generator, question="q", history=[])
    )

    assert events[0]["type"] == "sources"
    assert events[-1] == {"type": "done"}
