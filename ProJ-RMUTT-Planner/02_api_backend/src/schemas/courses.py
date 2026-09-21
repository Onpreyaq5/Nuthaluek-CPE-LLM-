from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from src.schemas.common import Day, Page, TimeStr


class MeetingSlot(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={"example": {"day": "MON", "start": "09:00", "end": "11:50", "room": "ENG-301"}}
    )

    day: Day
    start: TimeStr
    end: TimeStr
    room: str | None = None


class Section(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "section_id": "CPE301-01",
                "course_code": "CPE301",
                "course_name_th": "โครงสร้างข้อมูลและขั้นตอนวิธี",
                "teacher": "อ.สมชาย ใจดี",
                "credits": 3,
                "seats_available": 5,
                "seats_total": 40,
                "meetings": [{"day": "MON", "start": "09:00", "end": "11:50", "room": "ENG-301"}],
                "exam": {"day": "SAT", "start": "09:00", "end": "11:00", "room": None},
            }
        }
    )

    section_id: str
    course_code: str
    course_name_th: str
    teacher: str
    credits: int
    seats_available: int
    seats_total: int
    meetings: list[MeetingSlot]
    exam: MeetingSlot | None = None


class Course(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "code": "CPE301",
                "name_th": "โครงสร้างข้อมูลและขั้นตอนวิธี",
                "name_en": "Data Structures and Algorithms",
                "credits": 3,
                "prerequisites": ["CPE201"],
            }
        }
    )

    code: str
    name_th: str
    name_en: str
    credits: int
    prerequisites: list[str] = Field(default_factory=list)


class CourseListResponse(Page[Course]):
    pass


class SectionListResponse(Page[Section]):
    pass
