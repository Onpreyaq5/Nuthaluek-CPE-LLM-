from __future__ import annotations

import json

import httpx
import pytest

from src.adapters import get_answer_generator, get_chat_router, get_student_data
from src.adapters.mock.student_data import MockStudentData
from src.main import app

pytestmark = pytest.mark.db


class _SimpleChatRouter:
    async def stream(self, enriched):
        yield {"kind": "context_ready", "intent": "GENERAL_CHAT", "context": {}, "question": None}
        yield {"kind": "router_done", "outcome": "context_ready"}


class _SimpleAnswerGenerator:
    async def generate(self, *, question: str, context: dict, history: list[dict]):
        yield {"type": "token", "text": "คำตอบสั้นๆ"}


@pytest.fixture(autouse=True)
def _reset_overrides():
    yield
    app.dependency_overrides.clear()


async def test_submit_feedback_on_own_plan_success(logged_in_client: httpx.AsyncClient) -> None:
    create_response = await logged_in_client.post(
        "/api/v1/plans", json={"term": "1/2569", "name": "แผนให้ feedback", "section_ids": ["GE101-01"]}
    )
    plan_id = create_response.json()["data"]["plan_id"]

    response = await logged_in_client.post(
        "/api/v1/feedback",
        json={"target_type": "plan", "target_id": str(plan_id), "rating": 5, "reason": "ดีมาก"},
    )

    assert response.status_code == 200
    assert response.json()["data"]["feedback_id"] > 0


async def test_submit_feedback_on_own_chat_message_success(logged_in_client: httpx.AsyncClient) -> None:
    app.dependency_overrides[get_student_data] = lambda: MockStudentData()
    app.dependency_overrides[get_chat_router] = lambda: _SimpleChatRouter()
    app.dependency_overrides[get_answer_generator] = lambda: _SimpleAnswerGenerator()

    chat_response = await logged_in_client.post(
        "/api/v1/chat", json={"session_id": None, "message": "ทดสอบ"}
    )
    first_event = json.loads(chat_response.text.split("\n\n")[0][len("data: ") :])
    session_id = first_event["session_id"]
    messages_response = await logged_in_client.get(f"/api/v1/chat/sessions/{session_id}/messages")
    assistant_message_id = next(
        m["id"] for m in messages_response.json()["data"]["items"] if m["role"] == "assistant"
    )

    response = await logged_in_client.post(
        "/api/v1/feedback",
        json={"target_type": "chat_message", "target_id": str(assistant_message_id), "rating": 4},
    )

    assert response.status_code == 200


async def test_submit_feedback_on_other_students_plan_returns_403(
    logged_in_client: httpx.AsyncClient, second_student: dict
) -> None:
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(
        transport=transport, base_url="http://testserver", cookies={"session": second_student["token"]}
    ) as other_client:
        create_response = await other_client.post(
            "/api/v1/plans", json={"term": "1/2569", "name": "แผนของคนอื่น", "section_ids": ["GE101-01"]}
        )
    other_plan_id = create_response.json()["data"]["plan_id"]

    response = await logged_in_client.post(
        "/api/v1/feedback",
        json={"target_type": "plan", "target_id": str(other_plan_id), "rating": 1},
    )

    assert response.status_code == 403
    assert response.json()["error"]["code"] == "FORBIDDEN_403"


async def test_submit_feedback_on_nonexistent_target_returns_404(
    logged_in_client: httpx.AsyncClient,
) -> None:
    response = await logged_in_client.post(
        "/api/v1/feedback", json={"target_type": "plan", "target_id": "999999", "rating": 3}
    )
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "NOT_FOUND_404"


async def test_submit_feedback_without_login_returns_401() -> None:
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.post(
            "/api/v1/feedback", json={"target_type": "plan", "target_id": "1", "rating": 3}
        )
    assert response.status_code == 401


async def test_submit_feedback_invalid_rating_returns_422(logged_in_client: httpx.AsyncClient) -> None:
    response = await logged_in_client.post(
        "/api/v1/feedback", json={"target_type": "plan", "target_id": "1", "rating": 10}
    )
    assert response.status_code == 422
