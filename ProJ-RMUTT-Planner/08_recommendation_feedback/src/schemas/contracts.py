from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from src.services.privacy import is_probably_raw_student_id


class EventCreate(BaseModel):
    model_config = ConfigDict(extra="allow")

    event_id: str | None = Field(default=None, max_length=64)
    request_id: str | None = Field(default=None, max_length=128)
    student_hash: str | None = Field(default=None, max_length=128)
    service: str = Field(default="unknown", max_length=64)
    action: str = Field(min_length=1, max_length=128)
    intent: str | None = Field(default=None, max_length=128)
    tools: list[str] = Field(default_factory=list, max_length=50)
    latency_ms: int | None = Field(default=None, ge=0)
    tokens_in: int | None = Field(default=None, ge=0)
    tokens_out: int | None = Field(default=None, ge=0)
    cost_est: Decimal | None = Field(default=None, ge=0)
    status: str = Field(default="success", max_length=32)
    payload: dict[str, Any] = Field(default_factory=dict)
    occurred_at: datetime | None = None

    @model_validator(mode="before")
    @classmethod
    def support_gateway_aliases(cls, data: Any):
        if not isinstance(data, dict):
            return data
        value = dict(data)
        value.setdefault("action", value.pop("event", None))
        value.setdefault("student_hash", value.pop("id_hash", None))
        known = set(cls.model_fields)
        extras = {key: item for key, item in value.items() if key not in known}
        value = {key: item for key, item in value.items() if key in known}
        value["payload"] = {**value.get("payload", {}), **extras}
        return value

    @model_validator(mode="after")
    def reject_raw_student_id(self):
        if is_probably_raw_student_id(self.student_hash):
            raise ValueError("student_hash must be a hash, not a raw student id")
        return self


class EventBatchCreate(BaseModel):
    events: list[EventCreate] = Field(min_length=1)


class FeedbackCreate(BaseModel):
    source_feedback_id: str | None = Field(default=None, max_length=64)
    request_id: str | None = Field(default=None, max_length=128)
    student_hash: str | None = Field(default=None, max_length=128)
    target_type: Literal["plan", "chat_message", "explanation"]
    target_id: str = Field(min_length=1, max_length=128)
    rating: int = Field(ge=1, le=5)
    reason: str | None = Field(default=None, max_length=2000)
    preference_signal: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def reject_raw_student_id(self):
        if is_probably_raw_student_id(self.student_hash):
            raise ValueError("student_hash must be a hash, not a raw student id")
        return self


class PlanSection(BaseModel):
    section_id: str
    course_code: str
    course_name: str | None = None
    credits: int = Field(ge=0)
    meetings: list[dict[str, Any]] = Field(default_factory=list)


class PlanCandidate(BaseModel):
    plan_id: str | None = None
    name: str
    term: str
    sections: list[PlanSection]
    summary: dict[str, Any] = Field(default_factory=dict)
    rule_reasons: list[dict[str, Any]] = Field(default_factory=list)
    risks: list[str] = Field(default_factory=list)
    explanation: str | None = None


class RecommendationComposeRequest(BaseModel):
    candidates: list[PlanCandidate] = Field(min_length=1, max_length=5)


class AcademicEvent(BaseModel):
    event_type: Literal["registration", "withdraw"]
    event_date: date
    description: str | None = None


class PlannedSectionState(BaseModel):
    section_id: str
    course_code: str
    seats_remaining: int | None = Field(default=None, ge=0)
    cancelled: bool = False
    schedule_changed: bool = False


class AlertEvaluationRequest(BaseModel):
    student_hash: str
    as_of: date = Field(default_factory=date.today)
    academic_events: list[AcademicEvent] = Field(default_factory=list)
    planned_sections: list[PlannedSectionState] = Field(default_factory=list)
    planned_credits: int | None = Field(default=None, ge=0)
    min_credits: int = Field(default=9, ge=0)

    @model_validator(mode="after")
    def reject_raw_student_id(self):
        if is_probably_raw_student_id(self.student_hash):
            raise ValueError("student_hash must be a hash, not a raw student id")
        return self
