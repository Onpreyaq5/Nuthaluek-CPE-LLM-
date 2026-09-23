from __future__ import annotations

from src.core.config import get_settings
from src.core.errors import NotFound404Error
from src.schemas.common import Day
from src.schemas.courses import CourseListResponse, Section, SectionListResponse

from ..http_base import HttpAdapterClient, raise_for_upstream

# ปลายทางของ 04 ยังไม่มีสัญญาจริง — PLACEHOLDER ตาม RESTful convention ทั่วไป (ยืนยันกับทีม 04 ทีหลัง)
PATH_SEARCH_COURSES = "/courses"
PATH_GET_SECTIONS = "/courses/{code}/sections"
PATH_SECTIONS_BULK = "/sections/bulk"


class HttpCourseCatalog:
    def __init__(self) -> None:
        settings = get_settings()
        self._client = HttpAdapterClient(
            base_url=settings.COURSE_CATALOG_URL, module="04", timeout_policy=settings.timeouts.read
        )

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
        params = {
            "q": q,
            "term": term,
            "day": day.value if day else None,
            "teacher": teacher,
            "cursor": cursor,
            "limit": limit,
        }
        params = {k: v for k, v in params.items() if v is not None}
        response = await self._client.request("GET", PATH_SEARCH_COURSES, params=params)
        raise_for_upstream(response, "04")
        return CourseListResponse.model_validate(response.json())

    async def get_sections(self, code: str, term: str) -> SectionListResponse:
        response = await self._client.request(
            "GET", PATH_GET_SECTIONS.format(code=code), params={"term": term}
        )
        if response.status_code == 404:
            raise NotFound404Error("ไม่พบรายวิชานี้", details={"course_code": code})
        raise_for_upstream(response, "04")
        return SectionListResponse.model_validate(response.json())

    async def get_sections_by_ids(self, ids: list[str]) -> list[Section]:
        response = await self._client.request("POST", PATH_SECTIONS_BULK, json={"ids": ids})
        raise_for_upstream(response, "04")
        items = response.json().get("items", [])
        return [Section.model_validate(item) for item in items]
