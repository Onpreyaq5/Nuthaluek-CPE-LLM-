from __future__ import annotations

from src.core.config import get_settings
from src.schemas.common import Day
from src.schemas.courses import CourseListResponse, Section, SectionListResponse

from ..inprocess_loader import load_module_package


class InprocessCourseCatalog:
    """เรียก 04 ตรงในโปรเซสเดียวกันผ่าน mod04.adapters.oreg_rmutt เท่าที่มี

    ยังไม่มีโค้ด 04 ให้เรียกจริง (โฟลเดอร์ MODULE_04_DIR เป็น placeholder) — ทุกเมธอดจะ raise
    NotImplementedError/RuntimeError ที่บอกสาเหตุชัดเจนจนกว่าโมดูล 04 จะถูกวางไว้จริง
    """

    def __init__(self) -> None:
        self._mod = load_module_package(get_settings().MODULE_04_DIR, "mod04")

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
        raise NotImplementedError(
            "mod04.adapters.oreg_rmutt ยังไม่มีฟังก์ชัน search_courses ให้เรียก — ใช้ ADAPTER_04=mock หรือ http แทน"
        )

    async def get_sections(self, code: str, term: str) -> SectionListResponse:
        raise NotImplementedError(
            "mod04.adapters.oreg_rmutt ยังไม่มีฟังก์ชัน get_sections ให้เรียก — ใช้ ADAPTER_04=mock หรือ http แทน"
        )

    async def get_sections_by_ids(self, ids: list[str]) -> list[Section]:
        raise NotImplementedError(
            "mod04.adapters.oreg_rmutt ยังไม่มีฟังก์ชัน get_sections_by_ids ให้เรียก — "
            "ใช้ ADAPTER_04=mock หรือ http แทน"
        )
