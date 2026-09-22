"""In-memory course/section store — ข้อมูลตัวอย่างไปก่อน ถ้ามีไฟล์ HTML จริงจากระบบทะเบียน
ให้เพิ่ม loader ที่เรียก .adapters.oreg_rmutt.parse_search_results()/parse_course_detail()
แทนรายการ mock ด้านล่าง โครงสร้างข้อมูลที่ endpoint คืนจะไม่เปลี่ยนไม่ว่าจะมาจากแหล่งไหน"""
from __future__ import annotations
from typing import Any

_MOCK_COURSES: list[dict[str, Any]] = [
    {
        "code": "CPE301",
        "name_th": "โครงสร้างข้อมูลและขั้นตอนวิธี",
        "name_en": "Data Structures and Algorithms",
        "credits": 3,
        "prerequisites": ["CPE201"]
    },
    {
        "code": "CPE302",
        "name_th": "ระบบฐานข้อมูล",
        "name_en": "Database Systems",
        "credits": 3,
        "prerequisites": []
    }
]

_MOCK_SECTIONS: dict[str, list[dict[str, Any]]] = {
    "CPE301": [
        {
            "section_id": "CPE301-01",
            "course_code": "CPE301",
            "course_name_th": "โครงสร้างข้อมูลและขั้นตอนวิธี",
            "teacher": "อ.สมชาย ใจดี",
            "credits": 3,
            "seats_available": 5,
            "seats_total": 40,
            "meetings": [{"day": "MON", "start": "09:00", "end": "11:50", "room": "ENG-301"}],
            "exam": None
        },
    ],
    "CPE302": [
        {
            "section_id": "CPE302-01",
            "course_code": "CPE302",
            "course_name_th": "ระบบฐานข้อมูล",
            "teacher": "อ.สมหญิง แสนดี",
            "credits": 3,
            "seats_available": 10,
            "seats_total": 30,
            "meetings": [{"day": "WED", "start": "13:00", "end": "15:50", "room": "ENG-302"}],
            "exam": None
        },
    ]
}

class CourseStore:
    def search_courses(self, q: str | None, term: str | None, day: str | None, teacher: str | None, cursor: str | None, limit: int):
        results = [
            c for c in _MOCK_COURSES
            if not q or q.lower() in c["name_th"].lower()
            or q.lower() in c["code"].lower()
            or q.lower() in c.get("name_en", "").lower()
        ]
        return results[:limit], None  # cursor pagination แบบง่าย ยังไม่ทำ next_cursor จริง

    def get_sections(self, code: str, term: str | None = None):
        return _MOCK_SECTIONS.get(code.upper(), [])

    def get_sections_by_ids(self, ids: list[str]):
        all_sections = [s for secs in _MOCK_SECTIONS.values() for s in secs]
        return [s for s in all_sections if s["section_id"] in ids]

course_store = CourseStore()
