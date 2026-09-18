"""Parser หน้า "ตรวจสอบจบ" (graduate_check.asp) ของระบบทะเบียน มทร.ธัญบุรี

หน้านี้ต้องล็อกอินด้วยบัญชีนักศึกษา → นักศึกษาล็อกอินเอง แล้ว Save Page As (.html)
วางไฟล์ไว้ที่ data/raw/oreg/graduate_check_<รหัสนักศึกษา>.html
แล้วรัน:  python -m src.graduate_check data/raw/oreg/graduate_check_xxx.html

โครงสร้างหน้า (จากหน้าจริง 18 ก.ย. 2569):
  1166104620XX-X นายทดสอบ ระบบ   (ตัวอย่าง — ห้ามใส่ข้อมูลจริง)
  จำนวนหน่วยกิตขั้นต่ำ : 143   ปีสูงสุด : 8   GPAX ต่ำสุด : 2.00
  โครงสร้างหลักสูตร
    รวม  หน่วยกิตที่ผ่าน : -  GPA เฉลี่ย : -                     [ ] ผ่าน [ ] ไม่ผ่าน
    0 กลุ่มวิชาสมรรถนะ         หน่วยกิตต่ำสุด : -  หน่วยกิตสูงสุด : -  GPAX ต่ำสุด : 0.00
      ตาราง: รหัส | รายวิชา | หน่วยกิต | (ภาคการศึกษา/ปี) 1..5 | ระดับคะแนนครั้งที่ 1..5 | AVG | FINAL
      C0400011  Knowledge and Design of Basic Engineering  0 (0-0-0)  3/66  ผ่าน  0.00  0
      ...
    รวม  หน่วยกิตที่ผ่าน : -  GPA เฉลี่ย : 0.00                  [x] ผ่าน [ ] ไม่ผ่าน
    1 หมวดวิชาศึกษาทั่วไป      หน่วยกิตต่ำสุด : 30 ...
    รวม  หน่วยกิตที่ผ่าน : 20  GPA เฉลี่ย : 2.55  หน่วยกิตต่ำกว่าเกณฑ์   [ ] ผ่าน [x] ไม่ผ่าน
    1.1 กลุ่มคุณค่าแห่งชีวิตและหน้าที่พลเมือง  หน่วยกิตต่ำสุด : 7 ...
    1.1.1 รายวิชาสังคมศาสตร์ ...

ผลลัพธ์ = DegreeAudit → ใช้คำนวณ "เหลืออีกกี่หน่วยกิตในหมวดไหน" เพื่อวางแผนเรียนจบ
"""
from __future__ import annotations

import json
import re
import sys
from dataclasses import asdict, dataclass, field
from pathlib import Path

from bs4 import BeautifulSoup

PAGE_ENCODING = "cp874"  # หน้า oreg3 = windows-874/TIS-620

# รหัสวิชาปกติ 04000201-62 / รหัสสมรรถนะ C0400011 / รหัสเก่า 8 หลักไม่มีปี
_CODE_RE = re.compile(r"^(?:\d{8}-\d{2}|C\d{7}|\d{8}|\d{2}-\d{3}-\d{3})$")
_CREDIT_RE = re.compile(r"(\d+)\s*\(\s*(\d+)-(\d+)-(\d+)\s*\)")
_TERM_RE = re.compile(r"^(\d)/(\d{2})$")                 # "3/66" = เทอม 3 ปี 2566
_CATEGORY_HEAD_RE = re.compile(r"^(\d+(?:\.\d+)*)\s+(.+)$")   # "1.1 กลุ่มคุณค่าแห่งชีวิต..."
_NUM_RE = re.compile(r"-?\d+(?:\.\d+)?")
_GRADES_PASS = {"A", "B+", "B", "C+", "C", "D+", "D", "S", "ผ่าน", "P"}
_GRADES_FAIL = {"F", "U", "W", "I", "ไม่ผ่าน", "ไม่ สอบ", "ไม่สอบ", "ขาดสอบ"}


@dataclass
class Attempt:
    term: str            # "3/2566"
    grade: str           # "A" / "ผ่าน" / "ไม่สอบ" / "" (ยังไม่ออกเกรด)


@dataclass
class CourseRow:
    code: str
    name: str
    credits: int
    credit_text: str
    attempts: list[Attempt] = field(default_factory=list)
    avg: float | None = None
    final: float | None = None

    @property
    def passed(self) -> bool:
        return any(a.grade in _GRADES_PASS for a in self.attempts)

    @property
    def last_grade(self) -> str:
        return self.attempts[-1].grade if self.attempts else ""

    @property
    def taken(self) -> bool:
        return bool(self.attempts)


@dataclass
class Category:
    number: str          # "1.1.1"
    name: str            # "รายวิชาสังคมศาสตร์"
    min_credits: int | None = None
    max_credits: int | None = None
    min_gpax: float | None = None
    courses: list[CourseRow] = field(default_factory=list)
    # จากแถว "รวม" ที่ตามหลัง
    passed_credits: int | None = None
    gpa: float | None = None
    is_passed: bool | None = None
    below_min: bool = False      # ข้อความ "หน่วยกิตต่ำกว่าเกณฑ์"

    @property
    def depth(self) -> int:
        return self.number.count(".") + 1

    @property
    def remaining_credits(self) -> int | None:
        if self.min_credits is None:
            return None
        got = self.passed_credits if self.passed_credits is not None else sum(
            c.credits for c in self.courses if c.passed
        )
        return max(self.min_credits - got, 0)


@dataclass
class DegreeAudit:
    student_id: str
    student_name: str
    min_total_credits: int | None
    max_years: int | None
    min_gpax: float | None
    total_passed_credits: int | None
    gpa: float | None
    categories: list[Category] = field(default_factory=list)

    # ---------- สรุปเพื่อวางแผน ----------
    def all_courses(self) -> list[CourseRow]:
        return [c for cat in self.categories for c in cat.courses]

    def not_yet_passed(self) -> list[tuple[Category, CourseRow]]:
        """วิชาในโครงสร้างที่ยังไม่ผ่าน (ยังไม่ลง / ได้ F / W / ไม่สอบ)"""
        return [(cat, c) for cat in self.categories for c in cat.courses if not c.passed]

    def failed_courses(self) -> list[tuple[Category, CourseRow]]:
        return [(cat, c) for cat, c in self.not_yet_passed() if c.taken]

    def remaining_by_category(self) -> list[dict]:
        out = []
        for cat in self.categories:
            if cat.min_credits is None:
                continue
            out.append({
                "category": f"{cat.number} {cat.name}",
                "min": cat.min_credits,
                "passed": cat.passed_credits,
                "remaining": cat.remaining_credits,
                "status": "ผ่าน" if cat.is_passed else ("ไม่ผ่าน" if cat.is_passed is False else "-"),
            })
        return out

    def to_dict(self) -> dict:
        d = asdict(self)
        d["summary"] = {
            "remaining_by_category": self.remaining_by_category(),
            "failed_courses": [c.code for _, c in self.failed_courses()],
            "not_taken_courses": [c.code for _, c in self.not_yet_passed() if not c.taken],
        }
        return d


# ----------------------------------------------------------------------------
def _clean(t: str) -> str:
    return re.sub(r"[\s ]+", " ", t or "").strip()


def _num_after(text: str, label: str) -> float | None:
    m = re.search(re.escape(label) + r"\s*:?\s*(-?\d+(?:\.\d+)?|-)", text)
    if not m or m.group(1) == "-":
        return None
    return float(m.group(1))


def _int_after(text: str, label: str) -> int | None:
    v = _num_after(text, label)
    return int(v) if v is not None else None


def _parse_term(t: str) -> str | None:
    m = _TERM_RE.match(t)
    if not m:
        return None
    return f"{m.group(1)}/25{m.group(2)}"


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


def parse_graduate_check(raw: bytes | str) -> DegreeAudit:
    if isinstance(raw, bytes):
        raw = decode_html(raw)
    soup = BeautifulSoup(raw, "lxml")
    text = _clean(soup.get_text(" "))

    # ---- header ----
    sid_m = re.search(r"(\d{12}-\d)\s+(.+?)\s+ตรวจสอบจบ", text)
    audit = DegreeAudit(
        student_id=sid_m.group(1) if sid_m else "",
        student_name=_clean(sid_m.group(2)) if sid_m else "",
        min_total_credits=_int_after(text, "จำนวนหน่วยกิตขั้นต่ำ"),
        max_years=_int_after(text, "ปีสูงสุด"),
        min_gpax=_num_after(text, "GPAX ต่ำสุด"),
        total_passed_credits=None,
        gpa=None,
    )

    # ---- เดินทีละแถวของทุกตาราง (หน้าเป็น table ซ้อนกัน) ----
    current: Category | None = None
    first_total_seen = False
    for tr in soup.find_all("tr"):
        cells = [_clean(td.get_text(" ")) for td in tr.find_all("td", recursive=False)]
        cells = [c for c in cells if c != ""]
        if not cells:
            continue
        row_text = " ".join(cells)

        # 1) แถวหัวหมวด: "1.1 กลุ่มคุณค่า... หน่วยกิตต่ำสุด : 7 หน่วยกิตสูงสุด : - GPAX ต่ำสุด : 0.00"
        if "หน่วยกิตต่ำสุด" in row_text and "รวม" not in cells[0]:
            head = _CATEGORY_HEAD_RE.match(cells[0])
            if head:
                current = Category(
                    number=head.group(1),
                    name=_clean(re.split(r"หน่วยกิตต่ำสุด", head.group(2))[0]),
                    min_credits=_int_after(row_text, "หน่วยกิตต่ำสุด"),
                    max_credits=_int_after(row_text, "หน่วยกิตสูงสุด"),
                    min_gpax=_num_after(row_text, "GPAX ต่ำสุด"),
                )
                audit.categories.append(current)
            continue

        # 2) แถวสรุป "รวม หน่วยกิตที่ผ่าน : 20 GPA เฉลี่ย : 2.55 ..."
        if cells[0].startswith("รวม") and "หน่วยกิตที่ผ่าน" in row_text:
            passed = _int_after(row_text, "หน่วยกิตที่ผ่าน")
            gpa = _num_after(row_text, "GPA เฉลี่ย")
            is_passed = _checkbox_state(tr)
            if not first_total_seen:
                # แถว "รวม" แรกสุดคือของทั้งหลักสูตร (อยู่ก่อนหมวด 0)
                first_total_seen = True
                audit.total_passed_credits = passed
                audit.gpa = gpa
                continue
            if current is not None:
                current.passed_credits = passed
                current.gpa = gpa
                current.is_passed = is_passed
                current.below_min = "ต่ำกว่าเกณฑ์" in row_text
            continue

        # 3) แถวรายวิชา: รหัส | ชื่อ | หน่วยกิต | เทอม x5 | เกรด x5 | AVG | FINAL
        if current is not None and _CODE_RE.match(cells[0]):
            current.courses.append(_parse_course_row(tr))
            continue

    return audit


def _checkbox_state(tr) -> bool | None:
    """หาช่อง [x] ผ่าน / [x] ไม่ผ่าน ในแถว"""
    boxes = tr.find_all("input", {"type": "checkbox"})
    if len(boxes) >= 2:
        if boxes[0].has_attr("checked"):
            return True
        if boxes[1].has_attr("checked"):
            return False
        return None
    txt = _clean(tr.get_text(" "))
    if "☑ ผ่าน" in txt or "[x] ผ่าน" in txt.lower():
        return True
    if "☑ ไม่ผ่าน" in txt:
        return False
    return None


def _parse_course_row(tr) -> CourseRow:
    # เก็บ cell ทั้งหมด (รวมช่องว่าง) เพื่อรักษาตำแหน่งคอลัมน์ 5 เทอม + 5 เกรด
    tds = tr.find_all("td", recursive=False)
    cells = [_clean(td.get_text(" ")) for td in tds]
    code, name = cells[0], cells[1] if len(cells) > 1 else ""
    credit_text = cells[2] if len(cells) > 2 else ""
    cm = _CREDIT_RE.search(credit_text)
    credits = int(cm.group(1)) if cm else (int(credit_text) if credit_text.isdigit() else 0)

    rest = cells[3:]
    # ท้ายสุด 2 ช่องคือ AVG, FINAL (ถ้ามี)
    avg = final = None
    nums_tail = [c for c in rest[-2:] if _NUM_RE.fullmatch(c or "")]
    if len(rest) >= 2 and len(nums_tail) == 2:
        avg, final = float(rest[-2]), float(rest[-1])
        rest = rest[:-2]

    terms = [c for c in rest if _TERM_RE.match(c)]
    grades_zone = rest[len(rest) // 2:] if len(rest) >= 10 else rest[len(terms):]
    grades = [g for g in grades_zone if g and not _TERM_RE.match(g) and not _NUM_RE.fullmatch(g)]

    attempts = []
    for i, t in enumerate(terms):
        term = _parse_term(t) or t
        grade = grades[i] if i < len(grades) else ""
        attempts.append(Attempt(term=term, grade=grade))

    return CourseRow(
        code=code, name=name, credits=credits, credit_text=credit_text,
        attempts=attempts, avg=avg, final=final,
    )


# ----------------------------------------------------------------------------
def main(argv: list[str]) -> int:
    if len(argv) < 2:
        print("usage: python -m src.graduate_check <saved_graduate_check.html> [out.json]")
        return 1
    src = Path(argv[1])
    audit = parse_graduate_check(src.read_bytes())
    out = Path(argv[2]) if len(argv) > 2 else src.with_suffix(".json")
    out.write_text(json.dumps(audit.to_dict(), ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"นักศึกษา : {audit.student_id} {audit.student_name}")
    print(f"หน่วยกิตขั้นต่ำ {audit.min_total_credits}  ผ่านแล้ว {audit.total_passed_credits}  GPA {audit.gpa}")
    print("-" * 70)
    for row in audit.remaining_by_category():
        print(f"{row['category'][:45]:<45} ต่ำสุด {row['min']:>3}  ผ่าน {str(row['passed']):>3}  "
              f"เหลือ {str(row['remaining']):>3}  {row['status']}")
    print("-" * 70)
    failed = audit.failed_courses()
    if failed:
        print("วิชาที่ต้องลงใหม่ (ไม่ผ่าน):")
        for cat, c in failed:
            print(f"  {c.code}  {c.name}  [{c.last_grade}]  ({cat.number})")
    print(f"บันทึกผลที่ {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
