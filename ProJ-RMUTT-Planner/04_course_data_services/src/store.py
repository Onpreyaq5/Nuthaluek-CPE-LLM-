"""ข้อมูลรายวิชาและกลุ่มเรียน — แหล่งเดียวที่ 02, 03 และ 06 ใช้ร่วมกัน

โหลดตารางสอนจาก SEED_DIR (ไฟล์ cpe_timetable_<ภาค>_<ปี>.json) ซึ่งเป็นชุดเดียวกับที่ 07 และ 09 ใช้
ทุกโมดูลจึงเห็นกลุ่มเรียนชุดเดียวกัน ก่อนหน้านี้ 04 มีข้อมูลปลอมแค่ 2 วิชาเขียนในโค้ด
ผลคือ 02 เลือกกลุ่มเรียนจาก 04 แล้วส่งให้ 06 ตรวจชน แต่ 06 หาไม่เจอ ตรวจตารางชนพังทุกครั้ง

เก็บข้อมูลภายในเป็นรูปแบบ SectionInput ของ 06 (วันเป็นเลข 0-6 เวลาเป็นนาที)
แล้วแปลงเป็นรูปแบบของ 02 (วัน "MON" เวลา "09:00") ตอนตอบ 02

ไม่มีไฟล์ใน SEED_DIR (เช่นตอนรันเทสของโมดูลนี้เอง) = ใช้ข้อมูลตัวอย่าง 2 วิชาเดิม
"""
from __future__ import annotations

import json
import logging
import os
from datetime import date
from pathlib import Path
from typing import Any

log = logging.getLogger(__name__)

DAYS = ["MON", "TUE", "WED", "THU", "FRI", "SAT", "SUN"]
DEFAULT_TERM = "1/2569"

# ── ข้อมูลตัวอย่าง ใช้เมื่อไม่มีไฟล์ตารางสอนจริง ─────────────────────
_MOCK_SECTIONS: list[dict[str, Any]] = [
    {
        "id": "CPE301-01", "course_code": "CPE301", "section": "01",
        "course_name": "โครงสร้างข้อมูลและขั้นตอนวิธี", "course_name_en": "Data Structures and Algorithms",
        "credits": 3, "seat_total": 40, "seat_taken": 35, "prerequisites": ["CPE201"],
        "teachers": ["อ.สมชาย ใจดี"],
        "meetings": [{"day": 0, "start_min": 540, "end_min": 710, "room": "ENG-301"}], "exams": [],
    },
    {
        "id": "CPE302-01", "course_code": "CPE302", "section": "01",
        "course_name": "ระบบฐานข้อมูล", "course_name_en": "Database Systems",
        "credits": 3, "seat_total": 30, "seat_taken": 20, "prerequisites": [],
        "teachers": ["อ.สมหญิง แสนดี"],
        "meetings": [{"day": 2, "start_min": 780, "end_min": 950, "room": "ENG-302"}], "exams": [],
    },
]


def _hhmm(minutes: int) -> str:
    h, m = divmod(int(minutes), 60)
    return f"{h:02d}:{m:02d}"


def _weekday_of_be_date(value: str) -> str | None:
    """"2569-09-03" (พ.ศ.) -> "THU" """
    try:
        y, mth, d = (int(x) for x in value.split("-"))
        if y > 2400:
            y -= 543
        return DAYS[date(y, mth, d).weekday()]
    except (ValueError, TypeError):
        return None


def to_backend_section(s: dict[str, Any]) -> dict[str, Any]:
    """รูปแบบ Section ของ 02 (schemas/courses.py)"""
    total = int(s.get("seat_total") or 0)
    taken = int(s.get("seat_taken") or 0)
    exam = None
    finals = [e for e in s.get("exams") or [] if e.get("exam_type") == "final"] or (s.get("exams") or [])
    if finals:
        e = finals[0]
        day = _weekday_of_be_date(str(e.get("exam_date", "")))
        if day:
            room = e.get("room")
            exam = {"day": day, "start": _hhmm(e["start_min"]), "end": _hhmm(e["end_min"]),
                    "room": None if room in (None, "", "N/A") else room}
    return {
        "section_id": s["id"],
        "course_code": s["course_code"],
        "course_name_th": s.get("course_name") or s["course_code"],
        "teacher": ", ".join(s.get("teachers") or []) or "-",
        "credits": int(s.get("credits") or 0),
        "seats_available": max(total - taken, 0),
        "seats_total": total,
        "meetings": [
            {"day": DAYS[m["day"]], "start": _hhmm(m["start_min"]), "end": _hhmm(m["end_min"]),
             "room": m.get("room")}
            for m in s.get("meetings") or []
        ],
        "exam": exam,
    }


def to_engine_section(s: dict[str, Any]) -> dict[str, Any]:
    """รูปแบบ SectionInput ของ 06 — ตัด field ที่ 06 ไม่รู้จักออก"""
    keep = ("id", "course_code", "section", "course_name", "credits", "slots_mask", "meetings",
            "exams", "seat_total", "seat_taken", "prerequisites", "campus", "teachers")
    return {k: s[k] for k in keep if k in s}


class CourseStore:
    def __init__(self, seed_dir: str | os.PathLike | None = None) -> None:
        self.by_term: dict[str, list[dict[str, Any]]] = {}
        self.source = "mock"
        self.load(seed_dir if seed_dir is not None else os.getenv("SEED_DIR", ""))

    # ── โหลด ──────────────────────────────────────────────────
    def load(self, seed_dir: str | os.PathLike) -> None:
        self.by_term = {}
        files = sorted(Path(seed_dir).glob("cpe_timetable_*.json")) if seed_dir else []
        for f in files:
            data = json.loads(f.read_text(encoding="utf-8"))
            self.by_term[data.get("term") or DEFAULT_TERM] = list(data.get("sections") or [])
        if self.by_term:
            self.source = str(seed_dir)
            log.info("โหลดตารางสอน %s ภาค: %s", len(self.by_term),
                     {t: len(s) for t, s in self.by_term.items()})
        else:
            self.source = "mock"
            self.by_term = {DEFAULT_TERM: list(_MOCK_SECTIONS)}
            log.warning("ไม่พบตารางสอนใน SEED_DIR=%r ใช้ข้อมูลตัวอย่าง", seed_dir)

    @property
    def terms(self) -> list[str]:
        return sorted(self.by_term)

    def sections(self, term: str | None) -> list[dict[str, Any]]:
        if term and term in self.by_term:
            return self.by_term[term]
        if term:
            return []
        return self.by_term.get(DEFAULT_TERM) or next(iter(self.by_term.values()), [])

    # ── รายวิชา ───────────────────────────────────────────────
    def _courses(self, sections: list[dict[str, Any]]) -> list[dict[str, Any]]:
        seen: dict[str, dict[str, Any]] = {}
        for s in sections:
            code = s["course_code"]
            if code in seen:
                continue
            seen[code] = {
                "code": code,
                "name_th": s.get("course_name") or code,
                "name_en": s.get("course_name_en") or "",
                "credits": int(s.get("credits") or 0),
                "prerequisites": list(s.get("prerequisites") or []),
                "category": s.get("category"),
                "suggested_year": s.get("suggested_year"),
            }
        return sorted(seen.values(), key=lambda c: (c.get("suggested_year") or 9, c["code"]))

    def search_courses(self, q: str | None, term: str | None, day: str | None,
                       teacher: str | None, cursor: str | None, limit: int):
        secs = self.sections(term)
        if day:
            d = DAYS.index(day.upper()) if day.upper() in DAYS else -1
            secs = [s for s in secs if any(m["day"] == d for m in s.get("meetings") or [])]
        if teacher:
            t = teacher.strip().lower()
            secs = [s for s in secs if any(t in x.lower() for x in s.get("teachers") or [])]
        courses = self._courses(secs)
        if q:
            ql = q.strip().lower()
            courses = [c for c in courses
                       if ql in c["code"].lower() or ql in c["name_th"].lower() or ql in c["name_en"].lower()]
        start = int(cursor) if cursor and cursor.isdigit() else 0
        page = courses[start:start + limit]
        nxt = str(start + limit) if start + limit < len(courses) else None
        return page, nxt

    # ── กลุ่มเรียน ────────────────────────────────────────────
    def get_sections(self, code: str, term: str | None = None) -> list[dict[str, Any]]:
        code = code.strip()
        return [to_backend_section(s) for s in self.sections(term)
                if s["course_code"].upper() == code.upper()]

    def get_sections_by_ids(self, ids: list[str], term: str | None = None) -> list[dict[str, Any]]:
        return [to_backend_section(s) for s in self._raw_by_ids(ids, term)]

    def get_engine_sections_by_ids(self, ids: list[str], term: str | None = None) -> list[dict[str, Any]]:
        return [to_engine_section(s) for s in self._raw_by_ids(ids, term)]

    def _raw_by_ids(self, ids: list[str], term: str | None) -> list[dict[str, Any]]:
        wanted = set(ids)
        # term ไม่ระบุ = ค้นทุกภาค (02 ส่งแค่ ids มาใน /sections/bulk)
        pools = [self.sections(term)] if term else list(self.by_term.values())
        found: dict[str, dict[str, Any]] = {}
        for pool in pools:
            for s in pool:
                if s["id"] in wanted and s["id"] not in found:
                    found[s["id"]] = s
        return [found[i] for i in ids if i in found]

    def open_engine_sections(self, term: str | None, course_codes: list[str] | None,
                             q: str | None = None) -> list[dict[str, Any]]:
        secs = self.sections(term)
        if course_codes:
            codes = set(course_codes)
            secs = [s for s in secs if s["course_code"] in codes]
        elif q:
            ql = q.strip().lower()
            secs = [s for s in secs
                    if ql in s["course_code"].lower() or ql in (s.get("course_name") or "").lower()]
        return [to_engine_section(s) for s in secs]


course_store = CourseStore()
