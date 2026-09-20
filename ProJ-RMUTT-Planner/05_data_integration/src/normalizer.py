"""Course & Credit Normalizer + Search Index (RapidFuzz)
- ทำความสะอาดรหัสวิชา (uppercase, ตัดช่องว่าง)
- แยกรายละเอียดหน่วยกิต '3(2-2-5)' → credits=3, lecture=2, lab=2, self=5
- Search Index ด้วย RapidFuzz ค้นหาชื่อวิชาไทย/อังกฤษแม้พิมพ์ผิด
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

try:
    from rapidfuzz import fuzz, process
    HAS_RAPIDFUZZ = True
except ImportError:
    HAS_RAPIDFUZZ = False


_CREDIT_PATTERN = re.compile(
    r"^(\d+)(?:\s*\(\s*(\d+)\s*[-–]\s*(\d+)\s*[-–]\s*(\d+)\s*\))?$"
)


@dataclass
class CreditDetail:
    credits: int
    lecture: int = 0
    lab: int = 0
    self_study: int = 0
    raw: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "credits": self.credits,
            "lecture": self.lecture,
            "lab": self.lab,
            "self_study": self.self_study,
            "raw": self.raw or f"{self.credits}({self.lecture}-{self.lab}-{self.self_study})",
        }


def normalize_course_code(code: str) -> str:
    """ทำความสะอาดรหัสวิชา: ตัดช่องว่าง, แปลงเป็นตัวพิมพ์ใหญ่, แปลงขีดแดชมาตรฐาน
    เช่น ' 04000201 - 62 ' -> '04000201-62'
    """
    if not code:
        return ""
    c = code.strip().upper()
    # แปลง en-dash, em-dash เป็น hyphen
    c = c.replace("–", "-").replace("—", "-")
    # ตัดช่องว่างรอบเครื่องหมายขีด
    c = re.sub(r"\s*-\s*", "-", c)
    # ตัดช่องว่างระหว่างตัวอักษรและตัวเลขถ้ามี
    c = re.sub(r"\s+", "", c)
    return c


def extract_base_code(code: str) -> str:
    """ดึงรหัสวิชาพื้นฐานโดยตัดรหัสปีหลักสูตรท้ายสุดออก
    เช่น '04000201-62' -> '04000201'
    """
    norm = normalize_course_code(code)
    return norm.split("-")[0] if "-" in norm else norm


def parse_credit_detail(text: str) -> CreditDetail:
    """แปลงข้อความหน่วยกิต เช่น '3(2-2-5)' หรือ '3'
    -> CreditDetail(credits=3, lecture=2, lab=2, self_study=5)
    """
    if not text:
        return CreditDetail(credits=0, raw="")

    clean_text = text.strip().replace("–", "-")
    m = _CREDIT_PATTERN.match(clean_text)
    if m:
        total = int(m.group(1))
        lec = int(m.group(2)) if m.group(2) is not None else total
        lab = int(m.group(3)) if m.group(3) is not None else 0
        self_s = int(m.group(4)) if m.group(4) is not None else 0
        return CreditDetail(
            credits=total,
            lecture=lec,
            lab=lab,
            self_study=self_s,
            raw=clean_text,
        )

    # กรณีมีตัวเลขเดียว เช่น "3"
    digits = re.findall(r"\d+", clean_text)
    if digits:
        total = int(digits[0])
        return CreditDetail(credits=total, lecture=total, lab=0, self_study=0, raw=clean_text)

    return CreditDetail(credits=0, raw=clean_text)


@dataclass
class CourseItem:
    code: str
    name_th: str
    name_en: str = ""
    credits: int = 3
    credit_detail: str = ""
    category: str = ""
    description: str = ""

    def search_strings(self) -> list[str]:
        strs = [self.code, extract_base_code(self.code), self.name_th]
        if self.name_en:
            strs.append(self.name_en)
        return [s for s in strs if s]


class CourseSearchIndex:
    """ดัชนีสำหรับค้นหารายวิชาด้วย RapidFuzz
    รองรับการค้นหาด้วยรหัสวิชา ชื่อภาษาไทย หรือชื่อภาษาอังกฤษ (ทนต่อการพิมพ์ผิด)
    """

    def __init__(self, courses: list[CourseItem] | None = None):
        self.courses_by_code: dict[str, CourseItem] = {}
        self.search_entries: list[tuple[str, str]] = []  # (search_text, course_code)
        if courses:
            for c in courses:
                self.add_course(c)

    def add_course(self, course: CourseItem) -> None:
        norm_code = normalize_course_code(course.code)
        course.code = norm_code
        self.courses_by_code[norm_code] = course
        # เพิ่ม search strings
        for s in course.search_strings():
            self.search_entries.append((s.lower(), norm_code))

    def search(self, query: str, limit: int = 5, score_cutoff: float = 50.0) -> list[dict[str, Any]]:
        """ค้นหารายวิชาโดยคืนค่ารายการที่มีคะแนนความคล้ายคลึงสูงสุด"""
        q = query.strip().lower()
        if not q:
            return []

        # ถ้าค้นหาตรงกับรหัสวิชาหรือ base code พอดี
        norm_q = normalize_course_code(query)
        base_q = extract_base_code(query)
        exact_matches = []
        for code, c in self.courses_by_code.items():
            if code == norm_q or extract_base_code(code) == base_q:
                exact_matches.append({
                    "course": c,
                    "score": 100.0,
                    "match_type": "exact_code",
                })

        if exact_matches:
            return [
                {
                    "code": m["course"].code,
                    "name_th": m["course"].name_th,
                    "name_en": m["course"].name_en,
                    "credits": m["course"].credits,
                    "credit_detail": m["course"].credit_detail,
                    "category": m["course"].category,
                    "score": m["score"],
                }
                for m in exact_matches[:limit]
            ]

        results = []
        if HAS_RAPIDFUZZ and self.search_entries:
            # ค้นหาด้วย rapidfuzz extract
            choices = [entry[0] for entry in self.search_entries]
            matches = process.extract(
                q,
                choices,
                scorer=fuzz.WRatio,
                limit=limit * 3,
                score_cutoff=score_cutoff,
            )

            seen_codes = set()
            for match_str, score, idx in matches:
                code = self.search_entries[idx][1]
                if code in seen_codes:
                    continue
                seen_codes.add(code)
                c = self.courses_by_code[code]
                results.append({
                    "code": c.code,
                    "name_th": c.name_th,
                    "name_en": c.name_en,
                    "credits": c.credits,
                    "credit_detail": c.credit_detail,
                    "category": c.category,
                    "score": round(score, 1),
                })
                if len(results) >= limit:
                    break
        else:
            # Fallback หากไม่มี rapidfuzz: ทำ substring match
            seen_codes = set()
            for text, code in self.search_entries:
                if q in text and code not in seen_codes:
                    seen_codes.add(code)
                    c = self.courses_by_code[code]
                    results.append({
                        "code": c.code,
                        "name_th": c.name_th,
                        "name_en": c.name_en,
                        "credits": c.credits,
                        "credit_detail": c.credit_detail,
                        "category": c.category,
                        "score": 80.0,
                    })
                    if len(results) >= limit:
                        break

        return results
