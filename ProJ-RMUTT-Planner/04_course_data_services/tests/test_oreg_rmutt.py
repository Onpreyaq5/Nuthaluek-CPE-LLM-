"""ทดสอบ parser หน้าค้นหารายวิชา / รายละเอียดวิชา ของ oreg3.rmutt.ac.th
fixture สร้างจากภาพหน้าจอ — เมื่อได้ HTML จริงให้แทนที่ไฟล์ใน tests/fixtures/ แล้วปรับ expected"""
from datetime import date
from pathlib import Path

import pytest

from src.adapters.oreg_rmutt import parse_course_detail, parse_search_results
from src.adapters.thai_text import parse_credit, parse_day, parse_thai_date, parse_time_range

FIX = Path(__file__).parent / "fixtures"


# ---------- thai_text ----------
def test_parse_credit():
    c = parse_credit("3 (2-2-5)")
    assert (c.total, c.lecture, c.lab, c.self_study) == (3, 2, 2, 5)
    assert parse_credit("0 (0-0-0)").total == 0
    assert parse_credit("ไม่มี") is None


@pytest.mark.parametrize("txt,expected", [("จันทร์", 0), ("พฤหัสบดี", 3), ("เสาร์", 5), ("อาทิตย์", 6), ("x", None)])
def test_parse_day(txt, expected):
    assert parse_day(txt) == expected


def test_parse_time_range():
    assert parse_time_range("13:00-15:00") == (780, 900)
    assert parse_time_range("09:00 - 12:00") == (540, 720)


def test_parse_thai_date_be_to_ce():
    assert parse_thai_date("5 ก.ย. 2569") == date(2026, 9, 5)
    assert parse_thai_date("2 พ.ย. 2569") == date(2026, 11, 2)


# ---------- ค้นหารายวิชา ----------
def test_search_results_rows():
    rows = parse_search_results((FIX / "search_results_sample.html").read_bytes())
    assert len(rows) == 5
    r = rows[0]
    assert r.course_code == "04000201-62"
    assert r.curriculum_year == 62
    assert r.name_th == "ภาษาอังกฤษสำหรับงานวิศวกรรม"
    assert r.credit.text == "3 (2-2-5)"
    assert (r.section, r.seat_total, r.seat_taken, r.seat_left) == ("1", 36, 35, 1)
    assert r.status == "W"
    assert "เทียบโอน" in r.level
    assert r.term == "1/2569"


def test_search_results_full_section():
    rows = parse_search_results((FIX / "search_results_sample.html").read_bytes())
    full = [r for r in rows if r.seat_left == 0]
    assert [r.section for r in full] == ["5"]


# ---------- รายละเอียดวิชา ----------
@pytest.fixture(scope="module")
def detail():
    return parse_course_detail((FIX / "course_detail_sample.html").read_bytes())


def test_detail_header(detail):
    assert detail.course_code == "04000201-62"
    assert detail.name_en == "English for Engineering"
    assert detail.name_th == "ภาษาอังกฤษสำหรับงานวิศวกรรม"
    assert detail.credit.text == "3 (2-2-5)"
    assert detail.term == "1/2569"


def test_detail_sections_and_meetings(detail):
    secs = {s.section: s for s in detail.sections}
    assert set(secs) == {"02", "03", "05"}
    s2 = secs["02"]
    assert (s2.seat_total, s2.seat_taken, s2.seat_left) == (29, 26, 3)
    # 1 บรรยาย + 2 ปฏิบัติ วันเสาร์
    assert [(m.day, m.start_min, m.end_min, m.meeting_type) for m in s2.meetings] == [
        (5, 780, 900, "C"), (5, 900, 1020, "L"), (5, 1020, 1140, "L"),
    ]
    # sec 05 เรียนคนละวัน
    assert [(m.day_text, m.meeting_type) for m in secs["05"].meetings] == [("จันทร์", "C"), ("อังคาร", "L")]


def test_detail_teacher_exam_note(detail):
    s2 = next(s for s in detail.sections if s.section == "02")
    assert s2.teachers == ["ผู้ช่วยศาสตราจารย์ ดร.นรกมล วงษ์ศิลป์"]
    assert s2.midterm.exam_date == date(2026, 9, 5)
    assert (s2.midterm.start_min, s2.midterm.end_min) == (540, 720)
    assert s2.final.exam_date == date(2026, 11, 2)
    assert s2.note == "67146ETE1"
    assert "ชั้นปี 3" in s2.reserved_for


def test_detail_sections_share_exam_slot(detail):
    """กลุ่ม 02 กับ 03 สอบเวลาเดียวกัน → 06 ต้องใช้ข้อมูลนี้เช็ค EXAM_CLASH"""
    s2, s3 = (next(s for s in detail.sections if s.section == x) for x in ("02", "03"))
    assert s2.midterm.exam_date == s3.midterm.exam_date
    assert s2.midterm.start_min == s3.midterm.start_min
