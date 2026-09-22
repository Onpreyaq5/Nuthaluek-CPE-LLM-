"""Schema ของโมดูล 07 — ชื่อ field ตรงกับที่โมดูล 03 และ 02 เรียกใช้"""
from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field


# ── เอกสารที่ค้นเจอ ──────────────────────────────────────────────
class Source(BaseModel):
    """แหล่งอ้างอิงที่แนบไปกับคำตอบทุกครั้งที่อ้างระเบียบ"""
    doc_id: str
    title: str
    section: str = ""
    doc_type: str = ""
    effective_year: int | None = None
    score: float = 0.0


class Chunk(Source):
    text: str = ""


class KnowledgeSearchRequest(BaseModel):
    query: str = Field(..., min_length=1)
    top_k: int = Field(default=6, ge=1, le=50)
    doc_type: str | None = Field(default=None, description="regulation | curriculum | calendar | faq")
    effective_year: int | None = Field(default=None, description="กรองตามปีหลักสูตรของนักศึกษา")
    program_id: str | None = None


class KnowledgeSearchResponse(BaseModel):
    ok: bool = True
    query: str
    found: bool
    chunks: list[Chunk] = Field(default_factory=list)
    top_score: float = 0.0


# ── การสร้างคำตอบ ───────────────────────────────────────────────
class GenerateRequest(BaseModel):
    question: str = Field(..., min_length=1)
    context: dict[str, Any] = Field(
        default_factory=dict,
        description="ก้อน context จาก 03: student profile, plan, ผลจาก 06, ประวัติแชต",
    )
    top_k: int = Field(default=6, ge=1, le=20)
    language: Literal["th", "en"] = "th"


class GenerateResponse(BaseModel):
    ok: bool = True
    answer: str
    sources: list[Source] = Field(default_factory=list)
    grounded: bool = Field(..., description="True = มีหลักฐานรองรับ, False = ไม่พบข้อมูลจึงไม่ตอบ")
    provider: str
    disclaimer: str


# ── อธิบายผลจากโมดูล 06 ─────────────────────────────────────────
class ConflictIn(BaseModel):
    """รูปแบบเดียวกับ ConflictDetail / WarningDetail ของโมดูล 06"""
    code: str
    severity: str = "ERROR"
    message_key: str = ""
    message_th: str = ""
    message_en: str = ""
    subjects: list[str] = Field(default_factory=list)
    detail: dict[str, Any] = Field(default_factory=dict)
    suggestions: list[dict[str, Any]] = Field(default_factory=list)


class PlanItemIn(BaseModel):
    course_code: str = ""
    section: str = ""
    course_name: str = ""
    credits: int = 0


class ExplainPlanRequest(BaseModel):
    term: str = ""
    plan: list[PlanItemIn] = Field(default_factory=list)
    # None = ผู้เรียกยังไม่ได้ตรวจตารางชน  /  [] = ตรวจแล้วไม่เจอปัญหา
    # แยกสองกรณีนี้ให้ชัด ไม่งั้นแผนที่ยังไม่ถูกตรวจจะถูกรายงานว่า "ใช้ได้"
    conflicts: list[ConflictIn] | None = None
    warnings: list[ConflictIn] | None = None
    total_credits: int | None = None
    # รับ section_ids ได้ด้วย เพราะโมดูล 02 ส่งมาแบบนี้
    section_ids: list[str] = Field(default_factory=list)
    student_context: dict[str, Any] = Field(default_factory=dict)
    student: dict[str, Any] = Field(default_factory=dict)
    language: Literal["th", "en"] = "th"


class ExplainPlanResponse(BaseModel):
    ok: bool = True
    verdict: Literal["ok", "blocked", "warning", "unknown"]
    headline: str
    explanation: str
    next_steps: list[str] = Field(default_factory=list)
    credit_check: dict[str, Any] = Field(default_factory=dict)
    sources: list[Source] = Field(default_factory=list)
    provider: str
    disclaimer: str


class IngestResponse(BaseModel):
    ok: bool = True
    documents: int
    chunks: int
    files: list[str] = Field(default_factory=list)
