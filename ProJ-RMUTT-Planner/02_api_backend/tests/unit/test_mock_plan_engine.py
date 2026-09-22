from __future__ import annotations

from src.adapters.mock.data import SECTIONS
from src.adapters.mock.plan_engine import MockPlanEngine
from src.adapters.mock.student_data import MockStudentData
from src.schemas.common import hhmm_to_minutes


async def _student():
    return await MockStudentData().get_context("6500000000")


def _has_overlap(section_ids: list[str]) -> bool:
    slots = []
    for sid in section_ids:
        for m in SECTIONS[sid].meetings:
            slots.append((m.day, hhmm_to_minutes(m.start), hhmm_to_minutes(m.end)))
    for i in range(len(slots)):
        for j in range(i + 1, len(slots)):
            day_i, start_i, end_i = slots[i]
            day_j, start_j, end_j = slots[j]
            if day_i == day_j and start_i < end_j and start_j < end_i:
                return True
    return False


async def test_time_overlap_c1_detected() -> None:
    engine = MockPlanEngine()
    student = await _student()
    result = await engine.validate("1/2569", ["CPE201-01", "CPE301-01"], student)
    assert any(c.type == "TIME_OVERLAP" for c in result.conflicts)
    assert result.summary.is_valid is False


async def test_prerequisite_missing_c3_detected() -> None:
    engine = MockPlanEngine()
    student = await _student()  # ยังไม่ผ่าน CPE301
    result = await engine.validate("1/2569", ["CPE401-01"], student)
    assert any(c.type == "PREREQUISITE_MISSING" for c in result.conflicts)


async def test_credit_limit_c4_detected() -> None:
    engine = MockPlanEngine()
    student = await _student()
    section_ids = [
        "CPE201-01", "CPE301-02", "CPE302-02", "CPE303-01",
        "CPE305-01", "GE101-01", "GE102-01", "CPE401-01",
    ]
    result = await engine.validate("1/2569", section_ids, student)
    assert any(c.type == "CREDIT_LIMIT_EXCEEDED" for c in result.conflicts)


async def test_seat_full_c6_detected() -> None:
    engine = MockPlanEngine()
    student = await _student()
    result = await engine.validate("1/2569", ["CPE302-01"], student)
    assert any(c.type == "SEAT_FULL" for c in result.conflicts)


async def test_no_conflicts_when_sections_are_compatible() -> None:
    engine = MockPlanEngine()
    student = await _student()
    result = await engine.validate("1/2569", ["CPE301-02", "GE101-01"], student)
    assert result.conflicts == []
    assert result.summary.is_valid is True


async def test_generate_returns_three_non_conflicting_plans() -> None:
    engine = MockPlanEngine()
    student = await _student()
    plans = await engine.generate("1/2569", None, student, must_include=[], exclude=[])
    assert len(plans) == 3
    for plan in plans:
        assert len(plan.sections) == len(set(plan.sections))
        assert not _has_overlap(plan.sections)
        assert plan.total_credits <= 21
