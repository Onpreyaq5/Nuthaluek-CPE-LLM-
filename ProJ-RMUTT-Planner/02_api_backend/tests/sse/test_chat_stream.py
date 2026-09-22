from __future__ import annotations

import httpx
import pytest

from src.adapters import get_answer_generator, get_chat_router, get_student_data
from src.adapters.mock.student_data import MockStudentData
from src.core.errors import Upstream502Error
from src.main import app

pytestmark = pytest.mark.db


class _FakeAnswerGenerator:
    """แทน 07 ตัวจริง (ยังไม่มี contract ที่ยืนยันแล้ว) — inject เฉพาะใน test ตามที่ PLAN กำหนด"""

    def __init__(self, events: list[dict] | None = None) -> None:
        self._events = (
            events
            if events is not None
            else [
                {"type": "token", "text": "ถอนรายวิชา"},
                {"type": "token", "text": "ได้ตามระเบียบข้อ 18"},
                {
                    "type": "sources",
                    "items": [
                        {
                            "title": "ข้อบังคับฯ",
                            "section": "ข้อ 18",
                            "page": 12,
                            "document_id": "doc-regulation-2566",
                            "url": None,
                        }
                    ],
                },
            ]
        )
        self.calls: list[dict] = []

    async def generate(self, *, question: str, context: dict, history: list[dict]):
        self.calls.append({"question": question, "context": context, "history": history})
        for event in self._events:
            yield event


class _NeverCalledAnswerGenerator:
    async def generate(self, *, question: str, context: dict, history: list[dict]):
        raise AssertionError("ไม่ควรเรียก answer_generator ในเคสนี้")
        yield  # pragma: no cover - ทำให้เป็น async generator function


class _NormalChatRouter:
    async def stream(self, enriched):
        yield {"kind": "tool_start", "tool": "search_knowledge"}
        yield {"kind": "tool_end", "tool": "search_knowledge"}
        yield {"kind": "context_ready", "intent": "REGULATION_QA", "context": {}, "question": None}
        yield {"kind": "router_done", "outcome": "context_ready"}


class _NeverStartsChatRouter:
    async def stream(self, enriched):
        raise Upstream502Error("จำลอง 03 ไม่ตอบสนองตั้งแต่เริ่ม", details={"module": "03"})
        yield  # pragma: no cover - ทำให้เป็น async generator function


class _CutsOffMidwayChatRouter:
    async def stream(self, enriched):
        yield {"kind": "tool_start", "tool": "search_knowledge"}
        # จบ generator ตรงนี้เลยโดยไม่มี router_done (จำลอง 03 หลุดกลางทาง)


class _AmbiguousDoneChatRouter:
    """จำลอง 03 จบสตรีมด้วย done ที่ไม่มี outcome และไม่เคยมี clarify/context_ready มาก่อนเลย — กำกวม"""

    async def stream(self, enriched):
        yield {"kind": "router_done", "outcome": None}


class _ClarifyChatRouter:
    async def stream(self, enriched):
        yield {"kind": "clarify", "question": "ต้องการจัดตารางเทอมไหนครับ?"}
        yield {"kind": "router_done", "outcome": "clarify"}


class _RefusalChatRouter:
    async def stream(self, enriched):
        yield {"kind": "tool_start", "tool": "search_knowledge"}
        yield {"kind": "tool_end", "tool": "search_knowledge"}
        yield {"kind": "refusal", "message": "ไม่พบข้อมูลอ้างอิงที่เพียงพอ"}


class _MixedEventsChatRouter:
    """tool นอก allowlist ต้องถูกกรองทิ้งที่ sanitize_event ก่อนถึง frontend"""

    async def stream(self, enriched):
        yield {"kind": "tool_start", "tool": "delete_all_data"}
        yield {"kind": "tool_start", "tool": "search_knowledge"}
        yield {"kind": "tool_end", "tool": "search_knowledge"}
        yield {"kind": "context_ready", "intent": "REGULATION_QA", "context": {}, "question": None}
        yield {"kind": "router_done", "outcome": "context_ready"}


class _CapturingChatRouter:
    def __init__(self) -> None:
        self.captured = None

    async def stream(self, enriched):
        self.captured = enriched
        yield {"kind": "context_ready", "intent": "GENERAL_CHAT", "context": {}, "question": None}
        yield {"kind": "router_done", "outcome": "context_ready"}


def _client(*, authed: bool = True) -> httpx.AsyncClient:
    from src.core.config import get_settings
    from src.core.security import create_access_token

    transport = httpx.ASGITransport(app=app)
    if not authed:
        return httpx.AsyncClient(transport=transport, base_url="http://testserver")
    settings = get_settings()
    token = create_access_token(
        student_id=settings.DEMO_STUDENT_ID, username=settings.DEMO_USERNAME, role="student"
    )
    return httpx.AsyncClient(transport=transport, base_url="http://testserver", cookies={"session": token})


def _parse_sse_events(text: str) -> list[dict]:
    import json

    events = []
    for chunk in text.strip().split("\n\n"):
        chunk = chunk.strip()
        if not chunk:
            continue
        assert chunk.startswith("data: ")
        events.append(json.loads(chunk[len("data: ") :]))
    return events


@pytest.fixture(autouse=True)
def _reset_overrides():
    yield
    app.dependency_overrides.clear()


@pytest.fixture(autouse=True)
def _default_student_data():
    app.dependency_overrides[get_student_data] = lambda: MockStudentData()
    yield


@pytest.fixture(autouse=True)
def _default_answer_generator():
    app.dependency_overrides[get_answer_generator] = lambda: _FakeAnswerGenerator()
    yield


async def test_normal_event_sequence_ends_with_done(seeded_demo_student) -> None:
    app.dependency_overrides[get_chat_router] = lambda: _NormalChatRouter()
    async with _client() as client:
        response = await client.post("/api/v1/chat", json={"session_id": None, "message": "สวัสดีครับ"})

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/event-stream")
    events = _parse_sse_events(response.text)
    assert events[0]["type"] == "session"
    assert events[-1]["type"] == "done"
    types = [e["type"] for e in events]
    assert types == ["session", "tool_start", "tool_end", "token", "token", "sources", "done"]


async def test_done_message_id_matches_real_persisted_assistant_message(seeded_demo_student) -> None:
    """เคสที่เคย fail: message_id ต้องเป็นแถวจริงใน DB ไม่ใช่ placeholder 0 หรือค่าคงที่จาก router"""
    app.dependency_overrides[get_chat_router] = lambda: _NormalChatRouter()
    async with _client() as client:
        response = await client.post("/api/v1/chat", json={"session_id": None, "message": "สวัสดีครับ"})
        events = _parse_sse_events(response.text)
        session_id = events[0]["session_id"]
        done_event = events[-1]
        assert done_event["type"] == "done"
        message_id = done_event["message_id"]
        assert message_id != 0

        messages_response = await client.get(f"/api/v1/chat/sessions/{session_id}/messages")

    messages = messages_response.json()["data"]["items"]
    assistant_message = next(m for m in messages if m["role"] == "assistant")
    assert assistant_message["id"] == message_id
    assert assistant_message["content"] == "ถอนรายวิชาได้ตามระเบียบข้อ 18"
    assert assistant_message["status"] == "complete"


async def test_greeting_gets_real_answer_from_generator_not_empty_done(seeded_demo_student) -> None:
    """เคสที่เคย fail: ไม่มีคำตอบสำหรับคำทักทาย — ตอนนี้ context_ready ต้องเรียก generator จริงเสมอ"""
    app.dependency_overrides[get_chat_router] = lambda: _CapturingChatRouter()
    fake_generator = _FakeAnswerGenerator(events=[{"type": "token", "text": "สวัสดีครับ มีอะไรให้ช่วยไหม"}])
    app.dependency_overrides[get_answer_generator] = lambda: fake_generator

    async with _client() as client:
        response = await client.post("/api/v1/chat", json={"session_id": None, "message": "สวัสดีครับ"})

    events = _parse_sse_events(response.text)
    token_events = [e for e in events if e["type"] == "token"]
    assert len(token_events) == 1
    assert token_events[0]["text"] == "สวัสดีครับ มีอะไรให้ช่วยไหม"
    assert events[-1]["type"] == "done"
    assert len(fake_generator.calls) == 1


async def test_clarify_ends_turn_with_question_and_real_message_id_without_calling_generator(
    seeded_demo_student,
) -> None:
    app.dependency_overrides[get_chat_router] = lambda: _ClarifyChatRouter()
    app.dependency_overrides[get_answer_generator] = lambda: _NeverCalledAnswerGenerator()

    async with _client() as client:
        response = await client.post("/api/v1/chat", json={"session_id": None, "message": "ช่วยจัดตาราง"})
        events = _parse_sse_events(response.text)
        session_id = events[0]["session_id"]

        messages_response = await client.get(f"/api/v1/chat/sessions/{session_id}/messages")

    assert response.status_code == 200
    token_events = [e for e in events if e["type"] == "token"]
    assert len(token_events) == 1
    assert token_events[0]["text"] == "ต้องการจัดตารางเทอมไหนครับ?"
    assert events[-1]["type"] == "done"
    assert events[-1]["message_id"] != 0

    messages = messages_response.json()["data"]["items"]
    assistant_message = next(m for m in messages if m["role"] == "assistant")
    assert assistant_message["status"] == "complete"
    assert assistant_message["content"] == "ต้องการจัดตารางเทอมไหนครับ?"


async def test_refusal_sends_message_once_and_never_calls_generator(seeded_demo_student) -> None:
    app.dependency_overrides[get_chat_router] = lambda: _RefusalChatRouter()
    app.dependency_overrides[get_answer_generator] = lambda: _NeverCalledAnswerGenerator()

    async with _client() as client:
        response = await client.post("/api/v1/chat", json={"session_id": None, "message": "คำถามที่ตอบไม่ได้"})

    events = _parse_sse_events(response.text)
    token_events = [e for e in events if e["type"] == "token"]
    assert len(token_events) == 1
    assert token_events[0]["text"] == "ไม่พบข้อมูลอ้างอิงที่เพียงพอ"
    assert events[-1]["type"] == "done"


async def test_ambiguous_router_done_outcome_becomes_error_not_fake_success(seeded_demo_student) -> None:
    app.dependency_overrides[get_chat_router] = lambda: _AmbiguousDoneChatRouter()
    app.dependency_overrides[get_answer_generator] = lambda: _NeverCalledAnswerGenerator()

    async with _client() as client:
        response = await client.post("/api/v1/chat", json={"session_id": None, "message": "ทดสอบกำกวม"})
        events = _parse_sse_events(response.text)
        session_id = events[0]["session_id"]

        messages_response = await client.get(f"/api/v1/chat/sessions/{session_id}/messages")

    assert events[-1]["type"] == "error"
    assert events[-1]["code"] == "UPSTREAM_502"
    assert "done" not in [e["type"] for e in events]

    messages = messages_response.json()["data"]["items"]
    assistant_message = next(m for m in messages if m["role"] == "assistant")
    assert assistant_message["status"] == "interrupted"
    assert assistant_message["content"] == ""


async def test_null_session_id_creates_new_session(seeded_demo_student) -> None:
    app.dependency_overrides[get_chat_router] = lambda: _NormalChatRouter()
    async with _client() as client:
        response = await client.post("/api/v1/chat", json={"session_id": None, "message": "เริ่มใหม่"})
        events = _parse_sse_events(response.text)
        session_id = events[0]["session_id"]

        sessions_response = await client.get("/api/v1/chat/sessions")

    assert any(s["id"] == session_id for s in sessions_response.json()["data"]["items"])


async def test_upstream_fails_before_start_returns_502(seeded_demo_student) -> None:
    app.dependency_overrides[get_chat_router] = lambda: _NeverStartsChatRouter()
    async with _client() as client:
        response = await client.post("/api/v1/chat", json={"session_id": None, "message": "ทดสอบ"})

    assert response.status_code == 502
    assert response.headers["content-type"].startswith("application/json")
    assert response.json()["error"]["code"] == "UPSTREAM_502"


async def test_upstream_cuts_off_midway_sends_error_event_and_marks_interrupted(
    seeded_demo_student,
) -> None:
    app.dependency_overrides[get_chat_router] = lambda: _CutsOffMidwayChatRouter()
    async with _client() as client:
        response = await client.post("/api/v1/chat", json={"session_id": None, "message": "ทดสอบตัดกลางทาง"})
        events = _parse_sse_events(response.text)
        session_id = events[0]["session_id"]

        messages_response = await client.get(f"/api/v1/chat/sessions/{session_id}/messages")

    assert events[-1]["type"] == "error"
    assert events[-1]["code"] == "UPSTREAM_502"

    messages = messages_response.json()["data"]["items"]
    assistant_message = next(m for m in messages if m["role"] == "assistant")
    assert assistant_message["status"] == "interrupted"


async def test_disallowed_tool_is_dropped_before_frontend(seeded_demo_student) -> None:
    app.dependency_overrides[get_chat_router] = lambda: _MixedEventsChatRouter()
    async with _client() as client:
        response = await client.post("/api/v1/chat", json={"session_id": None, "message": "ทดสอบ filter"})

    events = _parse_sse_events(response.text)
    tool_start_events = [e for e in events if e["type"] == "tool_start"]

    # tool_start ของ delete_all_data (นอก allowlist) ต้องไม่ปรากฏ มีแค่ search_knowledge
    assert len(tool_start_events) == 1
    assert tool_start_events[0]["tool"] == "search_knowledge"
    assert "arguments" not in tool_start_events[0]

    assert events[-1]["type"] == "done"


async def test_enriched_payload_sent_to_router_has_no_real_identity(seeded_demo_student) -> None:
    capturing = _CapturingChatRouter()
    app.dependency_overrides[get_chat_router] = lambda: capturing

    from src.core.config import get_settings

    settings = get_settings()
    fake_id_in_message = f"{settings.DEMO_STUDENT_ID}-1"
    async with _client() as client:
        await client.post(
            "/api/v1/chat",
            json={"session_id": None, "message": f"รหัสของฉันคือ {fake_id_in_message} ช่วยดูให้หน่อย"},
        )

    assert capturing.captured is not None
    enriched = capturing.captured
    # schema เองไม่มี field student_id/name เลย มีแต่ id_hash
    assert not hasattr(enriched.student, "student_id")
    assert not hasattr(enriched.student, "name_th")
    assert enriched.student.id_hash
    assert enriched.student.id_hash != settings.DEMO_STUDENT_ID
    # scrub_text ต้องทำงานกับ query ก่อนส่งออกไปเสมอ
    assert fake_id_in_message not in enriched.query


async def test_history_skips_non_complete_messages(seeded_demo_student, db_session) -> None:
    from src.models import ChatMessage, ChatSession

    session = ChatSession(student_id=(await _demo_student_id()), title="ประวัติเก่า")
    db_session.add(session)
    await db_session.commit()
    await db_session.refresh(session)

    db_session.add_all(
        [
            ChatMessage(session_id=session.id, role="user", content="ข้อความเก่าที่สมบูรณ์", status="complete"),
            ChatMessage(
                session_id=session.id, role="assistant", content="คำตอบเก่า", status="complete", sources=[]
            ),
            ChatMessage(
                session_id=session.id, role="assistant", content="ค้างไว้ไม่จบ", status="interrupted", sources=[]
            ),
            ChatMessage(
                session_id=session.id, role="assistant", content="ถูกยกเลิก", status="cancelled", sources=[]
            ),
        ]
    )
    await db_session.commit()

    capturing = _CapturingChatRouter()
    app.dependency_overrides[get_chat_router] = lambda: capturing

    async with _client() as client:
        await client.post(
            "/api/v1/chat", json={"session_id": session.id, "message": "ข้อความใหม่"}
        )

    assert capturing.captured is not None
    history_contents = [item.content for item in capturing.captured.history]
    assert "ข้อความเก่าที่สมบูรณ์" in history_contents
    assert "คำตอบเก่า" in history_contents
    assert "ค้างไว้ไม่จบ" not in history_contents
    assert "ถูกยกเลิก" not in history_contents


async def test_chat_requires_login() -> None:
    async with _client(authed=False) as client:
        response = await client.post("/api/v1/chat", json={"session_id": None, "message": "hi"})
    assert response.status_code == 401


async def test_session_id_of_other_student_returns_403(second_student, seeded_demo_student) -> None:
    from src.core.config import get_settings

    settings = get_settings()
    # สร้าง session เป็นของ second_student ก่อน
    transport = httpx.ASGITransport(app=app)
    app.dependency_overrides[get_chat_router] = lambda: _NormalChatRouter()
    async with httpx.AsyncClient(
        transport=transport, base_url="http://testserver", cookies={"session": second_student["token"]}
    ) as other_client:
        other_response = await other_client.post(
            "/api/v1/chat", json={"session_id": None, "message": "ของคนอื่น"}
        )
    other_session_id = _parse_sse_events(other_response.text)[0]["session_id"]

    async with _client() as client:
        response = await client.post(
            "/api/v1/chat", json={"session_id": other_session_id, "message": "แอบใช้ของคนอื่น"}
        )

    assert response.status_code == 403
    assert response.json()["error"]["code"] == "FORBIDDEN_403"
    _ = settings


async def test_session_id_not_found_returns_404(seeded_demo_student) -> None:
    app.dependency_overrides[get_chat_router] = lambda: _NormalChatRouter()
    async with _client() as client:
        response = await client.post(
            "/api/v1/chat", json={"session_id": 999999, "message": "ไม่มีจริง"}
        )
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "NOT_FOUND_404"


async def _demo_student_id() -> str:
    from src.core.config import get_settings

    return get_settings().DEMO_STUDENT_ID


async def test_list_sessions_without_login_returns_401() -> None:
    async with _client(authed=False) as client:
        response = await client.get("/api/v1/chat/sessions")

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "AUTH_401"


async def test_list_sessions_empty_when_no_chats_yet(seeded_demo_student) -> None:
    async with _client() as client:
        response = await client.get("/api/v1/chat/sessions")

    assert response.status_code == 200
    body = response.json()
    assert body["ok"] is True
    assert body["data"]["items"] == []
    assert body["data"]["next_cursor"] is None


async def test_list_sessions_returns_only_own_sessions(second_student, seeded_demo_student) -> None:
    app.dependency_overrides[get_chat_router] = lambda: _NormalChatRouter()
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app),
        base_url="http://testserver",
        cookies={"session": second_student["token"]},
    ) as other_client:
        await other_client.post("/api/v1/chat", json={"session_id": None, "message": "ของคนอื่น"})

    async with _client() as client:
        own_response = await client.post(
            "/api/v1/chat", json={"session_id": None, "message": "ของฉัน"}
        )
        sessions_response = await client.get("/api/v1/chat/sessions")

    assert own_response.status_code == 200
    body = sessions_response.json()
    assert len(body["data"]["items"]) == 1


async def test_list_messages_without_login_returns_401() -> None:
    async with _client(authed=False) as client:
        response = await client.get("/api/v1/chat/sessions/1/messages")

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "AUTH_401"


async def test_list_messages_nonexistent_session_returns_404(seeded_demo_student) -> None:
    async with _client() as client:
        response = await client.get("/api/v1/chat/sessions/999999/messages")

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "NOT_FOUND_404"


async def test_list_messages_of_other_students_session_returns_403(
    second_student, seeded_demo_student
) -> None:
    app.dependency_overrides[get_chat_router] = lambda: _NormalChatRouter()
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app),
        base_url="http://testserver",
        cookies={"session": second_student["token"]},
    ) as other_client:
        other_response = await other_client.post(
            "/api/v1/chat", json={"session_id": None, "message": "ของคนอื่น"}
        )
    other_session_id = _parse_sse_events(other_response.text)[0]["session_id"]

    async with _client() as client:
        response = await client.get(f"/api/v1/chat/sessions/{other_session_id}/messages")

    assert response.status_code == 403
    assert response.json()["error"]["code"] == "FORBIDDEN_403"
