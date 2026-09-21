from __future__ import annotations

import json
from pathlib import Path

import pytest
from pydantic import TypeAdapter

from src.schemas.auth import LoginResponse, MeResponse
from src.schemas.chat import (
    ChatMessageListResponse,
    ChatSessionListResponse,
    ChatSSEEvent,
    EnrichedChatRequest,
    ErrorEvent,
)
from src.schemas.courses import CourseListResponse, SectionListResponse
from src.schemas.envelope import ErrorEnvelope, SuccessEnvelope
from src.schemas.feedback import FeedbackResponse
from src.schemas.plans import PlanCreateResponse, PlanDetail, PlanListResponse, PlanValidateResponse
from src.schemas.students import (
    AutoPlanResponse,
    ExplainResponse,
    ImportResult,
    StudentProfile,
    TranscriptResponse,
)

FIXTURES_DIR = Path(__file__).resolve().parents[2] / "fixtures"

SUCCESS_FIXTURES: dict[str, type] = {
    "auth/login.success.json": LoginResponse,
    "auth/me.success.json": MeResponse,
    "auth/logout.success.json": dict,
    "courses/list_courses.success.json": CourseListResponse,
    "courses/sections.success.json": SectionListResponse,
    "plans/validate.success.json": PlanValidateResponse,
    "plans/validate.conflict.json": PlanValidateResponse,
    "plans/create.success.json": PlanCreateResponse,
    "plans/list.success.json": PlanListResponse,
    "plans/detail.success.json": PlanDetail,
    "plans/delete.success.json": dict,
    "plans/auto.success.json": AutoPlanResponse,
    "plans/explain.success.json": ExplainResponse,
    "chat/sessions.success.json": ChatSessionListResponse,
    "chat/messages.success.json": ChatMessageListResponse,
    "students/profile.success.json": StudentProfile,
    "students/transcript.success.json": TranscriptResponse,
    "students/import.success.json": ImportResult,
    "feedback/submit.success.json": FeedbackResponse,
}

ERROR_FIXTURES: list[str] = [
    "auth/login.error.json",
    "auth/me.error.json",
    "courses/list_courses.error.json",
    "courses/sections.error.json",
    "plans/validate.error.json",
    "plans/validate.not_found.json",
    "plans/create.error.json",
    "plans/list.error.json",
    "plans/detail.error.json",
    "plans/delete.error.json",
    "plans/auto.error.json",
    "plans/explain.error.json",
    "chat/sessions.error.json",
    "chat/messages.error.json",
    "students/profile.error.json",
    "students/transcript.error.json",
    "students/import.error.json",
    "feedback/submit.error.json",
]

SSE_FIXTURES: list[str] = [
    "sse/normal.txt",
    "sse/error_mid_stream.txt",
    "sse/closed_without_done.txt",
    "sse/sources_thai.txt",
]


def _load(relative_path: str) -> dict:
    return json.loads((FIXTURES_DIR / relative_path).read_text(encoding="utf-8"))


@pytest.mark.parametrize("relative_path,data_model", SUCCESS_FIXTURES.items())
def test_success_fixture_matches_schema(relative_path: str, data_model: type) -> None:
    payload = _load(relative_path)
    SuccessEnvelope[data_model].model_validate(payload)


@pytest.mark.parametrize("relative_path", ERROR_FIXTURES)
def test_error_fixture_matches_envelope(relative_path: str) -> None:
    payload = _load(relative_path)
    ErrorEnvelope.model_validate(payload)


def test_enriched_chat_request_fixture_matches_schema() -> None:
    payload = _load("chat/enriched_request.example.json")
    EnrichedChatRequest.model_validate(payload)


@pytest.mark.parametrize("relative_path", SSE_FIXTURES)
def test_sse_fixture_events_match_schema(relative_path: str) -> None:
    adapter = TypeAdapter(ChatSSEEvent)
    text = (FIXTURES_DIR / relative_path).read_text(encoding="utf-8")
    chunks = [chunk for chunk in text.strip().split("\n\n") if chunk.strip()]
    assert chunks, f"ไม่มี event ใน {relative_path}"

    for chunk in chunks:
        assert chunk.startswith("data: "), f"event ต้องขึ้นต้นด้วย 'data: ' ใน {relative_path}"
        event = json.loads(chunk[len("data: ") :])
        if event.get("type") == "error":
            ErrorEvent.model_validate(event)
        else:
            adapter.validate_python(event)
