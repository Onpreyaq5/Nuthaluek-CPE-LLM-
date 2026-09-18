"""Adapter: ระบบบริการการศึกษา มทร.ธัญบุรี (oreg3.rmutt.ac.th — Vision Net)

หน้าที่ parse ได้
  1. ค้นหารายวิชา (ผลการค้นหา)  → parse_search_results()
     คอลัมน์: รหัสวิชา | ชื่อรายวิชา | หน่วยกิต | กลุ่ม | รับ | ลง | เหลือ | สถานะ | ระดับ
  2. รายละเอียดรายวิชา          → parse_course_detail()
     header + บล็อกต่อกลุ่ม: วัน/เวลา/ห้อง/อาคาร/เรียน(C,L)/ที่นั่ง/หมวด
     + อาจารย์ + สำรองสำหรับ + สอบกลางภาค + สอบปลายภาค + หมายเหตุ

การเข้าถึง
  ทุกหน้าต้องล็อกอินด้วยบัญชีนักศึกษา → ระบบนี้ **ไม่เก็บ/ไม่กรอกรหัสผ่านให้ใคร**
  รับ HTML ได้ 2 ทาง
    a) นักศึกษาล็อกอินเองในเบราว์เซอร์ → Save Page As (.html) → วางใน data/raw/oreg/
    b) นักศึกษาส่ง session cookie ของตัวเองให้ fetch (ใช้เฉพาะข้อมูลของตัวเอง, rate-limit)

หมายเหตุ: parser เขียนแบบ "อ่านจากข้อความ" ไม่พึ่ง class/id ของ HTML
เพราะหน้า Vision Net เป็น table ซ้อน table ไม่มี id ที่แน่นอน
เมื่อได้ HTML จริงแล้วให้เพิ่ม fixture ใน tests/fixtures/ และปรับ selector ตามจริง
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import date

from bs4 import BeautifulSoup, Tag

from .thai_text import (
    COURSE_CODE_RE,
    Credit,
    clean,
    parse_credit,
    parse_day,
    parse_thai_date,
    parse_time_range,
)

PAGE_ENCODING = "cp874"  # หน้า oreg3 ประกาศ charset=windows-874 (TIS-620) → Python เรียก cp874


def decode_html(raw: bytes) -> str:
    """หน้าจริงเป็น windows-874 แต่ถ้า Save Page As จากเบราว์เซอร์อาจถูกแปลงเป็น UTF-8
    → ดู charset ใน <meta> ก่อน ถ้าไม่มีให้ลอง utf-8 แล้วค่อย fallback cp874"""
    head = raw[:4096].decode("ascii", errors="ignore").lower()
    m = re.search(r'charset=["\']?\s*([\w-]+)', head)
    if m:
        enc = m.group(1)
        enc = "cp874" if enc in ("windows-874", "tis-620", "iso-8859-11") else enc
        try:
            return raw.decode(enc)
        except (LookupError, UnicodeDecodeError):
            pass
    try:
        return raw.decode("utf-8")
    except UnicodeDecodeError:
        return raw.decode(PAGE_ENCODING, errors="replace")


def load_html(raw: bytes | str) -> BeautifulSoup:
    if isinstance(raw, bytes):
        raw = decode_html(raw)
    return BeautifulSoup(raw, "lxml")


# ----------------------------------------------------------------------------
# 1) ผลการค้นหารายวิชา
# ----------------------------------------------------------------------------
@dataclass
class SearchRow:
    course_code: str          # "04000201-62"
    curriculum_year: int      # 62 → หลักสูตรปี 2562
    name_th: str
    credit: Credit | None
    section: str              # "1"
    seat_total: int | None    # รับ
    seat_taken: int | None    # ลง
    seat_left: int | None     # เหลือ
    status: str               # "W"
    level: str                # "ระดับปริญญาตรี ภาคปกติ" / "เทียบโอน ภาคพิเศษ"
    term: str | None = None   # "1/2569" (เติมจาก header ของหน้า)


_TERM_RE = re.compile(r"ปีการศึกษา\s*(\d{4})\s*/\s*(\d)")


def _int_or_none(text: str) -> int | None:
    t = clean(text)
    return int(t) if t.isdigit() else None


def parse_search_results(raw: bytes | str) -> list[SearchRow]:
    soup = load_html(raw)
    page_text = soup.get_text(" ")
    term = None
    m = _TERM_RE.search(page_text)
    if m:
        term = f"{m.group(2)}/{m.group(1)}"  # "1/2569"

    rows: list[SearchRow] = []
    for tr in soup.find_all("tr"):
        cells = [clean(td.get_text(" ")) for td in tr.find_all("td", recursive=False)]
        if len(cells) < 8:
            continue
        code_m = COURSE_CODE_RE.search(cells[0])
        if not code_m:
            continue
        # โครงคอลัมน์ตามหน้าจริง: รหัส | ชื่อ | หน่วยกิต | กลุ่ม | รับ | ลง | เหลือ | สถานะ | ระดับ
        rows.append(
            SearchRow(
                course_code=f"{code_m.group(1)}-{code_m.group(2)}",
                curriculum_year=int(code_m.group(2)),
                name_th=cells[1],
                credit=parse_credit(cells[2]),
                section=cells[3],
                seat_total=_int_or_none(cells[4]),
                seat_taken=_int_or_none(cells[5]),
                seat_left=_int_or_none(cells[6]),
                status=cells[7],
                level=cells[8] if len(cells) > 8 else "",
                term=term,
            )
        )
    return rows


# ----------------------------------------------------------------------------
# 2) รายละเอียดรายวิชา
# ----------------------------------------------------------------------------
@dataclass
class Meeting:
    day: int | None           # 0=จันทร์ .. 6=อาทิตย์
    day_text: str
    start_min: int
    end_min: int
    room: str
    building: str
    meeting_type: str         # "C" = บรรยาย (lecture), "L" = ปฏิบัติ (lab)


@dataclass
class Exam:
    exam_date: date | None
    start_min: int | None
    end_min: int | None
    building: str
    room: str
    raw: str


@dataclass
class SectionDetail:
    section: str              # "02"
    meetings: list[Meeting] = field(default_factory=list)
    seat_total: int | None = None
    seat_taken: int | None = None
    seat_left: int | None = None
    status: str = ""          # หมวด "W"
    teachers: list[str] = field(default_factory=list)
    reserved_for: str = ""    # "วิศวกรรมอิเล็กทรอนิกส์ฯ ชั้นปี 3 กลุ่ม 1  29-26-3"
    midterm: Exam | None = None
    final: Exam | None = None
    note: str = ""            # "67146ETE1"
    level: str = ""           # "ระดับ 20: ปริญญาตรี ภาคปกติ"


@dataclass
class CourseDetail:
    course_code: str
    name_en: str
    name_th: str
    faculty: str
    credit: Credit | None
    status: str
    term: str | None
    sections: list[SectionDetail] = field(default_factory=list)


_SEAT_RE = re.compile(r"\b(\d{1,3})\s+(\d{1,3})\s+(\d{1,3})\b")
_LEVEL_RE = re.compile(r"ระดับ\s*\d+\s*:\s*[^\n]+")
_SECTION_HEAD_RE = re.compile(r"^(\d{1,2})$")
_TERM_DETAIL_RE = re.compile(r"เลือก\s*ปีการศึกษา\s*:?\s*(\d)\s*/\s*(\d{4})")


def _parse_exam(text: str) -> Exam:
    t = clean(text)
    tr = parse_time_range(t)
    b = re.search(r"อาคาร\s*(\S+)", t)
    r = re.search(r"ห้อง\s*(\S+)", t)
    return Exam(
        exam_date=parse_thai_date(t),
        start_min=tr[0] if tr else None,
        end_min=tr[1] if tr else None,
        building=b.group(1) if b else "",
        room=r.group(1) if r else "",
        raw=t,
    )


def _label_value(block_text: str, label: str) -> str:
    """ดึงข้อความหลัง label เช่น 'อาจารย์:' จนถึง label ถัดไป"""
    labels = ["อาจารย์", "สำรอง สำหรับ", "สำรองสำหรับ", "สอบกลาง ภาค", "สอบกลางภาค",
              "สอบปลาย ภาค", "สอบปลายภาค", "หมายเหตุ"]
    start = block_text.find(label)
    if start < 0:
        return ""
    start += len(label)
    end = len(block_text)
    for other in labels:
        if other == label:
            continue
        pos = block_text.find(other, start)
        if 0 <= pos < end:
            end = pos
    return clean(block_text[start:end]).lstrip(":").strip()


def parse_course_detail(raw: bytes | str) -> CourseDetail:
    soup = load_html(raw)
    text = clean(soup.get_text(" "))

    code_m = COURSE_CODE_RE.search(text)
    code = f"{code_m.group(1)}-{code_m.group(2)}" if code_m else ""
    # header: "04000201-62 English for Engineering ภาษาอังกฤษสำหรับงานวิศวกรรม สังกัด คณะ..."
    name_en = ""
    name_th = ""
    if code_m:
        after = text[code_m.end():]
        head = re.split(r"สังกัด", after, maxsplit=1)[0]
        parts = head.strip().split(" ")
        en, th = [], []
        for p in parts:
            (th if re.search(r"[฀-๿]", p) else en).append(p)
        name_en, name_th = " ".join(en).strip(), " ".join(th).strip()

    faculty = _label_value(text, "สังกัด").split(" หน่วยกิต")[0]
    credit = parse_credit(_label_value(text, "หน่วยกิต"))
    status_m = re.search(r"สถานะรายวิชา\s*:?\s*(\S+)", text)
    term_m = _TERM_DETAIL_RE.search(text)
    term = f"{term_m.group(1)}/{term_m.group(2)}" if term_m else None

    detail = CourseDetail(
        course_code=code,
        name_en=name_en,
        name_th=name_th,
        faculty=clean(faculty),
        credit=credit,
        status=status_m.group(1) if status_m else "",
        term=term,
    )

    # ---- บล็อกต่อกลุ่ม: หาแถวที่ cell แรกเป็นเลขกลุ่ม แล้วมีวัน+เวลา ----
    current_level = ""
    current: SectionDetail | None = None
    for tr in soup.find_all("tr"):
        row_text = clean(tr.get_text(" "))
        lvl = _LEVEL_RE.search(row_text)
        if lvl and len(row_text) < 80:
            current_level = lvl.group(0)
            continue

        tds = tr.find_all("td", recursive=False)
        cells = [clean(td.get_text(" ")) for td in tds]
        # แถว meeting ต่อเนื่องของกลุ่มเดิม ช่อง "กลุ่ม" จะว่าง → ตัดช่องว่างนำหน้าออก
        while cells and cells[0] == "":
            cells.pop(0)
        if not cells:
            continue

        # แถวหัวกลุ่ม: "02 | เสาร์ | 13:00-15:00 | N/A | C | 29 26 3 | W"
        if _SECTION_HEAD_RE.match(cells[0]) and parse_day(cells[1] if len(cells) > 1 else "") is not None:
            current = SectionDetail(section=cells[0].zfill(2), level=current_level)
            detail.sections.append(current)
            seat_m = _SEAT_RE.search(" ".join(cells[2:]))
            if seat_m:
                current.seat_total, current.seat_taken, current.seat_left = (
                    int(g) for g in seat_m.groups()
                )
            st = [c for c in cells if c in ("W", "R", "C")]  # หมวด W (ลงทะเบียนผ่านเว็บ)
            if st:
                current.status = st[-1]
            _append_meeting(current, cells[1:])
            continue

        # แถว meeting เพิ่มเติมของกลุ่มเดิม: "เสาร์ | 15:00-17:00 | N/A | L"
        if current and parse_day(cells[0]) is not None and len(cells) >= 2:
            _append_meeting(current, cells)
            continue

        # แถวรายละเอียด (อาจารย์/สำรอง/สอบ/หมายเหตุ) มักอยู่ใน tr เดียวเป็นข้อความยาว
        if current and any(k in row_text for k in ("อาจารย์", "สอบกลาง", "สอบปลาย", "หมายเหตุ")):
            if "อาจารย์" in row_text and not current.teachers:
                t = _label_value(row_text, "อาจารย์")
                current.teachers = [clean(x) for x in re.split(r"[,/]", t) if clean(x)]
            if "สำรอง" in row_text and not current.reserved_for:
                current.reserved_for = _label_value(row_text, "สำรอง สำหรับ") or _label_value(row_text, "สำรองสำหรับ")
            if "สอบกลาง" in row_text and current.midterm is None:
                v = _label_value(row_text, "สอบกลาง ภาค") or _label_value(row_text, "สอบกลางภาค")
                if v:
                    current.midterm = _parse_exam(v)
            if "สอบปลาย" in row_text and current.final is None:
                v = _label_value(row_text, "สอบปลาย ภาค") or _label_value(row_text, "สอบปลายภาค")
                if v:
                    current.final = _parse_exam(v)
            if "หมายเหตุ" in row_text and not current.note:
                current.note = _label_value(row_text, "หมายเหตุ")

    return detail


def _append_meeting(section: SectionDetail, cells: list[str]) -> None:
    """cells เริ่มที่วัน: [วัน, เวลา, ห้อง, อาคาร?, เรียน(C/L), ...]"""
    day_text = cells[0]
    tr = parse_time_range(cells[1] if len(cells) > 1 else "")
    if tr is None:
        return
    rest = cells[2:]
    mtype = next((c for c in rest if c in ("C", "L")), "")
    others = [c for c in rest if c not in ("C", "L") and not _SEAT_RE.search(c) and c not in ("W", "R")]
    room = others[0] if others else ""
    building = others[1] if len(others) > 1 else ""
    section.meetings.append(
        Meeting(
            day=parse_day(day_text),
            day_text=day_text,
            start_min=tr[0],
            end_min=tr[1],
            room=room,
            building=building,
            meeting_type=mtype,
        )
    )
