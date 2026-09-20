"""Transcript Parser
- แปลงข้อมูลผลการเรียนจาก CSV, JSON หรือ Text
- จำแนกสถานะผ่าน / ไม่ผ่าน (F, W, U, ไม่สอบ → ต้องลงใหม่)
- คำนวณหน่วยกิตสะสมและ GPAX
"""
from __future__ import annotations

import csv
import io
import re
from dataclasses import asdict, dataclass
from typing import Any

from .normalizer import normalize_course_code

GRADE_POINTS: dict[str, float] = {
    "A": 4.0,
    "B+": 3.5,
    "B": 3.0,
    "C+": 2.5,
    "C": 2.0,
    "D+": 1.5,
    "D": 1.0,
    "F": 0.0,
}

GRADES_PASS = {"A", "B+", "B", "C+", "C", "D+", "D", "S", "ผ่าน", "P"}
GRADES_FAIL = {"F", "U", "W", "I", "ไม่ผ่าน", "ไม่ สอบ", "ไม่สอบ", "ขาดสอบ"}


@dataclass
class TranscriptRecord:
    course_code: str
    course_name: str = ""
    credits: int = 3
    grade: str = ""
    term: str = ""
    passed: bool = False
    grade_point: float | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class TranscriptSummary:
    records: list[TranscriptRecord]
    passed_courses: list[str]
    failed_courses: list[str]
    total_credits_attempted: int
    total_credits_passed: int
    gpax: float | None

    def to_dict(self) -> dict[str, Any]:
        return {
            "records": [r.to_dict() for r in self.records],
            "passed_courses": self.passed_courses,
            "failed_courses": self.failed_courses,
            "total_credits_attempted": self.total_credits_attempted,
            "total_credits_passed": self.total_credits_passed,
            "gpax": self.gpax,
        }


def _clean_grade(g: str) -> str:
    cleaned = g.strip().upper()
    if cleaned in ("ไม่ สอบ", "ไม่สอบ"):
        return "ไม่สอบ"
    return cleaned


def is_grade_passed(grade: str) -> bool:
    return _clean_grade(grade) in GRADES_PASS


def get_grade_point(grade: str) -> float | None:
    return GRADE_POINTS.get(_clean_grade(grade))


def build_transcript_summary(records: list[TranscriptRecord]) -> TranscriptSummary:
    """ประมวลผลรายการผลการเรียน: คำนวณวิชาที่ผ่าน, วิชาที่ค้าง (ได้ F/W แต่ยังไม่ผ่าน), หน่วยกิต และ GPAX"""
    passed_by_base: dict[str, bool] = {}
    last_grade_by_code: dict[str, str] = {}
    credits_by_code: dict[str, int] = {}

    total_attempted = 0
    total_passed = 0
    quality_points = 0.0
    graded_credits = 0

    for r in records:
        code = normalize_course_code(r.course_code)
        grade = _clean_grade(r.grade)
        r.course_code = code
        r.grade = grade
        r.passed = is_grade_passed(grade)
        r.grade_point = get_grade_point(grade)

        total_attempted += r.credits
        if r.passed:
            total_passed += r.credits
            passed_by_base[code] = True
        else:
            if code not in passed_by_base:
                passed_by_base[code] = False

        last_grade_by_code[code] = grade
        credits_by_code[code] = r.credits

        if r.grade_point is not None:
            quality_points += r.grade_point * r.credits
            graded_credits += r.credits

    passed_list = [code for code, passed in passed_by_base.items() if passed]
    failed_list = [code for code, passed in passed_by_base.items() if not passed]

    gpax = round(quality_points / graded_credits, 2) if graded_credits > 0 else None

    return TranscriptSummary(
        records=records,
        passed_courses=sorted(passed_list),
        failed_courses=sorted(failed_list),
        total_credits_attempted=total_attempted,
        total_credits_passed=total_passed,
        gpax=gpax,
    )


def parse_transcript_csv(csv_content: str) -> TranscriptSummary:
    """แปลงข้อมูลทรานสคริปต์จากรูปแบบ CSV
    รองรับ headers: course_code/รหัสวิชา, course_name/ชื่อวิชา, credits/หน่วยกิต, grade/เกรด, term/ภาคเรียน
    """
    records: list[TranscriptRecord] = []
    f = io.StringIO(csv_content.strip())
    reader = csv.reader(f)

    headers = None
    col_map = {
        "code": -1,
        "name": -1,
        "credits": -1,
        "grade": -1,
        "term": -1,
    }

    for row in reader:
        if not row or not any(row):
            continue
        if headers is None:
            # วิเคราะห์ header
            headers = [h.strip().lower() for h in row]
            for idx, h in enumerate(headers):
                if any(k in h for k in ("code", "รหัส", "course_id")):
                    col_map["code"] = idx
                elif any(k in h for k in ("name", "ชื่อวิชา", "รายวิชา", "title")):
                    col_map["name"] = idx
                elif any(k in h for k in ("credit", "หน่วยกิต", "cr")):
                    col_map["credits"] = idx
                elif any(k in h for k in ("grade", "เกรด", "ระดับคะแนน")):
                    col_map["grade"] = idx
                elif any(k in h for k in ("term", "ภาค", "ปี", "semester")):
                    col_map["term"] = idx

            # ถ้าไม่พบ header ที่ชัดเจน แต่เป็นข้อมูลเลย
            if col_map["code"] == -1:
                # ลองเดาตำแหน่ง: col 0 = code, col 1 = name/credits, etc.
                col_map["code"] = 0
                col_map["grade"] = 1 if len(row) > 1 else -1
            else:
                continue

        # อ่านข้อมูลแถว
        code_idx = col_map["code"]
        if code_idx >= len(row):
            continue
        code = row[code_idx].strip()
        if not code or code.lower() in ("course_code", "รหัสวิชา", "code"):
            continue

        name = row[col_map["name"]].strip() if col_map["name"] >= 0 and col_map["name"] < len(row) else ""
        
        cr_val = 3
        if col_map["credits"] >= 0 and col_map["credits"] < len(row):
            cr_str = row[col_map["credits"]].strip()
            digits = re.findall(r"\d+", cr_str)
            if digits:
                cr_val = int(digits[0])

        grade = row[col_map["grade"]].strip() if col_map["grade"] >= 0 and col_map["grade"] < len(row) else ""
        term = row[col_map["term"]].strip() if col_map["term"] >= 0 and col_map["term"] < len(row) else ""

        records.append(TranscriptRecord(
            course_code=code,
            course_name=name,
            credits=cr_val,
            grade=grade,
            term=term,
        ))

    return build_transcript_summary(records)


def parse_transcript_text(text: str) -> TranscriptSummary:
    """แปลงข้อมูลทรานสคริปต์จากข้อความธรรมดา เช่น:
    04000201-62 ฟิสิกส์ 1 3 B+ 1/2566
    04000202-62 เคมี 3 F 1/2566
    """
    records: list[TranscriptRecord] = []
    lines = text.strip().splitlines()
    # รูปแบบ: [รหัสวิชา] [ชื่อ (ถ้ามี)] [หน่วยกิต] [เกรด] [เทอม (ถ้ามี)]
    code_pattern = re.compile(r"([A-Za-z0-9]+(?:-[0-9]+)?)")
    grade_pattern = re.compile(r"\b(A|B\+|B|C\+|C|D\+|D|F|W|U|S|P|I|ผ่าน|ไม่ผ่าน|ไม่สอบ|ขาดสอบ)\b", re.IGNORECASE)

    for line in lines:
        line = line.strip()
        if not line:
            continue
        c_match = code_pattern.search(line)
        g_match = grade_pattern.search(line)
        if c_match and g_match:
            code = c_match.group(1)
            grade = g_match.group(1)

            # หาหน่วยกิต
            cr_val = 3
            # หาตัวเลขเดี่ยวๆ ที่ไม่ใช่รหัสวิชาและไม่ใช่เกรด
            tokens = line.split()
            for t in tokens:
                if t.isdigit() and 1 <= int(t) <= 12 and t != code:
                    cr_val = int(t)
                    break

            records.append(TranscriptRecord(
                course_code=code,
                credits=cr_val,
                grade=grade,
            ))

    return build_transcript_summary(records)
