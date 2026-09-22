"""06_schedule_conflict_engine - Provider Protocols & Exceptions
"""
from __future__ import annotations

from typing import Protocol
from ..models.schemas import SectionInput, StudentContextInput


class SectionNotFoundError(Exception):
    """รหัส section หรือ course code ไม่พบในฐานข้อมูล"""
    def __init__(self, section_id: str, message: str = ""):
        self.section_id = section_id
        super().__init__(message or f"Section '{section_id}' not found")


class DataIncompleteError(Exception):
    """ข้อมูล section ไม่ครบถ้วน (เช่น ไม่มีเวลาเรียน และไม่ได้เป็น online)"""
    def __init__(self, section_id: str, reason: str):
        self.section_id = section_id
        self.reason = reason
        super().__init__(f"Incomplete schedule data for '{section_id}': {reason}")


class UpstreamServiceError(Exception):
    """บริการภายนอก (04/05) ตอบสนองผิดพลาดหรือ timeout"""
    def __init__(self, service: str, status_code: int, message: str):
        self.service = service
        self.status_code = status_code
        super().__init__(f"Upstream {service} error ({status_code}): {message}")


class StudentContextNotFoundError(Exception):
    """ไม่พบประวัตินักศึกษาจาก identifier หรือ hash"""
    def __init__(self, student_ref: str):
        self.student_ref = student_ref
        super().__init__(f"Student context not found for identifier: {student_ref}")


class SectionProvider(Protocol):
    async def get_sections_by_ids(self, section_ids: list[str], term: str) -> list[SectionInput]:
        """Resolve section IDs เป็นรายการ SectionInput ที่มีข้อมูลเวลาเรียน/สอบ/ที่นั่งจริงครบถ้วน"""
        ...

    async def search_open_sections(self, term: str, course_codes: list[str] | None = None) -> list[SectionInput]:
        """ค้นหากลุ่มเรียนที่เปิดสอนจริงในเทอมที่ระบุ"""
        ...


class StudentContextProvider(Protocol):
    async def get_context(self, student_ref: str) -> StudentContextInput:
        """ดึงประวัติการเรียน (ผ่าน prereq, เคยได้ F/W) จาก student identifier หรือ hash"""
        ...
