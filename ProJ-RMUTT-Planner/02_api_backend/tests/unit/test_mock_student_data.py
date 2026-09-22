from __future__ import annotations

from src.adapters.mock.student_data import MockStudentData


async def test_get_context_returns_consistent_hash() -> None:
    adapter = MockStudentData()
    ctx1 = await adapter.get_context("6500000000")
    ctx2 = await adapter.get_context("6500000000")
    assert ctx1.id_hash == ctx2.id_hash
    assert ctx1.student_id == "6500000000"


async def test_import_graduate_check_returns_fixture_shaped_result() -> None:
    adapter = MockStudentData()
    result = await adapter.import_graduate_check(b"<html></html>")
    assert result.imported_courses > 0
