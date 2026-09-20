from __future__ import annotations

import pytest

from src.adapters.mock.course_catalog import MockCourseCatalog
from src.core.errors import NotFound404Error
from src.schemas.common import Day


async def test_search_courses_returns_paginated_items() -> None:
    catalog = MockCourseCatalog()
    page1 = await catalog.search_courses(limit=3)
    assert len(page1.items) == 3
    assert page1.next_cursor is not None

    page2 = await catalog.search_courses(limit=3, cursor=page1.next_cursor)
    assert len(page2.items) > 0
    assert page1.items[0].code != page2.items[0].code


async def test_search_courses_filters_by_query() -> None:
    catalog = MockCourseCatalog()
    page = await catalog.search_courses(q="CPE301")
    assert page.items
    assert all("CPE301" in c.code for c in page.items)


async def test_search_courses_filters_by_day() -> None:
    catalog = MockCourseCatalog()
    page = await catalog.search_courses(day=Day.FRI)
    codes = {c.code for c in page.items}
    assert "CPE303" in codes


async def test_get_sections_returns_matching_sections() -> None:
    catalog = MockCourseCatalog()
    result = await catalog.get_sections("CPE301", "1/2569")
    ids = {s.section_id for s in result.items}
    assert ids == {"CPE301-01", "CPE301-02"}


async def test_get_sections_unknown_course_raises_404() -> None:
    catalog = MockCourseCatalog()
    with pytest.raises(NotFound404Error):
        await catalog.get_sections("XXX999", "1/2569")


async def test_get_sections_by_ids_returns_requested_sections() -> None:
    catalog = MockCourseCatalog()
    sections = await catalog.get_sections_by_ids(["CPE301-01", "GE101-01"])
    assert {s.section_id for s in sections} == {"CPE301-01", "GE101-01"}


async def test_get_sections_by_ids_missing_raises_404() -> None:
    catalog = MockCourseCatalog()
    with pytest.raises(NotFound404Error):
        await catalog.get_sections_by_ids(["NOT-EXIST"])
