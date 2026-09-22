"""Tests for SectionProvider and StudentContextProvider adapters
Verifies fail-closed behavior, incomplete data rejection, and zero quiet mock fallbacks in production
"""
import asyncio
import pydantic
import pytest
from src.adapters.course_data import MemorySectionProvider, validate_section_schedule
from src.adapters.providers import (
    DataIncompleteError,
    SectionNotFoundError,
    StudentContextNotFoundError,
)
from src.adapters.student_data import MemoryStudentContextProvider
from src.models.schemas import Meeting, SectionInput, StudentContextInput


def test_section_without_meetings_and_not_online_fails():
    """Section ไม่มีเวลาเรียน และไม่ได้เป็น online ต้องถือว่าข้อมูลไม่ครบ ห้ามตีความว่าไม่ชน"""
    sec = SectionInput(
        id="CPE999-01",
        course_code="CPE999",
        section="01",
        is_online=False,
        meetings=[],
    )
    with pytest.raises(DataIncompleteError) as exc_info:
        validate_section_schedule(sec)
    assert "no meeting schedule" in str(exc_info.value)


def test_section_online_without_meetings_passes():
    """วิชา online/asynchronous สามารถไม่มี meeting ได้อย่างถูกต้อง"""
    sec = SectionInput(
        id="CPE999-01",
        course_code="CPE999",
        section="01",
        is_online=True,
        meetings=[],
    )
    validate_section_schedule(sec)


def test_invalid_time_range_fails():
    """end_min <= start_min ต้อง raise DataIncompleteError"""
    sec = SectionInput(
        id="CPE999-01",
        course_code="CPE999",
        section="01",
        meetings=[Meeting(day=0, start_min=600, end_min=500)],  # เวลาสิ้นสุดก่อนเวลาเริ่ม
    )
    with pytest.raises(DataIncompleteError):
        validate_section_schedule(sec)


def test_invalid_day_fails():
    """day อยู่นอกช่วง 0-6 ต้องถูก reject โดย Pydantic หรือ validation"""
    with pytest.raises((pydantic.ValidationError, DataIncompleteError)):
        Meeting(day=7, start_min=540, end_min=720)


def test_memory_section_provider_missing_id():
    """หาก ID ใด ID หนึ่งหาไม่พบ ต้อง raise SectionNotFoundError"""
    provider = MemorySectionProvider([
        SectionInput(
            id="CPE101-01",
            course_code="CPE101",
            section="01",
            meetings=[Meeting(day=0, start_min=540, end_min=720)],
        )
    ])
    with pytest.raises(SectionNotFoundError) as exc:
        asyncio.run(provider.get_sections_by_ids(["CPE101-01", "CPE102-01"], "1/2569"))
    assert exc.value.section_id == "CPE102-01"


def test_memory_student_provider_missing_hash():
    """หาก student hash หาไม่พบ ต้อง raise StudentContextNotFoundError"""
    provider = MemoryStudentContextProvider({})
    with pytest.raises(StudentContextNotFoundError):
        asyncio.run(provider.get_context("unknown_hash_123"))
