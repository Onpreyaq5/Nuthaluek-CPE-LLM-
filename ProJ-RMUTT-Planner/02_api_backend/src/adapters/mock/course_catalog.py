from __future__ import annotations

import base64

from src.core.errors import NotFound404Error
from src.schemas.common import Day
from src.schemas.courses import CourseListResponse, Section, SectionListResponse

from .data import COURSES, SECTIONS


def _encode_cursor(offset: int) -> str:
    return base64.urlsafe_b64encode(str(offset).encode()).decode()


def _decode_cursor(cursor: str | None) -> int:
    if not cursor:
        return 0
    return int(base64.urlsafe_b64decode(cursor.encode()).decode())


class MockCourseCatalog:
    async def search_courses(
        self,
        *,
        q: str | None = None,
        term: str | None = None,
        day: Day | None = None,
        teacher: str | None = None,
        cursor: str | None = None,
        limit: int = 20,
    ) -> CourseListResponse:
        courses = list(COURSES.values())

        if q:
            needle = q.strip().lower()
            courses = [
                c for c in courses
                if needle in c.code.lower() or needle in c.name_th or needle in c.name_en.lower()
            ]

        if day is not None or teacher is not None:
            matching_codes = {
                s.course_code
                for s in SECTIONS.values()
                if (day is None or any(m.day == day for m in s.meetings))
                and (teacher is None or teacher.strip().lower() in s.teacher.lower())
            }
            courses = [c for c in courses if c.code in matching_codes]

        offset = _decode_cursor(cursor)
        page = courses[offset : offset + limit]
        next_offset = offset + limit
        next_cursor = _encode_cursor(next_offset) if next_offset < len(courses) else None
        return CourseListResponse(items=page, next_cursor=next_cursor)

    async def get_sections(self, code: str, term: str) -> SectionListResponse:
        if code not in COURSES:
            raise NotFound404Error("ไม่พบรายวิชานี้", details={"course_code": code})
        sections = [s for s in SECTIONS.values() if s.course_code == code]
        return SectionListResponse(items=sections, next_cursor=None)

    async def get_sections_by_ids(self, ids: list[str]) -> list[Section]:
        missing = [i for i in ids if i not in SECTIONS]
        if missing:
            raise NotFound404Error("ไม่พบ section บางรายการ", details={"section_ids": missing})
        return [SECTIONS[i] for i in ids]
