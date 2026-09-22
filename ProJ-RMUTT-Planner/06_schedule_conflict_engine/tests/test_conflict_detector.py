"""Tests for Hard Conflicts (C1 - C6)"""
from src.core.conflict_detector import detect_conflicts
from src.models.schemas import (
    Exam,
    Meeting,
    SectionInput,
    StudentContextInput,
)


def test_c1_time_clash():
    sec1 = SectionInput(
        id="CPE101-01",
        course_code="CPE101",
        section="01",
        meetings=[Meeting(day=0, start_min=540, end_min=720)],  # จันทร์ 09:00-12:00
    )
    sec2 = SectionInput(
        id="CPE102-01",
        course_code="CPE102",
        section="01",
        meetings=[Meeting(day=0, start_min=660, end_min=840)],  # จันทร์ 11:00-14:00 (ชน 11:00-12:00)
    )

    conflicts = detect_conflicts([sec1, sec2])
    c1 = [c for c in conflicts if c.code == "C1"]
    assert len(c1) == 1
    assert c1[0].severity == "ERROR"
    assert "CPE101-01" in c1[0].subjects
    assert "CPE102-01" in c1[0].subjects


def test_c2_exam_clash():
    sec1 = SectionInput(
        id="CPE101-01",
        course_code="CPE101",
        section="01",
        meetings=[Meeting(day=0, start_min=540, end_min=660)],
        exams=[Exam(exam_type="final", exam_date="2026-10-15", start_min=540, end_min=720)],
    )
    sec2 = SectionInput(
        id="CPE102-01",
        course_code="CPE102",
        section="01",
        meetings=[Meeting(day=1, start_min=540, end_min=660)],  # เรียนคนละวัน
        exams=[Exam(exam_type="final", exam_date="2026-10-15", start_min=600, end_min=780)],  # สอบวันเดียวกันเวลาชนกัน
    )

    conflicts = detect_conflicts([sec1, sec2])
    c2 = [c for c in conflicts if c.code == "C2"]
    assert len(c2) == 1
    assert c2[0].message_key == "exam_clash"


def test_c3_prereq_fail():
    sec = SectionInput(
        id="CPE201-01",
        course_code="CPE201",
        section="01",
        prerequisites=["CPE101"],
        meetings=[Meeting(day=0, start_min=540, end_min=720)],
    )
    # นักศึกษายังไม่ผ่าน CPE101
    student = StudentContextInput(student_id="116610462000-0", passed_courses=["GEN101"])

    conflicts = detect_conflicts([sec], student=student)
    c3 = [c for c in conflicts if c.code == "C3"]
    assert len(c3) == 1
    assert c3[0].detail["missing_prereq"] == "CPE101"


def test_c4_credit_limit_exceeded():
    # สร้าง 8 วิชา วิชาละ 3 หน่วยกิต = 24 หน่วยกิต (เกินเพดาน 21)
    sections = [
        SectionInput(
            id=f"CPE10{i}-01",
            course_code=f"CPE10{i}",
            section="01",
            credits=3,
            meetings=[Meeting(day=i % 5, start_min=540 + (i * 30), end_min=600 + (i * 30))],
        )
        for i in range(8)
    ]
    conflicts = detect_conflicts(sections)
    c4 = [c for c in conflicts if c.code == "C4" and c.severity == "ERROR"]
    assert len(c4) == 1
    assert c4[0].detail["total_credits"] == 24


def test_c4_summer_credit_limit():
    # เทอม 3 (ฤดูร้อน) เพดาน 9 หน่วยกิต
    sections = [
        SectionInput(
            id=f"CPE10{i}-01",
            course_code=f"CPE10{i}",
            section="01",
            credits=4,
            meetings=[],
        )
        for i in range(3)  # 3 * 4 = 12 หน่วยกิต
    ]
    conflicts = detect_conflicts(sections, term="3/2569")
    c4 = [c for c in conflicts if c.code == "C4" and c.severity == "ERROR"]
    assert len(c4) == 1
    assert c4[0].detail["max_credits"] == 9


def test_c5_duplicate_sections():
    # ลง 2 section ในวิชาเดียวกัน
    sec1 = SectionInput(id="CPE101-01", course_code="CPE101", section="01", meetings=[])
    sec2 = SectionInput(id="CPE101-02", course_code="CPE101", section="02", meetings=[])

    conflicts = detect_conflicts([sec1, sec2])
    c5 = [c for c in conflicts if c.code == "C5"]
    assert len(c5) == 1
    assert c5[0].message_key == "duplicate_section"


def test_c6_seat_full():
    sec = SectionInput(
        id="CPE101-01",
        course_code="CPE101",
        section="01",
        seat_total=40,
        seat_taken=40,  # เต็ม
        meetings=[],
    )
    conflicts = detect_conflicts([sec])
    c6 = [c for c in conflicts if c.code == "C6"]
    assert len(c6) == 1
    assert c6[0].detail["seat_taken"] == 40
