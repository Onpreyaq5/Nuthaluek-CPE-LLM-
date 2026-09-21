"""เดโม่ต้นแบบ: จัดตารางเรียนวิศวกรรมคอมพิวเตอร์ เทอม 1/2569 แล้วให้ 07 อธิบายผล

รัน:  PYTHONPATH=. python demo_plan.py

สิ่งที่เดโม่นี้แสดง
1. อ่านตารางสอนจำลอง (data/seed/cpe_timetable_1_2569.json)
2. เลือกวิชาแบบไม่ให้เวลาเรียน/เวลาสอบชนกัน และคุมหน่วยกิตให้อยู่ 9–21
3. ส่งผลเข้า explainer ของโมดูล 07 เพื่อให้ได้คำอธิบายภาษาคน
4. พิมพ์ตารางเรียนรายสัปดาห์

หมายเหตุ: ตัวเลือกวิชาในไฟล์นี้เป็น greedy อย่างง่ายไว้เดโม่เท่านั้น
ของจริงต้องเรียก `POST /plans/auto` ของโมดูล 06 ซึ่งใช้ CP-SAT และคิดเรื่อง
ความชอบ/ลำดับความสำคัญ/ความก้าวหน้าหลักสูตรครบกว่า
"""
from __future__ import annotations

import json
from pathlib import Path

from src.config import settings
from src.models.schemas import ConflictIn, ExplainPlanRequest, PlanItemIn
from src.services.explainer import explain_plan
from src.services.knowledge import knowledge_base

SEED = Path(__file__).parent / "data" / "seed" / "cpe_timetable_1_2569.json"
DAY_TH = ["จันทร์", "อังคาร", "พุธ", "พฤหัสบดี", "ศุกร์", "เสาร์", "อาทิตย์"]


def hhmm(minutes: int) -> str:
    return f"{minutes // 60:02d}:{minutes % 60:02d}"


def exams_clash(a: dict, b: dict) -> bool:
    for ea in a["exams"]:
        for eb in b["exams"]:
            if ea["exam_type"] != eb["exam_type"] or ea["exam_date"] != eb["exam_date"]:
                continue
            if ea["start_min"] < eb["end_min"] and eb["start_min"] < ea["end_min"]:
                return True
    return False


def pick_plan(sections: list[dict], min_credits: int, max_credits: int) -> tuple[list[dict], list[str]]:
    """เลือกหมู่เรียนแบบ greedy: วิชาสำคัญก่อน เลือกหมู่ที่ยังมีที่นั่งและไม่ชน"""
    by_course: dict[str, list[dict]] = {}
    for s in sections:
        by_course.setdefault(s["course_code"], []).append(s)

    # วิชาที่สำคัญกว่า (priority สูง) มาก่อน แล้วค่อยเรียงตามรหัส
    order = sorted(
        by_course.items(),
        key=lambda kv: (-max(s["priority_score"] for s in kv[1]), kv[0]),
    )

    chosen: list[dict] = []
    skipped: list[str] = []
    used_mask = 0
    credits = 0

    for code, options in order:
        if credits >= max_credits:
            break
        cost = options[0]["credits"]
        if credits + cost > max_credits:
            skipped.append(f"{code} (ลงแล้วจะเกิน {max_credits} หน่วยกิต)")
            continue

        placed = False
        for sec in sorted(options, key=lambda s: s["seat_taken"] - s["seat_total"]):
            if sec["seat_taken"] >= sec["seat_total"]:
                continue                                  # C6 ที่นั่งเต็ม
            if used_mask & sec["slots_mask"]:
                continue                                  # C1 เวลาเรียนชน
            if any(exams_clash(sec, c) for c in chosen):
                continue                                  # C2 เวลาสอบชน
            chosen.append(sec)
            used_mask |= sec["slots_mask"]
            credits += cost
            placed = True
            break
        if not placed:
            skipped.append(f"{code} (ทุกหมู่ชนกับวิชาที่เลือกไว้ หรือที่นั่งเต็ม)")

    return chosen, skipped


def print_week(chosen: list[dict]) -> None:
    rows: dict[int, list[tuple[int, int, str, str]]] = {}
    for s in chosen:
        for m in s["meetings"]:
            kind = "ปฏิบัติ" if m["meeting_type"] == "lab" else "บรรยาย"
            rows.setdefault(m["day"], []).append(
                (m["start_min"], m["end_min"], f"{s['course_code']} ม.{s['section']}",
                 f"{kind} {m['room']}")
            )
    print("\n" + "=" * 64)
    print(" ตารางเรียนรายสัปดาห์")
    print("=" * 64)
    for day in range(7):
        if day not in rows:
            print(f" {DAY_TH[day]:<10} — ว่าง —")
            continue
        for i, (st, en, code, note) in enumerate(sorted(rows[day])):
            label = DAY_TH[day] if i == 0 else ""
            print(f" {label:<10} {hhmm(st)}-{hhmm(en)}  {code:<18} {note}")


def main() -> None:
    data = json.loads(SEED.read_text(encoding="utf-8"))
    rule = data["credit_rule"]
    print("=" * 64)
    print(f" ต้นแบบจัดตารางเรียน {data['faculty']} / {data['program_id']}")
    print(f" ภาคการศึกษา {data['term']}  |  กติกา {rule['min_credits']}–{rule['max_credits']} หน่วยกิต")
    print(f" {data['disclaimer']}")
    print("=" * 64)

    chosen, skipped = pick_plan(data["sections"], rule["min_credits"], rule["max_credits"])
    total = sum(s["credits"] for s in chosen)

    print(f"\nเลือกได้ {len(chosen)} วิชา รวม {total} หน่วยกิต\n")
    for s in sorted(chosen, key=lambda x: x["course_code"]):
        days = "/".join(sorted({DAY_TH[m["day"]] for m in s["meetings"]}))
        seat = f"{s['seat_total'] - s['seat_taken']} ที่ว่าง"
        print(f"  {s['course_code']} ม.{s['section']}  {s['course_name'][:34]:<36}"
              f" {s['credits']} นก.  {days:<16} {seat}")

    if skipped:
        print("\nวิชาที่ยังไม่ได้ลงเทอมนี้:")
        for line in skipped:
            print(f"  - {line}")

    print_week(chosen)

    # ── ให้โมดูล 07 อธิบายผล ────────────────────────────────────
    knowledge_base.load()
    plan_items = [
        PlanItemIn(course_code=s["course_code"], section=s["section"],
                   course_name=s["course_name"], credits=s["credits"])
        for s in chosen
    ]
    result = explain_plan(ExplainPlanRequest(term=data["term"], plan=plan_items))

    print("\n" + "=" * 64)
    print(" คำอธิบายจากระบบ (โมดูล 07)")
    print("=" * 64)
    print(f" {result.headline}\n")
    print(result.explanation)
    if result.next_steps:
        print("\n ขั้นตอนถัดไป:")
        for step in result.next_steps:
            print(f"  - {step}")
    print(f"\n ตรวจหน่วยกิต: {result.credit_check}")
    print(f"\n {result.disclaimer}")

    # ── ตัวอย่างแผนที่ผิดกติกา เพื่อให้เห็นว่าระบบจับได้ ─────────
    print("\n" + "=" * 64)
    print(" ตัวอย่างแผนที่ระบบปฏิเสธ")
    print("=" * 64)
    bad = explain_plan(ExplainPlanRequest(
        term=data["term"],
        plan=plan_items[:2],
        conflicts=[ConflictIn(
            code="C1", severity="ERROR", message_key="time_clash",
            message_th="04100201-66 หมู่ 01 เรียนทับกับ 04100202-66 หมู่ 01",
            subjects=["04100201-66-01", "04100202-66-01"],
            detail={"day": 0, "overlap_start": 540, "overlap_end": 660},
            suggestions=[{"action": "change_section", "to": "04100201-66-02"}],
        )],
    ))
    print(f" {bad.headline}\n")
    print(bad.explanation)
    print(f"\n ผลตรวจ: verdict={bad.verdict} | หน่วยกิต={bad.credit_check['status']}")
    print(f" อ้างอิงระเบียบ: {[s.section or s.title for s in bad.sources]}")


if __name__ == "__main__":
    main()
