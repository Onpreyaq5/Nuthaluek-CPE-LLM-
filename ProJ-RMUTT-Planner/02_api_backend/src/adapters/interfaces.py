from __future__ import annotations

from collections.abc import AsyncIterator
from typing import Protocol

from pydantic import BaseModel, Field

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
    gpax: float
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
    """โมดูล 07 — อธิบายแผนเป็นภาษาคน"""

    async def explain_plan(
        self, term: str, section_ids: list[str], student: StudentContext
    ) -> ExplainResponse: ...


class LogSink(Protocol):
    """โมดูล 08 — เก็บ log/feedback แบบไม่บล็อกผู้ใช้"""

    async def send_batch(self, events: list[dict]) -> None: ...

    async def send_feedback(self, feedback: dict) -> None: ...


class ChatRouter(Protocol):
    """โมดูล 03 — AI router/agent ใช้ http เสมอ"""

    def stream(self, enriched: EnrichedChatRequest) -> AsyncIterator[dict]: ...
