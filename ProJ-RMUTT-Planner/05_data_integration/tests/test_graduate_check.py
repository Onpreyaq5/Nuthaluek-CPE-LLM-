"""ทดสอบ parser หน้าตรวจสอบจบ + ตัวสร้างรายการวิชาที่ควรลง (degree_plan)"""
from pathlib import Path

import pytest

from src.degree_plan import P0_RETAKE, P1_REQUIRED, P3_OTHER, build_candidates, build_plan_input
from src.graduate_check import decode_html, parse_graduate_check

FIX = Path(__file__).parent / "fixtures"


@pytest.fixture(scope="module")
def audit():
    return parse_graduate_check((FIX / "graduate_check_sample.html").read_bytes())


def test_decode_prefers_meta_charset():
    assert decode_html(b'<meta charset="utf-8">\xe0\xb8\x81') == '<meta charset="utf-8">ก'
    assert decode_html(b'<meta charset="windows-874">\xa1') == '<meta charset="windows-874">ก'


def test_header(audit):
    assert audit.student_id == "116610462000-0"
    assert audit.student_name == "นายทดสอบ ระบบ"
    assert audit.min_total_credits == 143
    assert audit.max_years == 8
    assert audit.min_gpax == 2.0


def test_categories_hierarchy(audit):
    nums = [c.number for c in audit.categories]
    assert nums == ["0", "1", "1.1", "1.1.1", "2.1"]
    depth = {c.number: c.depth for c in audit.categories}
    assert depth["1"] == 1 and depth["1.1"] == 2 and depth["1.1.1"] == 3


def test_category_totals_and_status(audit):
    cat = {c.number: c for c in audit.categories}
    assert (cat["1"].min_credits, cat["1"].passed_credits, cat["1"].gpa) == (30, 20, 2.55)
    assert cat["1"].is_passed is False and cat["1"].below_min is True
    assert cat["1"].remaining_credits == 10
    assert cat["1.1"].is_passed is True and cat["1.1"].remaining_credits == 0
    assert cat["2.1"].remaining_credits == 23


def test_course_attempts_and_pass_logic(audit):
    courses = {c.code: c for c in audit.all_courses()}
    # เคยได้ F แล้วลงใหม่ได้ C → ถือว่าผ่าน
    calc = courses["04000202-63"]
    assert [(a.term, a.grade) for a in calc.attempts] == [("1/2566", "F"), ("2/2566", "C")]
    assert calc.passed is True and calc.last_grade == "C"
    # W = ยังไม่ผ่าน ต้องลงใหม่
    assert courses["04000203-63"].passed is False and courses["04000203-63"].taken is True
    # ยังไม่เคยลง
    assert courses["04000204-63"].taken is False
    # กลุ่มสมรรถนะ: "ไม่ สอบ" = ไม่ผ่าน
    assert courses["C0407131"].passed is False
    assert courses["C0400011"].passed is True


def test_summary_lists(audit):
    d = audit.to_dict()["summary"]
    assert d["failed_courses"] == ["C0407131", "04000203-63"]
    assert set(d["not_taken_courses"]) == {"C0407141", "C5100001", "04000204-63"}


# ---------- degree_plan ----------
def test_candidates_priority_order(audit):
    cands = build_candidates(audit)
    codes_by_pr = {}
    for c in cands:
        codes_by_pr.setdefault(c.priority, []).append(c.code)
    assert set(codes_by_pr[P0_RETAKE]) == {"C0407131", "04000203-63"}
    assert codes_by_pr[P1_REQUIRED] == ["04000204-63"]        # หมวด 2.1 ยังไม่ผ่าน
    assert set(codes_by_pr[P3_OTHER]) == {"C0407141", "C5100001"}  # หมวด 0 ผ่านแล้ว
    # เรียงจาก P0 ก่อนเสมอ
    assert [c.priority for c in cands] == sorted(c.priority for c in cands)


def test_plan_input_without_search_rows(audit):
    plan = build_plan_input(audit)
    assert plan.min_total_credits == 143
    assert plan.to_dict()["stats"]["must_retake"] == 2
    assert all(not c.is_open_this_term for c in plan.candidates)


def test_plan_input_attaches_open_sections(audit):
    class Row:  # ย่อส่วนของ SearchRow จาก 04
        def __init__(self, code, sec, left):
            self.course_code, self.section, self.seat_left, self.level, self.term = code, sec, left, "ปกติ", "1/2569"

    # รหัสเดียวกันต่างปีหลักสูตร (-63 vs -68) ให้จับคู่ได้
    rows = [Row("04000203-68", "1", 5), Row("04000203-68", "2", 0), Row("99999999-68", "1", 9)]
    plan = build_plan_input(audit, rows)
    phys = next(c for c in plan.candidates if c.code == "04000203-63")
    assert phys.is_open_this_term and len(phys.open_sections) == 2
    assert plan.term == "1/2569"
    assert plan.to_dict()["stats"]["open_this_term"] == 1
