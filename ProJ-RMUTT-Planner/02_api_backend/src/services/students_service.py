from __future__ import annotations

from src.adapters.interfaces import StudentContext, StudentData
from src.core.errors import Validation422Error
from src.schemas.students import ImportResult, StudentProfile, TranscriptResponse

_HTML_MARKERS = (b"<html", b"<!doctype html")
_INVALID_HTML_MESSAGE = "ไฟล์ที่อัปโหลดไม่ใช่ HTML ที่รองรับ"


def _context_to_profile(context: StudentContext) -> StudentProfile:
    return StudentProfile(
        student_id=context.student_id,
        program_id=context.program_id,
        program_name=context.program_name,
        year_level=context.year_level,
        gpax=context.gpax,
        credits_earned=context.credits_earned,
        credits_remaining=context.credits_remaining,
    )


async def get_profile(student_data: StudentData, student_id: str) -> StudentProfile:
    context = await student_data.get_context(student_id)
    return _context_to_profile(context)


async def get_transcript(student_data: StudentData, student_id: str) -> TranscriptResponse:
    return await student_data.get_transcript(student_id)


def ensure_html_content(raw: bytes) -> None:
    """ตรวจเนื้อหาจริงว่าเป็น HTML ไม่เชื่อแค่นามสกุลไฟล์หรือ content-type ที่ client ส่งมา"""
    lowered = raw.lower()
    if not any(marker in lowered for marker in _HTML_MARKERS):
        raise Validation422Error(_INVALID_HTML_MESSAGE)


async def import_graduate_check(
    student_data: StudentData, raw: bytes, student_id: str | None = None
) -> ImportResult:
    ensure_html_content(raw)
    return await student_data.import_graduate_check(raw, student_id=student_id)
