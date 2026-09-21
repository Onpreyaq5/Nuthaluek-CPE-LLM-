"""แปลงผลตรวจตารางชนจากโมดูล 06 ให้เป็นคำอธิบายภาษาคน

หลักการสำคัญ: โมดูลนี้ **ไม่คำนวณอะไรเองเลย**
ตัวเลขเวลา/หน่วยกิต/รหัสวิชา หยิบมาจากสิ่งที่ 06 ส่งมาทั้งหมด
หน้าที่ของไฟล์นี้คือเรียบเรียงให้นักศึกษาอ่านรู้เรื่องและบอกว่าต้องทำอะไรต่อ
"""
from __future__ import annotations

from ..config import DISCLAIMER, settings
from ..models.schemas import (
    ConflictIn,
    ExplainPlanRequest,
    ExplainPlanResponse,
    Source,
)
from .knowledge import knowledge_base

DAY_TH = ["จันทร์", "อังคาร", "พุธ", "พฤหัสบดี", "ศุกร์", "เสาร์", "อาทิตย์"]

# ข้อความอธิบายต่อรหัสปัญหา — ตรงกับ C1-C6 / W1-W5 ของโมดูล 06
CODE_LABEL = {
    "C1": "เวลาเรียนชนกัน",
    "C2": "เวลาสอบชนกัน",
    "C3": "ยังไม่ผ่านวิชาบังคับก่อน",
    "C4": "หน่วยกิตไม่อยู่ในเกณฑ์",
    "C5": "ลงวิชาซ้ำ",
    "C6": "ที่นั่งเต็ม",
    "W1": "เรียนติดกันยาวเกินไป",
    "W2": "มีช่องว่างระหว่างคาบนาน",
    "W3": "มีคาบเรียนเช้าในวันที่ขอว่าง",
    "W4": "เวลาย้ายอาคารกระชั้น",
    "W5": "ต้องมามหาวิทยาลัยหลายวัน",
}

# คำแนะนำว่าควรทำอะไรต่อ
CODE_ACTION = {
    "C1": "เปลี่ยนหมู่เรียนของวิชาใดวิชาหนึ่งให้เป็นคาบที่ไม่ทับกัน",
    "C2": "เปลี่ยนหมู่เรียน หรือติดต่อฝ่ายวิชาการคณะเพื่อขอจัดสอบซ้อนล่วงหน้าอย่างน้อย 1 สัปดาห์",
    "C3": "ลงวิชาบังคับก่อนให้ผ่านก่อน แล้วค่อยลงวิชานี้ในเทอมถัดไป",
    "C4": f"ปรับจำนวนหน่วยกิตให้อยู่ระหว่าง {settings.min_credits}–{settings.max_credits} หน่วยกิต",
    "C5": "เอาวิชาที่ซ้ำออก เหลือไว้หมู่เดียว",
    "C6": "เลือกหมู่เรียนอื่นที่ยังมีที่นั่ง หรือยื่นคำร้องขอเพิ่มที่นั่งที่ภาควิชา",
    "W1": "ลองสลับหมู่เรียนให้มีเวลาพักกลางวัน",
    "W2": "ลองเลือกหมู่ที่คาบอยู่ติดกันมากขึ้น จะได้ไม่ต้องรอนาน",
    "W3": "ถ้าต้องการวันว่างจริง ๆ ให้เลือกหมู่ที่ไม่มีคาบในวันนั้น",
    "W4": "เผื่อเวลาเดินทางระหว่างอาคาร หรือเลือกหมู่ที่เรียนอาคารเดียวกัน",
    "W5": "ลองรวมวิชาให้อยู่ในวันน้อยลง จะได้มีวันว่างเต็มวัน",
}


def _fmt_minutes(value: object) -> str:
    """540 -> '09:00'  (ถ้าไม่ใช่ตัวเลขให้คืนค่าเดิม)"""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return str(value)
    total = int(value)
    return f"{total // 60:02d}:{total % 60:02d}"


def _describe_detail(item: ConflictIn) -> str:
    """ประกอบรายละเอียดจาก detail ที่ 06 ส่งมา (ไม่คำนวณเพิ่ม)"""
    d = item.detail or {}
    bits: list[str] = []

    day = d.get("day")
    if isinstance(day, int) and 0 <= day <= 6:
        bits.append(f"วัน{DAY_TH[day]}")
    elif isinstance(day, str) and day:
        bits.append(str(day))

    start, end = d.get("overlap_start", d.get("start_min")), d.get("overlap_end", d.get("end_min"))
    if start is not None and end is not None:
        bits.append(f"ช่วง {_fmt_minutes(start)}–{_fmt_minutes(end)}")

    if d.get("exam_date"):
        bits.append(f"วันสอบ {d['exam_date']}")
    if d.get("missing"):
        bits.append(f"ต้องผ่าน {', '.join(map(str, d['missing']))} ก่อน")
    if d.get("total_credits") is not None:
        bits.append(f"รวม {d['total_credits']} หน่วยกิต")
    if d.get("seat_left") is not None:
        bits.append(f"เหลือ {d['seat_left']} ที่นั่ง")

    return " ".join(bits)


def _line_for(item: ConflictIn) -> str:
    label = CODE_LABEL.get(item.code, item.message_key or item.code)
    subjects = " กับ ".join(item.subjects) if item.subjects else ""
    detail = _describe_detail(item)

    # ถ้า 06 เขียนข้อความไทยมาให้แล้ว ใช้ของเขาเป็นหลัก
    if item.message_th:
        head = item.message_th
    else:
        head = f"{label}" + (f": {subjects}" if subjects else "")

    parts = [f"- **{label}** — {head}"]
    if detail:
        parts.append(f"  ({detail})")
    action = CODE_ACTION.get(item.code)
    if action:
        parts.append(f"\n  แนะนำ: {action}")
    if item.suggestions:
        for s in item.suggestions[:2]:
            to = s.get("to") or s.get("section") or s.get("value")
            if to:
                parts.append(f"\n  ตัวเลือก: เปลี่ยนเป็น {to}")
    return "".join(parts)


def check_credits(total_credits: int | None, term: str = "") -> dict:
    """ตรวจว่าหน่วยกิตอยู่ในเกณฑ์ไหม — ใช้ค่าจาก settings ไม่ hardcode"""
    is_summer = term.startswith("3/")
    max_credits = settings.summer_max_credits if is_summer else settings.max_credits
    min_credits = 0 if is_summer else settings.min_credits

    if total_credits is None:
        return {"status": "unknown", "min": min_credits, "max": max_credits}

    if total_credits > max_credits:
        status, note = "over", f"เกินเพดาน {max_credits} หน่วยกิตอยู่ {total_credits - max_credits}"
    elif total_credits < min_credits:
        status, note = "under", f"ยังขาดอีก {min_credits - total_credits} หน่วยกิตถึงจะครบขั้นต่ำ"
    else:
        status, note = "ok", "อยู่ในเกณฑ์"

    return {
        "status": status,
        "total_credits": total_credits,
        "min": min_credits,
        "max": max_credits,
        "term_type": "summer" if is_summer else "regular",
        "note": note,
    }


def _regulation_sources(codes: set[str]) -> list[Source]:
    """ดึงระเบียบที่เกี่ยวข้องกับปัญหาที่เจอ มาแนบเป็นแหล่งอ้างอิง"""
    if not knowledge_base.ready:
        return []
    queries = []
    if {"C1", "C2"} & codes:
        queries.append("ห้ามลงทะเบียนรายวิชาที่เวลาเรียนหรือเวลาสอบซ้ำซ้อน")
    if "C3" in codes:
        queries.append("รายวิชาบังคับก่อน prerequisite ต้องสอบผ่านก่อน")
    if "C4" in codes:
        queries.append("จำนวนหน่วยกิตต่อภาคการศึกษา ไม่น้อยกว่า 9 ไม่เกิน 21")

    seen: dict[str, Source] = {}
    for q in queries:
        for c in knowledge_base.search(q, top_k=1):
            if c.doc_id not in seen:
                seen[c.doc_id] = Source(
                    doc_id=c.doc_id, title=c.title, section=c.section,
                    doc_type=c.doc_type, effective_year=c.effective_year, score=c.score,
                )
    return list(seen.values())


def explain_plan(req: ExplainPlanRequest) -> ExplainPlanResponse:
    errors = [c for c in req.conflicts if c.severity == "ERROR"]
    non_errors = [c for c in req.conflicts if c.severity != "ERROR"] + list(req.warnings)

    total_credits = req.total_credits
    if total_credits is None and req.plan:
        total_credits = sum(item.credits for item in req.plan)
    credit_check = check_credits(total_credits, req.term)

    # ── สรุปหัวเรื่อง ────────────────────────────────────────────
    if errors:
        verdict = "blocked"
        headline = f"แผนนี้ยังลงทะเบียนไม่ได้ — ติดปัญหา {len(errors)} เรื่อง"
    elif non_errors or credit_check["status"] in {"over", "under"}:
        verdict = "warning"
        headline = "แผนนี้ลงทะเบียนได้ แต่มีข้อควรระวัง"
    else:
        verdict = "ok"
        headline = "แผนนี้ใช้ได้ ไม่มีวิชาไหนชนกัน"

    # ── เนื้อคำอธิบาย ───────────────────────────────────────────
    body: list[str] = []
    if req.plan:
        courses = ", ".join(
            f"{p.course_code}" + (f" หมู่ {p.section}" if p.section else "") for p in req.plan
        )
        body.append(f"แผนเทอม {req.term or '-'} มี {len(req.plan)} วิชา ({courses}) "
                    f"รวม {total_credits if total_credits is not None else '-'} หน่วยกิต")

    if credit_check["status"] == "ok":
        body.append(f"หน่วยกิตอยู่ในเกณฑ์ {credit_check['min']}–{credit_check['max']} หน่วยกิต")
    elif credit_check["status"] in {"over", "under"}:
        body.append(f"⚠️ หน่วยกิต {credit_check['note']}")

    if errors:
        body.append("\n**ปัญหาที่ต้องแก้ก่อนถึงจะลงได้**")
        body.extend(_line_for(c) for c in errors)
    if non_errors:
        body.append("\n**ข้อควรระวัง (ลงได้แต่ควรรู้ไว้)**")
        body.extend(_line_for(c) for c in non_errors)
    if verdict == "ok" and not non_errors:
        body.append("ไม่มีเวลาเรียนหรือเวลาสอบทับกัน และผ่านเงื่อนไขวิชาบังคับก่อนครบ")

    # ── ขั้นตอนถัดไป ────────────────────────────────────────────
    next_steps: list[str] = []
    for c in errors[:3]:
        action = CODE_ACTION.get(c.code)
        if action:
            subj = f" ({', '.join(c.subjects)})" if c.subjects else ""
            next_steps.append(f"{action}{subj}")
    if credit_check["status"] == "under":
        next_steps.append(f"เพิ่มวิชาอีกอย่างน้อย {credit_check['min'] - (total_credits or 0)} หน่วยกิต")
    elif credit_check["status"] == "over":
        next_steps.append(f"ถอดวิชาออก {(total_credits or 0) - credit_check['max']} หน่วยกิต")
    if verdict == "ok":
        next_steps.append("ตรวจสอบที่นั่งคงเหลืออีกครั้งในวันลงทะเบียนจริง")

    codes = {c.code for c in errors} | {c.code for c in non_errors}
    return ExplainPlanResponse(
        verdict=verdict,
        headline=headline,
        explanation="\n".join(body).strip(),
        next_steps=next_steps,
        credit_check=credit_check,
        sources=_regulation_sources(codes),
        provider="rule_based",
        disclaimer=DISCLAIMER,
    )
