"""Schema ของโมดูล 07 — ชื่อ field ตรงกับที่โมดูล 03 และ 02 เรียกใช้"""
from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field, model_validator


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
# ชื่อปัญหาของ 06 (message_key / type) -> รหัส C1-C6 / W1-W5
# ยกจาก src/core/*.py ของโมดูล 06
MESSAGE_KEY_TO_CODE = {
    "time_clash": "C1", "exam_clash": "C2", "prereq_fail": "C3",
    "credit_limit_exceeded": "C4", "credit_limit_under": "C4", "credit_limit": "C4",
    "already_passed": "C5", "duplicate_section": "C5", "duplicate": "C5", "seat_full": "C6",
    "long_stretch": "W1", "large_gap": "W2", "busy_preferred_free_day": "W3",
    "early_morning_class": "W3", "rush_building_move": "W4", "heavy_days": "W5",
}


class ConflictIn(BaseModel):
    """รูปแบบเดียวกับ ConflictDetail / WarningDetail ของโมดูล 06

    รับรูปแบบที่ 02 ส่งต่อมาด้วย ({type, message, details} และ code / message_th ว่าง)
    ก่อนหน้านี้ 07 อ่านแค่ code กับ message_th หน้า "อธิบายแผน" จึงได้บรรทัดว่าง "- **** —"
    """
    code: str = ""
    severity: str = "ERROR"
    message_key: str = ""
    message_th: str = ""
    message_en: str = ""
    subjects: list[str] = Field(default_factory=list)
    detail: dict[str, Any] = Field(default_factory=dict)
    suggestions: list[dict[str, Any]] = Field(default_factory=list)

    @model_validator(mode="before")
    @classmethod
    def _accept_backend_shape(cls, data: Any) -> Any:
        if not isinstance(data, dict):
            return data
        data = dict(data)
        key = data.get("message_key") or data.get("type") or ""
        if not data.get("message_key") and key:
            data["message_key"] = key
        if not data.get("code"):
            data["code"] = MESSAGE_KEY_TO_CODE.get(key, "")
        if not data.get("message_th") and data.get("message"):
            data["message_th"] = data["message"]
        if not data.get("detail") and isinstance(data.get("details"), dict):
            data["detail"] = data["details"]
        if not data.get("subjects") and isinstance(data.get("section_ids"), list):
            data["subjects"] = data["section_ids"]
        return data


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
