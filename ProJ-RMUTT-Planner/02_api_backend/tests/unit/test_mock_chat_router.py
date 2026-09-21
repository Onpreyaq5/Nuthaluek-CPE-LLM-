from __future__ import annotations

import pytest

from src.adapters.mock.chat_router import MockChatRouter
from src.schemas.chat import EnrichedChatRequest, EnrichedStudent, StudentPreferences


def _enriched(query: str) -> EnrichedChatRequest:
    return EnrichedChatRequest(
        request_id="req_test",
        session_id=1,
        query=query,
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


async def test_stream_yields_full_sequence_ending_in_done() -> None:
    events = [event async for event in MockChatRouter().stream(_enriched("สวัสดี"))]
    types = [e["type"] for e in events]
    assert types[0] == "session"
    assert types[-1] == "done"
    assert "sources" in types
    assert "token" in types


async def test_stream_fails_mid_way_when_query_contains_fail_marker() -> None:
    with pytest.raises(ConnectionError):
        async for _ in MockChatRouter().stream(_enriched("ทดสอบ __fail__ กลางทาง")):
            pass
