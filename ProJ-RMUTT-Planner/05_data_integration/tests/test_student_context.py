"""Unit tests for Student Context Engine & Transcript Parser"""
from pathlib import Path

import pytest
from src.graduate_check import parse_graduate_check
from src.prereq_graph import PrerequisiteDAG
from src.student_context import (
    StudentPreferences,
    StudentProfile,
    build_student_context_from_audit,
    build_student_context_from_transcript,
)
from src.transcript_parser import (
    parse_transcript_csv,
    parse_transcript_text,
)

FIX = Path(__file__).parent / "fixtures"


def test_transcript_parser_csv():
    csv_data = """course_code,course_name,credits,grade,term
04000201-62,ฟิสิกส์ 1,3,B+,1/2566
04000202-62,เคมีสำหรับวิศวกร,3,F,1/2566
04000203-62,แคลคูลัส 1,3,C,1/2566
04000204-62,แคลคูลัส 2,3,W,2/2566
04000202-62,เคมีสำหรับวิศวกร,3,C+,2/2566
"""
    summary = parse_transcript_csv(csv_data)
    assert summary.total_credits_attempted == 15
    # 04000202 เคย F แต่ลงใหม่ได้ C+ -> ผ่าน
    assert "04000202-62" in summary.passed_courses
    # 04000204 ได้ W ยังไม่ได้ลงใหม่ -> อยู่ใน failed_courses (ต้องลงใหม่)
    assert "04000204-62" in summary.failed_courses
    assert summary.gpax is not None
    assert summary.gpax >= 2.0


def test_transcript_parser_text():
    text_data = """
    04000201-62 3 A 1/2566
    04000202-62 3 F 1/2566
    04000203-62 3 B 1/2566
    """
    summary = parse_transcript_text(text_data)
    assert "04000201-62" in summary.passed_courses
    assert "04000202-62" in summary.failed_courses
    assert summary.total_credits_passed == 6


def test_build_student_context_from_audit():
    audit_file = FIX / "graduate_check_sample.html"
    if not audit_file.exists():
        pytest.skip("Fixture not found")

    audit = parse_graduate_check(audit_file.read_bytes())
    dag = PrerequisiteDAG()
    dag.add_prerequisite("04000204-63", "04000203-63")

    prefs = StudentPreferences(no_early_class=True, free_days=[4], max_credits=18)
    ctx = build_student_context_from_audit(audit, preferences=prefs, prereq_dag=dag)

    d = ctx.to_dict()
    assert d["student_id"] == "116610462000-0"
    assert d["id_hash"] == "116610462000-0"
    assert d["program_name"] == "วิศวกรรมคอมพิวเตอร์"
    assert d["entry_year"] == 2566
    assert d["student_year"] == d["year_level"]
    assert d["credits_earned"] == 20
    assert d["credits_remaining"] == 123
    assert d["completed_course_codes"] == d["passed_courses"]
    assert d["academic_summary"]["total_credits_earned"] == 20
    assert d["academic_summary"]["min_total_credits"] == 143
    assert d["academic_summary"]["remaining_total_credits"] == 123
    assert d["preferences"]["no_early_class"] is True
    assert d["preferences"]["free_days"] == ["FRI"]
    assert len(d["category_progress"]) > 0
