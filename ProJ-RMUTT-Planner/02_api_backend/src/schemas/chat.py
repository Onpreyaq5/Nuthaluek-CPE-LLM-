from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field

from src.schemas.common import Day, Page, TermStr


class StudentPreferences(BaseModel):
    free_days: list[Day] = Field(default_factory=list)
    no_early_class: bool = False
    max_credits: int | None = None


class EnrichedStudent(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id_hash: str
    program_id: str
    curriculum_year: int
    year_level: int
    credits_earned: int
    preferences: StudentPreferences


class ChatHistoryItem(BaseModel):
    model_config = ConfigDict(extra="forbid")

    role: Literal["user", "assistant"]
    content: str


class EnrichedChatRequest(BaseModel):
    """สัญญาที่ 02 ส่งให้ 03 — ตาม PLAN.md หัวข้อ 6.1 ห้ามมีชื่อ/รหัสนักศึกษาจริง"""

    model_config = ConfigDict(
        extra="forbid",
        json_schema_extra={
            "example": {
                "request_id": "req_8f2a",
                "session_id": 7,
                "query": "ช่วยวางแผนลงทะเบียนเทอมหน้า อยากว่างวันศุกร์",
                "role": "student",
                "student": {
                    "id_hash": "a91c...e0",
                    "program_id": "CPE-2566",
                    "curriculum_year": 2566,
                    "year_level": 3,
                    "credits_earned": 80,
                    "preferences": {"free_days": ["FRI"], "no_early_class": True, "max_credits": 21},
                },
                "history": [
                    {"role": "user", "content": "เทอมนี้ผมติด F ฟิสิกส์"},
                    {"role": "assistant", "content": "รับทราบครับ ..."},
                ],
                "plan_draft": None,
                "term": "1/2569",
            }
        },
    )

    request_id: str
    session_id: int
    query: str
    role: Literal["student"] = "student"
    student: EnrichedStudent
    history: list[ChatHistoryItem]
    plan_draft: dict | None = None
    term: TermStr


class ChatRequest(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "session_id": None,
                "message": "ช่วยวางแผนลงทะเบียนเทอมหน้า อยากว่างวันศุกร์",
                "plan_draft": None,
            }
        }
    )

    session_id: int | None = None
    message: str
    plan_draft: dict | None = None


class SourceItem(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "title": "ข้อบังคับฯ",
                "section": "ข้อ 18",
                "page": 12,
                "document_id": "doc-regulation-2566",
                "url": None,
            }
        }
    )

    title: str
    section: str
    page: int | None = None
    document_id: str
    url: str | None = None


class SessionEvent(BaseModel):
    type: Literal["session"] = "session"
    session_id: int


class ToolStartEvent(BaseModel):
    type: Literal["tool_start"] = "tool_start"
    tool: str


class ToolEndEvent(BaseModel):
    type: Literal["tool_end"] = "tool_end"
    tool: str


class TokenEvent(BaseModel):
    type: Literal["token"] = "token"
    text: str


class SourcesEvent(BaseModel):
    type: Literal["sources"] = "sources"
    items: list[SourceItem]


class DoneEvent(BaseModel):
    type: Literal["done"] = "done"
    message_id: int


class ErrorEvent(BaseModel):
    type: Literal["error"] = "error"
    code: str
    message: str


ChatSSEEvent = Annotated[
    SessionEvent | ToolStartEvent | ToolEndEvent | TokenEvent | SourcesEvent | DoneEvent | ErrorEvent,
    Field(discriminator="type"),
]


class MessageStatus(str, Enum):
    COMPLETE = "complete"
    INTERRUPTED = "interrupted"
    CANCELLED = "cancelled"


class ChatSessionSummary(BaseModel):
    id: int
    title: str | None = None
    updated_at: datetime


class ChatSessionListResponse(Page[ChatSessionSummary]):
    pass


class ChatMessage(BaseModel):
    id: int
    role: Literal["user", "assistant"]
    content: str
    status: MessageStatus
    sources: list[SourceItem] = Field(default_factory=list)
    created_at: datetime


class ChatMessageListResponse(Page[ChatMessage]):
    pass
