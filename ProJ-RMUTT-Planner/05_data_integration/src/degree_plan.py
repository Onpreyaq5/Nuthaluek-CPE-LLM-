"""เชื่อม "ตรวจสอบจบ" (DegreeAudit) เข้ากับ "วิชาที่เปิดสอนเทอมนี้" (ผลค้นหารายวิชา)
→ ได้รายการ "วิชาที่ควรลง + ลงได้จริง" ส่งต่อให้ 06_schedule_conflict_engine จัดตาราง

ใช้กับ 2 กลุ่ม
  - นักศึกษาปัจจุบัน : ดูว่าเหลืออะไร ต้องลงใหม่อะไร แล้ววางแผนให้จบตามเกณฑ์
  - น้องปี 2 (เพิ่งเข้าวิศวะคอม) : ยังไม่มีประวัติมาก → ใช้โครงสร้างหลักสูตรจากหน้าเดียวกัน
    เป็น "แผนที่ 4 ปี" แล้วให้ระบบเรียงลำดับว่าเทอมนี้ควรลงอะไรก่อน

รัน:
  python -m src.degree_plan data/raw/oreg/graduate_check_xxx.html data/raw/oreg/search_1-2569.html
"""
from __future__ import annotations

import json
import sys
from dataclasses import asdict, dataclass, field
from pathlib import Path

from .graduate_check import Category, CourseRow, DegreeAudit, parse_graduate_check

# ลำดับความสำคัญ (ตรงกับ 06_schedule_conflict_engine/03_process.txt)
P0_RETAKE = 0      # เคยลงแล้วไม่ผ่าน (F / W / ไม่สอบ) → ต้องลงใหม่ก่อน
P1_REQUIRED = 1    # วิชาในหมวดที่ "ไม่ผ่าน" และหน่วยกิตยังต่ำกว่าเกณฑ์
P2_UNLOCK = 2      # วิชาที่ปลดล็อกวิชาอื่น (ต้องมี prereq graph — เติมภายหลัง)
P3_OTHER = 3       # วิชาที่เหลือ / เลือกเสรี


@dataclass
class Candidate:
    code: str
    name: str
    credits: int
    category: str          # "2.1 กลุ่มวิชาพื้นฐานวิชาชีพ"
    priority: int
    reason: str
    last_grade: str = ""
    open_sections: list[dict] = field(default_factory=list)  # จากผลค้นหารายวิชา (ถ้ามี)

    @property
    def is_open_this_term(self) -> bool:
        return bool(self.open_sections)


@dataclass
class DegreePlanInput:
    student_id: str
    term: str | None
    min_total_credits: int | None
    passed_credits: int | None
    remaining_total: int | None
    categories: list[dict]
    candidates: list[Candidate]

    def to_dict(self) -> dict:
        d = asdict(self)
        d["stats"] = {
            "candidates": len(self.candidates),
            "open_this_term": sum(1 for c in self.candidates if c.is_open_this_term),
            "must_retake": sum(1 for c in self.candidates if c.priority == P0_RETAKE),
        }
        return d


def _base_code(code: str) -> str:
    """'04000202-63' → '04000202'  (รหัสเดียวกันต่างปีหลักสูตร ให้ถือว่าเทียบเท่ากันเบื้องต้น)"""
    return code.split("-")[0]


def build_candidates(audit: DegreeAudit, prereq_dag: Any | None = None) -> list[Candidate]:
    out: list[Candidate] = []
    critical_scores = prereq_dag.calculate_critical_path_scores() if prereq_dag else {}
    for cat in audit.categories:
        cat_label = f"{cat.number} {cat.name}"
        cat_needs_more = (cat.is_passed is False) or cat.below_min
        for c in cat.courses:
            if c.passed:
                continue
            unlocks_count = len(prereq_dag.get_all_unlocks(c.code)) if prereq_dag else 0
            if c.taken:
                pr, why = P0_RETAKE, f"เคยลงแล้วได้ {c.last_grade} ต้องลงใหม่"
            elif cat_needs_more:
                pr, why = P1_REQUIRED, f"หมวด {cat.number} ยังขาดอีก {cat.remaining_credits} หน่วยกิต"
            elif unlocks_count > 0:
                pr, why = P2_UNLOCK, f"ปลดล็อกวิชาอื่นอีก {unlocks_count} วิชา (Critical Path Score: {critical_scores.get(c.code, 0)})"
            else:
                pr, why = P3_OTHER, "อยู่ในโครงสร้างหลักสูตร ยังไม่ได้ลง"
            out.append(Candidate(
                code=c.code, name=c.name, credits=c.credits, category=cat_label,
                priority=pr, reason=why, last_grade=c.last_grade,
            ))
    out.sort(key=lambda x: (x.priority, x.category, x.code))
    return out


def attach_open_sections(candidates: list[Candidate], search_rows: list) -> None:
    """search_rows = list[SearchRow] จาก 04_course_data_services.adapters.oreg_rmutt"""
    by_base: dict[str, list] = {}
    for r in search_rows:
        by_base.setdefault(_base_code(r.course_code), []).append(r)
    for c in candidates:
        for r in by_base.get(_base_code(c.code), []):
            c.open_sections.append({
                "course_code": r.course_code, "section": r.section,
                "seat_left": r.seat_left, "level": r.level, "term": r.term,
            })


def build_plan_input(
    audit: DegreeAudit,
    search_rows: list | None = None,
    prereq_dag: Any | None = None,
) -> DegreePlanInput:
    cands = build_candidates(audit, prereq_dag=prereq_dag)
    term = None
    if search_rows:
        attach_open_sections(cands, search_rows)
        term = next((r.term for r in search_rows if r.term), None)
    remaining_total = None
    if audit.min_total_credits is not None and audit.total_passed_credits is not None:
        remaining_total = max(audit.min_total_credits - audit.total_passed_credits, 0)
    return DegreePlanInput(
        student_id=audit.student_id,
        term=term,
        min_total_credits=audit.min_total_credits,
        passed_credits=audit.total_passed_credits,
        remaining_total=remaining_total,
        categories=audit.remaining_by_category(),
        candidates=cands,
    )


def main(argv: list[str]) -> int:
    if len(argv) < 2:
        print("usage: python -m src.degree_plan <graduate_check.html> [search_results.html] [out.json]")
        return 1
    audit = parse_graduate_check(Path(argv[1]).read_bytes())
    rows = None
    if len(argv) > 2 and argv[2].endswith(".html"):
        # import แบบ lazy เพราะอยู่คนละ service (ตอน deploy จริงจะเรียกผ่าน HTTP ไป 04)
        # ทั้ง 2 service ใช้ชื่อ package "src" เหมือนกัน → โหลดของ 04 ภายใต้ชื่อ oreg_adapters แทน
        import importlib
        import types

        adapters_dir = Path(__file__).resolve().parents[2] / "04_course_data_services" / "src" / "adapters"
        pkg = types.ModuleType("oreg_adapters")
        pkg.__path__ = [str(adapters_dir)]  # type: ignore[attr-defined]
        sys.modules["oreg_adapters"] = pkg
        oreg = importlib.import_module("oreg_adapters.oreg_rmutt")
        rows = oreg.parse_search_results(Path(argv[2]).read_bytes())
    plan = build_plan_input(audit, rows)
    out = Path(argv[3]) if len(argv) > 3 else Path(argv[1]).with_name("degree_plan_input.json")
    out.write_text(json.dumps(plan.to_dict(), ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"{plan.student_id}  เหลืออีก {plan.remaining_total} หน่วยกิต (จาก {plan.min_total_credits})")
    print("-" * 78)
    for c in plan.candidates:
        opened = f"เปิด {len(c.open_sections)} กลุ่ม" if c.open_sections else ("-" if rows is None else "ไม่เปิดเทอมนี้")
        print(f"P{c.priority}  {c.code:<12} {c.name[:34]:<34} {c.credits}นก  {opened:<14} {c.reason}")
    print(f"บันทึกที่ {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
