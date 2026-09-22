"""06_schedule_conflict_engine - Course Data Adapter (Section Provider)
Resolves section IDs to real meeting schedules from 04 or memory fixtures
"""
from __future__ import annotations

import httpx
from typing import Any
from ..config import get_settings
from ..models.schemas import Exam, Meeting, SectionInput
from .providers import DataIncompleteError, SectionNotFoundError, SectionProvider, UpstreamServiceError


def validate_section_schedule(sec: SectionInput) -> None:
    """ตรวจสอบความถูกต้องของข้อมูลเวลาเรียนและเวลาสอบใน Section
    ห้ามถือว่าวิชาที่ไม่มีเวลาเรียนเป็น 'ไม่ชน'
    """
    if not sec.is_online and not sec.meetings:
        raise DataIncompleteError(
            sec.id,
            "Section has no meeting schedule and is not marked as online course"
        )

    for m in sec.meetings:
        if m.day < 0 or m.day > 6:
            raise DataIncompleteError(sec.id, f"Invalid day of week: {m.day}")
        if m.end_min <= m.start_min:
            raise DataIncompleteError(
                sec.id,
                f"Invalid meeting time: end_min ({m.end_min}) <= start_min ({m.start_min})"
            )

    for ex in sec.exams:
        if ex.end_min <= ex.start_min:
            raise DataIncompleteError(
                sec.id,
                f"Invalid exam time: end_min ({ex.end_min}) <= start_min ({ex.start_min})"
            )


class MemorySectionProvider:
    """In-memory Section Provider สำหรับ Unit & Integration Tests"""
    def __init__(self, sections: list[SectionInput] | None = None):
        self._sections: dict[str, SectionInput] = {}
        if sections:
            for s in sections:
                validate_section_schedule(s)
                self._sections[s.id] = s

    def add_section(self, section: SectionInput) -> None:
        validate_section_schedule(section)
        self._sections[section.id] = section

    async def get_sections_by_ids(self, section_ids: list[str], term: str) -> list[SectionInput]:
        result = []
        for sid in section_ids:
            if sid not in self._sections:
                raise SectionNotFoundError(sid)
            result.append(self._sections[sid])
        return result

    async def search_open_sections(self, term: str, course_codes: list[str] | None = None) -> list[SectionInput]:
        if course_codes is None:
            return list(self._sections.values())
        codes_set = set(course_codes)
        return [s for s in self._sections.values() if s.course_code in codes_set]


class HttpSectionProvider:
    """HTTP Client เรียกข้อมูล Section จริงจากโมดูล 04 (04_course_data_services)"""
    def __init__(self, base_url: str | None = None, timeout: float | None = None):
        settings = get_settings()
        self.base_url = (base_url or settings.course_data_url).rstrip("/")
        self.timeout = timeout or settings.http_timeout_seconds

    async def get_sections_by_ids(self, section_ids: list[str], term: str) -> list[SectionInput]:
        settings = get_settings()
        url = f"{self.base_url}/sections/batch"
        payload = {"term": term, "section_ids": section_ids}

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                res = await client.post(url, json=payload)
                if res.status_code == 404:
                    raise SectionNotFoundError(str(section_ids), "One or more sections not found in 04")
                if res.status_code != 200:
                    raise UpstreamServiceError("04_course_data_services", res.status_code, res.text)
                data = res.json()
        except (httpx.ConnectError, httpx.TimeoutException) as exc:
            if settings.demo_mode:
                # อนุญาตเฉพาะเมื่อเปิด DEMO_MODE=True ชัดเจน
                from ..core.demo_fixtures import get_demo_sections
                demo_map = {s.id: s for s in get_demo_sections()}
                found = []
                for sid in section_ids:
                    if sid in demo_map:
                        found.append(demo_map[sid])
                    else:
                        raise SectionNotFoundError(sid, "Not found in demo dataset")
                return found
            raise UpstreamServiceError("04_course_data_services", 503, f"Cannot connect to 04: {exc}")

        sections = []
        for item in data.get("sections", []):
            sec = SectionInput.model_validate(item)
            validate_section_schedule(sec)
            sections.append(sec)

        # ตรวจสอบว่าได้ section ครบตามที่ขอหรือไม่
        resolved_ids = {s.id for s in sections}
        for sid in section_ids:
            if sid not in resolved_ids:
                raise SectionNotFoundError(sid)

        return sections

    async def search_open_sections(self, term: str, course_codes: list[str] | None = None) -> list[SectionInput]:
        settings = get_settings()
        url = f"{self.base_url}/courses/search"
        payload = {"term": term, "course_codes": course_codes or []}

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                res = await client.post(url, json=payload)
                if res.status_code != 200:
                    raise UpstreamServiceError("04_course_data_services", res.status_code, res.text)
                data = res.json()
        except (httpx.ConnectError, httpx.TimeoutException) as exc:
            if settings.demo_mode:
                from ..core.demo_fixtures import get_demo_sections
                demo_list = get_demo_sections()
                if course_codes:
                    c_set = set(course_codes)
                    return [s for s in demo_list if s.course_code in c_set]
                return demo_list
            raise UpstreamServiceError("04_course_data_services", 503, f"Cannot connect to 04: {exc}")

        sections = []
        for item in data.get("sections", []):
            sec = SectionInput.model_validate(item)
            validate_section_schedule(sec)
            sections.append(sec)

        return sections
