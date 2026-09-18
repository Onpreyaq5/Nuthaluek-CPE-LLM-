"""ตัวช่วยแปลงข้อความไทยจากระบบทะเบียน (Vision Net) ให้เป็นค่าที่โปรแกรมใช้ได้

ใช้ร่วมกันทั้ง 04 (ดึงข้อมูล) และ 05 (normalize)
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date

# วันในสัปดาห์ → 0=จันทร์ ... 6=อาทิตย์ (ตรงกับ 05_data_integration)
THAI_DAYS: dict[str, int] = {
    "จันทร์": 0, "จ.": 0,
    "อังคาร": 1, "อ.": 1,
    "พุธ": 2, "พ.": 2,
    "พฤหัสบดี": 3, "พฤหัส": 3, "พฤ.": 3,
    "ศุกร์": 4, "ศ.": 4,
    "เสาร์": 5, "ส.": 5,
    "อาทิตย์": 6, "อา.": 6,
}

THAI_MONTHS: dict[str, int] = {
    "ม.ค.": 1, "ก.พ.": 2, "มี.ค.": 3, "เม.ย.": 4, "พ.ค.": 5, "มิ.ย.": 6,
    "ก.ค.": 7, "ส.ค.": 8, "ก.ย.": 9, "ต.ค.": 10, "พ.ย.": 11, "ธ.ค.": 12,
    "มกราคม": 1, "กุมภาพันธ์": 2, "มีนาคม": 3, "เมษายน": 4, "พฤษภาคม": 5,
    "มิถุนายน": 6, "กรกฎาคม": 7, "สิงหาคม": 8, "กันยายน": 9, "ตุลาคม": 10,
    "พฤศจิกายน": 11, "ธันวาคม": 12,
}

# "3 (2-2-5)"  หรือ "3(2-2-5)"  หรือ "0 (0-0-0)"
_CREDIT_RE = re.compile(r"(\d+)\s*\(\s*(\d+)\s*-\s*(\d+)\s*-\s*(\d+)\s*\)")
# "13:00-15:00" / "13:00 - 15:00"
_TIME_RANGE_RE = re.compile(r"(\d{1,2}):(\d{2})\s*-\s*(\d{1,2}):(\d{2})")
# "5 ก.ย. 2569 เวลา 09:00 - 12:00 อาคาร N/A ห้อง N-A"
_THAI_DATE_RE = re.compile(r"(\d{1,2})\s+(\S+?\.?)\s+(\d{4})")
# รหัสวิชา มทร.ธัญบุรี เช่น 04000201-62  (8 หลัก - ปีหลักสูตร 2 หลัก)
COURSE_CODE_RE = re.compile(r"\b(\d{8})-(\d{2})\b")
# รหัสกลุ่มสมรรถนะในหน้าตรวจสอบจบ เช่น C0400011
COMPETENCY_CODE_RE = re.compile(r"\b(C\d{7})\b")


@dataclass(frozen=True)
class Credit:
    total: int
    lecture: int
    lab: int
    self_study: int

    @property
    def text(self) -> str:
        return f"{self.total} ({self.lecture}-{self.lab}-{self.self_study})"


def parse_credit(text: str) -> Credit | None:
    """'3 (2-2-5)' → Credit(3,2,2,5)"""
    m = _CREDIT_RE.search(text or "")
    if not m:
        return None
    return Credit(*(int(g) for g in m.groups()))


def parse_day(text: str) -> int | None:
    t = (text or "").strip()
    for name, idx in THAI_DAYS.items():
        if t.startswith(name):
            return idx
    return None


def parse_time_range(text: str) -> tuple[int, int] | None:
    """'13:00-15:00' → (780, 900) นาทีจากเที่ยงคืน"""
    m = _TIME_RANGE_RE.search(text or "")
    if not m:
        return None
    h1, m1, h2, m2 = (int(g) for g in m.groups())
    return h1 * 60 + m1, h2 * 60 + m2


def parse_thai_date(text: str) -> date | None:
    """'5 ก.ย. 2569' → date(2026, 9, 5)  (พ.ศ. → ค.ศ.)"""
    m = _THAI_DATE_RE.search(text or "")
    if not m:
        return None
    day, mon_txt, year = m.groups()
    month = THAI_MONTHS.get(mon_txt)
    if month is None:
        return None
    y = int(year)
    if y > 2400:  # พ.ศ.
        y -= 543
    try:
        return date(y, month, int(day))
    except ValueError:
        return None


def be_to_ce(year: int) -> int:
    return year - 543 if year > 2400 else year


def clean(text: str | None) -> str:
    """ยุบช่องว่าง/ขึ้นบรรทัดใหม่/nbsp ให้เหลือช่องว่างเดียว"""
    return re.sub(r"[\s ]+", " ", text or "").strip()
