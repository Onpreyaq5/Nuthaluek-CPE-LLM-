from __future__ import annotations

import json
from pathlib import Path

from src.core.masking import hash_student_id
from src.schemas.chat import StudentPreferences
from src.schemas.common import Day
from src.schemas.students import ImportResult, TranscriptResponse

from ..interfaces import StudentContext

_FIXTURES_DIR = Path(__file__).resolve().parents[3] / "fixtures"


class MockStudentData:
    async def get_context(self, student_id: str) -> StudentContext:
        return StudentContext(
            student_id=student_id,
            id_hash=hash_student_id(student_id),
            program_id="CPE-2566",
            program_name="วิศวกรรมคอมพิวเตอร์",
            curriculum_year=2566,
            year_level=3,
            credits_earned=80,
            credits_remaining=56,
            gpax=3.42,
            completed_course_codes=["CPE201", "GE101"],
            preferences=StudentPreferences(free_days=[Day.FRI], no_early_class=False, max_credits=21),
        )

    async def get_transcript(self, student_id: str) -> TranscriptResponse:
        payload = json.loads(
            (_FIXTURES_DIR / "students" / "transcript.success.json").read_text(encoding="utf-8")
        )
        return TranscriptResponse.model_validate(payload["data"])

    async def import_graduate_check(self, raw: bytes) -> ImportResult:
        payload = json.loads((_FIXTURES_DIR / "students" / "import.success.json").read_text(encoding="utf-8"))
        return ImportResult.model_validate(payload["data"])
