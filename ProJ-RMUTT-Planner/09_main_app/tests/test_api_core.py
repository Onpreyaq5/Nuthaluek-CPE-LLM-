"""เทสแกนกลางของ 09 — กันไม่ให้บั๊กที่เคยเจอกลับมาอีก

รันจาก 09_main_app:  pytest -q
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

BASE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BASE / "api"))

from _core.conflicts import DEFAULT_MAX_CREDITS, detect_conflicts   # noqa: E402
from _core.planner import _clamp_credits, exams_clash, generate_plan  # noqa: E402
from _core.store import available_terms, load_timetable, resolve_sections, safe_term  # noqa: E402

TERM = "1/2569"


@pytest.fixture(scope="module")
def sections() -> list[dict]:
    return load_timetable(TERM)["sections"]


# ── ความปลอดภัยของชื่อไฟล์ ────────────────────────────────────────
@pytest.mark.parametrize("evil", [
    "..\\..\\..\\secret",
    "../../../etc/passwd",
    "1/2569/../../x",
    "1_2569",
    "",
    "9/9999",
])
def test_term_ที่ไม่ถูกต้องต้องถูกปฏิเสธ(evil: str) -> None:
    """term มาจากผู้ใช้ตรง ๆ ถ้าหลุดไปประกอบชื่อไฟล์ได้จะอ่านไฟล์นอกโฟลเดอร์ data ได้"""
    with pytest.raises(FileNotFoundError):
        safe_term(evil)


def test_term_ที่มีอยู่จริงต้องผ่าน() -> None:
    for term in available_terms():
        assert safe_term(term) == term


def test_ข้อความ_error_ต้องไม่หลุด_path_ในเครื่อง() -> None:
    with pytest.raises(FileNotFoundError) as exc:
        load_timetable("../../etc/passwd")
    assert "data" not in str(exc.value).lower()


# ── เพดานหน่วยกิต ────────────────────────────────────────────────
@pytest.mark.parametrize("raw,expected", [
    (99, 21),       # เกินเพดาน -> ตัดลงมาที่เพดาน
    (-5, 1),        # ติดลบ -> ขั้นต่ำของช่วง
    ("มาก", 21),    # แปลงไม่ได้ -> ค่าตั้งต้น
    (None, 21),
    (15, 15),       # ค่าที่สมเหตุสมผลต้องได้ตามที่ขอ
])
def test_clamp_credits(raw, expected) -> None:
    assert _clamp_credits(raw, 21, 1, 21) == expected


def test_ตั้ง_max_credits_เกินระเบียบต้องไม่ทะลุเพดาน(sections: list[dict]) -> None:
    """ค่าจากผู้ใช้เชื่อไม่ได้ — ถ้าไม่บังคับกรอบ ระบบจะจัดแผนที่ลงทะเบียนจริงไม่ได้ให้"""
    result = generate_plan(sections, term=TERM, student_year=2,
                           preferences={"max_credits": 99})
    assert result["summary"]["total_credits"] <= DEFAULT_MAX_CREDITS


def test_preferences_ผิดชนิดต้องไม่ทำให้พังทั้งแผน(sections: list[dict]) -> None:
    result = generate_plan(sections, term=TERM, student_year=2,
                           preferences={"max_credits": "มาก", "free_days": "จันทร์"})
    assert result["summary"]["total_credits"] > 0


# ── ตรรกะตารางชน ─────────────────────────────────────────────────
def test_เวลาสอบชนกันต้องตรวจเจอ() -> None:
    a = {"exams": [{"exam_type": "midterm", "exam_date": "2026-08-10",
                    "start_min": 540, "end_min": 660}]}
    b = {"exams": [{"exam_type": "midterm", "exam_date": "2026-08-10",
                    "start_min": 600, "end_min": 720}]}
    c = {"exams": [{"exam_type": "final", "exam_date": "2026-08-10",
                    "start_min": 600, "end_min": 720}]}
    assert exams_clash(a, b) is True
    assert exams_clash(a, c) is False          # คนละประเภทการสอบ ไม่นับว่าชน


def test_แผนที่ระบบจัดให้ต้องไม่มี_error(sections: list[dict]) -> None:
    for year in (1, 2, 3, 4):
        result = generate_plan(sections, term=TERM, student_year=year)
        errors = [c["code"] for c in result["conflicts"]]
        assert errors == [], f"ปี {year} ยังมีปัญหา {errors}"


def test_เลือกวิชาที่เวลาชนกันต้องขึ้น_C1(sections: list[dict]) -> None:
    """หาคู่ที่เวลาทับกันจริงจากข้อมูล แล้วยืนยันว่าเครื่องตรวจจับได้"""
    def overlaps(x: dict, y: dict) -> bool:
        for m1 in x["meetings"]:
            for m2 in y["meetings"]:
                if m1["day"] == m2["day"] and m1["start_min"] < m2["end_min"] \
                        and m2["start_min"] < m1["end_min"]:
                    return True
        return False

    pair = next(
        ((x, y) for i, x in enumerate(sections) for y in sections[i + 1:]
         if x["course_code"] != y["course_code"] and overlaps(x, y)),
        None,
    )
    assert pair is not None, "ข้อมูลทดสอบควรมีคู่ที่เวลาชนกันอย่างน้อยหนึ่งคู่"
    result = detect_conflicts(list(pair), term=TERM, all_sections=sections)
    assert "C1" in [c["code"] for c in result["conflicts"]]


def test_หมู่เรียนที่ไม่มีอยู่ต้องรายงานกลับ_ไม่ใช่เงียบ(sections: list[dict]) -> None:
    found, missing = resolve_sections(["ไม่มีจริง-99"], TERM)
    assert found == []
    assert missing == ["ไม่มีจริง-99"]
