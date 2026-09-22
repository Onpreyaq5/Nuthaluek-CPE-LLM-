from __future__ import annotations

from collections.abc import AsyncIterator
from typing import Protocol

from pydantic import BaseModel, Field

from src.core.errors import Upstream502Error
from src.schemas.chat import EnrichedChatRequest, StudentPreferences
from src.schemas.common import Day
from src.schemas.courses import CourseListResponse, Section, SectionListResponse
from src.schemas.plans import PlanValidateResponse
from src.schemas.students import ExplainResponse, GeneratedPlan, ImportResult, TranscriptResponse


class StudentContext(BaseModel):
    """ข้อมูลนักศึกษาที่ 05 คืนให้ 02 ใช้ต่อ (ภายในเท่านั้น ไม่ใช่ response ของ endpoint ไหนตรงๆ)

    program_name/gpax/credits_remaining เพิ่มเข้ามาใน Prompt 9 เพื่อให้พอสร้าง StudentProfile ได้
    (PLAN.md บอกว่า GET /students/me/profile มาจาก "DB + adapter 05" แต่ 02 ไม่ได้เก็บข้อมูลวิชาการพวกนี้
    ไว้เองเลย จึงต้องให้ 05 เป็นคนคืนมาให้ครบ ไม่ใช่เดาว่า DB เก็บอะไรเพิ่ม)
    """

    student_id: str
    id_hash: str
    program_id: str
    program_name: str
    curriculum_year: int
    year_level: int
    credits_earned: int
    credits_remaining: int
    # 05 ส่ง null ให้นักศึกษาที่ยังไม่มีเกรดเลย (ไม่มีเกรด = ยังคำนวณ GPAX ไม่ได้ ไม่ใช่ 0.00)
    # ถ้าบังคับเป็น float แชตทั้งเส้นจะพังเป็น 500 ตั้งแต่ขั้นดึงข้อมูลนักศึกษา
    gpax: float | None = None
    completed_course_codes: list[str] = Field(default_factory=list)
    preferences: StudentPreferences


class CourseCatalog(Protocol):
    """โมดูล 04 — ข้อมูลวิชา/section"""

    async def search_courses(
        self,
        *,
        q: str | None = None,
        term: str | None = None,
        day: Day | None = None,
        teacher: str | None = None,
        cursor: str | None = None,
        limit: int = 20,
    ) -> CourseListResponse: ...

    async def get_sections(self, code: str, term: str) -> SectionListResponse: ...

    async def get_sections_by_ids(self, ids: list[str]) -> list[Section]: ...


class StudentData(Protocol):
    """โมดูล 05 — ข้อมูลนักศึกษา + parse ผลการเรียน"""

    async def get_context(self, student_id: str) -> StudentContext: ...

    async def get_transcript(self, student_id: str) -> TranscriptResponse: ...

    async def import_graduate_check(self, raw: bytes) -> ImportResult: ...


class PlanEngine(Protocol):
    """โมดูล 06 — ตรวจ/สร้างแผนการเรียน (02 ห้ามตัดสินเอง)"""

    async def validate(
        self, term: str, section_ids: list[str], student: StudentContext
    ) -> PlanValidateResponse: ...

    async def generate(
        self,
        term: str,
        preferences: StudentPreferences | None,
        student: StudentContext,
        must_include: list[str],
        exclude: list[str],
    ) -> list[GeneratedPlan]: ...


class Explainer(Protocol):
    """โมดูล 07 — อธิบายแผนเป็นภาษาคน

    validation (ผล 06 ล่าสุด) ต้องส่งไปด้วยเสมอเมื่อมี — ไม่งั้น 07 ไม่มีทาง verdict ตามจริงได้ (จะได้
    "unknown" เสมอ) เป็น None ได้เฉพาะกรณีที่ไม่มีผลตรวจจริงๆ (ไม่ควรเกิดในโค้ด 02 เอง — caller ทุกจุดควร
    validate/มี validation อยู่แล้วก่อนเรียกเสมอ)"""

    async def explain_plan(
        self,
        term: str,
        section_ids: list[str],
        student: StudentContext,
        validation: PlanValidateResponse | None = None,
    ) -> ExplainResponse: ...


class LogSink(Protocol):
    """โมดูล 08 — เก็บ log/feedback แบบไม่บล็อกผู้ใช้"""

    async def send_batch(self, events: list[dict]) -> None: ...

    async def send_feedback(self, feedback: dict) -> None: ...


class ChatRouter(Protocol):
    """โมดูล 03 — AI router/agent ใช้ http เสมอ

    stream() คืน event "ภายใน" ของ router เท่านั้น (ไม่ใช่ public SSE event ที่ส่งให้ frontend ตรงๆ) —
    แต่ละ dict มี key "kind" (ไม่ใช่ "type" แบบ public event) เป็นตัวจำแนก: tool_start/tool_end (มี "tool"),
    clarify (มี "question"), refusal (มี "message"), context_ready (มี "intent","context","question"),
    router_done (มี "outcome": "clarify"|"context_ready"|"refused"|None), error (มี "message")
    ผู้เรียกต้องผ่าน src.services.chat_orchestrator ก่อนเสมอ ไม่ส่ง event เหล่านี้ตรงไปหา frontend"""

    def stream(self, enriched: EnrichedChatRequest) -> AsyncIterator[dict]: ...


class AnswerGenerator(Protocol):
    """โมดูล 07 — สร้างคำตอบจริงจาก context ที่ 03 รวบรวมมา (ใช้เฉพาะตอน router จบด้วย context_ready)

    generate() คืน event แบบ public event บางส่วน: {"type":"token","text":...} หรือ
    {"type":"sources","items":[...]} เท่านั้น (ไม่ต้องคืน "done" — orchestrator เป็นคนปิดท้ายเอง)"""

    def generate(
        self, *, question: str, context: dict, history: list[dict]
    ) -> AsyncIterator[dict]: ...


class NotReadyAnswerGenerator:
    """placeholder ตอนที่ยังไม่มี contract จริงจากทีม 07 — production path ต้องได้ error ชัดเจน
    ห้ามเงียบๆ แกล้งตอบสำเร็จ (ดู PLAN งานแก้ chat adapter รอบ 2) แทนที่ตัวนี้เมื่อ 07 ยืนยัน interface แล้ว"""

    async def generate(
        self, *, question: str, context: dict, history: list[dict]
    ) -> AsyncIterator[dict]:
        raise Upstream502Error(
            "โมดูล 07 (ตัวสร้างคำตอบ) ยังไม่มี contract ที่ยืนยันแล้วจากทีม 07 จึงยังเรียกใช้งานจริงไม่ได้",
            details={"module": "07"},
        )
        yield  # pragma: no cover - ทำให้เป็น async generator function
