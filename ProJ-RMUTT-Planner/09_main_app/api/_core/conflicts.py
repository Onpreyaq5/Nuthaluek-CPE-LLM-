"""ตรวจตารางชน — พอร์ตมาจาก 06_schedule_conflict_engine ให้รันบน Vercel ได้

ทำไมต้องพอร์ต: โมดูล 06 ใช้ ortools (~180 MB) สำหรับ CP-SAT ซึ่งเกินโควตา
ขนาดฟังก์ชันของ Vercel (250 MB) แต่ "ส่วนตรวจการชน" เป็นตรรกะล้วน ไม่ต้องใช้ ortools
จึงยกมาเฉพาะส่วนนั้น ให้เว็บใช้งานได้จริงโดยไม่ต้องรัน container

รหัสปัญหาและข้อความตรงกับ 06 ทุกตัว (C1-C6, W1-W5) เพื่อให้สลับไปเรียก 06 ตัวจริง
ผ่าน HTTP ได้ทันทีโดยไม่ต้องแก้ฝั่งหน้าเว็บ
"""
from __future__ import annotations

from typing import Any

# ── กริดเวลา 182 บิต: 7 วัน x 26 ช่อง (30 นาที) 08:00–21:00 ──────────────
SLOT_MINUTES = 30
DAY_START_MIN = 8 * 60      # 480
DAY_END_MIN = 21 * 60       # 1260
SLOTS_PER_DAY = (DAY_END_MIN - DAY_START_MIN) // SLOT_MINUTES   # 26
TOTAL_DAYS = 7
TOTAL_BITS = TOTAL_DAYS * SLOTS_PER_DAY                          # 182

DAY_TH = ["จันทร์", "อังคาร", "พุธ", "พฤหัสบดี", "ศุกร์", "เสาร์", "อาทิตย์"]
DAY_EN = ["MON", "TUE", "WED", "THU", "FRI", "SAT", "SUN"]

DEFAULT_MIN_CREDITS = 9
DEFAULT_MAX_CREDITS = 21
SUMMER_MAX_CREDITS = 9


def hhmm(minutes: int) -> str:
    return f"{minutes // 60:02d}:{minutes % 60:02d}"


def time_range_to_bitmask(day: int, start_min: int, end_min: int) -> int:
    """แปลงช่วงเวลาของวันหนึ่งเป็น bitmask"""
    if day < 0 or day >= TOTAL_DAYS:
        return 0
    s = max(start_min, DAY_START_MIN)
    e = min(end_min, DAY_END_MIN)
    if s >= e:
        return 0
    start_slot = (s - DAY_START_MIN) // SLOT_MINUTES
    end_slot = min((e - DAY_START_MIN + SLOT_MINUTES - 1) // SLOT_MINUTES, SLOTS_PER_DAY)
    offset = day * SLOTS_PER_DAY
    mask = 0
    for slot in range(start_slot, end_slot):
        mask |= 1 << (offset + slot)
    return mask


def meetings_to_bitmask(meetings: list[dict]) -> int:
    mask = 0
    for m in meetings or []:
        mask |= time_range_to_bitmask(m.get("day", -1), m.get("start_min", 0), m.get("end_min", 0))
    return mask


def section_mask(section: dict) -> int:
    """ใช้ slots_mask ที่มากับข้อมูล ถ้าไม่มีค่อยคำนวณจาก meetings"""
    if section.get("is_online"):
        return 0
    if section.get("slots_mask") is not None:
        return int(section["slots_mask"])
    return meetings_to_bitmask(section.get("meetings", []))


def overlap_window(a: dict, b: dict) -> tuple[int, int, int] | None:
    """หาช่วงเวลาที่ทับกันจริง คืน (day, start_min, end_min) เพื่อบอกผู้ใช้ให้ชัด"""
    for ma in a.get("meetings", []):
        for mb in b.get("meetings", []):
            if ma.get("day") != mb.get("day"):
                continue
            start = max(ma["start_min"], mb["start_min"])
            end = min(ma["end_min"], mb["end_min"])
            if start < end:
                return ma["day"], start, end
    return None


def _conflict(code, key, th, subjects=None, detail=None, severity="ERROR", suggestions=None):
    return {
        "code": code, "severity": severity, "message_key": key, "message_th": th,
        "subjects": subjects or [], "detail": detail or {}, "suggestions": suggestions or [],
    }


def detect_conflicts(
    sections: list[dict],
    passed_courses: list[str] | None = None,
    term: str = "",
    min_credits: int | None = None,
    max_credits: int | None = None,
    all_sections: list[dict] | None = None,
) -> dict:
    """ตรวจ C1-C6 และ W1-W5 — ตรรกะและข้อความตรงกับโมดูล 06"""
    passed = set(passed_courses or [])
    is_summer = term.startswith("3/")
    lo = min_credits if min_credits is not None else (0 if is_summer else DEFAULT_MIN_CREDITS)
    hi = max_credits if max_credits is not None else (SUMMER_MAX_CREDITS if is_summer else DEFAULT_MAX_CREDITS)

    conflicts: list[dict] = []
    warnings: list[dict] = []

    # ── C1 เวลาเรียนทับกัน ──────────────────────────────────────
    for i, a in enumerate(sections):
        for b in sections[i + 1:]:
            if section_mask(a) & section_mask(b):
                win = overlap_window(a, b)
                detail: dict[str, Any] = {}
                if win:
                    d, st, en = win
                    detail = {"day": d, "day_th": DAY_TH[d], "overlap_start": st, "overlap_end": en}
                    when = f"วัน{DAY_TH[d]} เวลา {hhmm(st)}-{hhmm(en)}"
                else:
                    when = ""
                conflicts.append(_conflict(
                    "C1", "time_clash",
                    f"เวลาเรียนวิชา {a['id']} ชนกับ {b['id']} {when}".strip(),
                    [a["id"], b["id"]], detail,
                    suggestions=_alt_sections(a, b, sections, all_sections),
                ))

    # ── C2 เวลาสอบทับกัน ────────────────────────────────────────
    for i, a in enumerate(sections):
        for b in sections[i + 1:]:
            for ea in a.get("exams", []):
                for eb in b.get("exams", []):
                    if ea.get("exam_type") != eb.get("exam_type"):
                        continue
                    if ea.get("exam_date") != eb.get("exam_date"):
                        continue
                    if ea["start_min"] < eb["end_min"] and eb["start_min"] < ea["end_min"]:
                        kind = "กลางภาค" if ea["exam_type"] == "midterm" else "ปลายภาค"
                        conflicts.append(_conflict(
                            "C2", "exam_clash",
                            f"สอบ{kind}ของ {a['course_code']} ชนกับ {b['course_code']} "
                            f"วันที่ {ea['exam_date']} เวลา {hhmm(ea['start_min'])}-{hhmm(ea['end_min'])}",
                            [a["id"], b["id"]],
                            {"exam_type": ea["exam_type"], "exam_date": ea["exam_date"],
                             "start_min": ea["start_min"], "end_min": ea["end_min"]},
                        ))

    # ── C3 วิชาบังคับก่อน ───────────────────────────────────────
    for sec in sections:
        missing = [p for p in sec.get("prerequisites", []) if p not in passed]
        if missing:
            conflicts.append(_conflict(
                "C3", "prereq_fail",
                f"ยังไม่ผ่านวิชาบังคับก่อน ({', '.join(missing)}) ของวิชา {sec['course_code']}",
                [sec["id"]], {"missing": missing},
            ))

    # ── C4 หน่วยกิต ─────────────────────────────────────────────
    total_credits = sum(int(s.get("credits", 0)) for s in sections)
    if total_credits > hi:
        conflicts.append(_conflict(
            "C4", "credit_limit_exceeded",
            f"หน่วยกิตรวม ({total_credits}) เกินเพดานสูงสุดที่กำหนด ({hi} หน่วยกิต)",
            [], {"total_credits": total_credits, "max": hi},
        ))
    elif sections and total_credits < lo:
        conflicts.append(_conflict(
            "C4", "credit_limit_under",
            f"หน่วยกิตรวม ({total_credits}) ต่ำกว่าเกณฑ์ขั้นต่ำของมหาวิทยาลัย ({lo} หน่วยกิต)",
            [], {"total_credits": total_credits, "min": lo},
        ))

    # ── C5 ลงซ้ำ / เคยผ่านแล้ว ──────────────────────────────────
    by_course: dict[str, list[str]] = {}
    for sec in sections:
        by_course.setdefault(sec["course_code"], []).append(sec["id"])
    for code, ids in by_course.items():
        if len(ids) > 1:
            conflicts.append(_conflict(
                "C5", "duplicate_section",
                f"ลงทะเบียนวิชาเดียวกันซ้ำกันมากกว่าหนึ่งกลุ่ม: {code} ({', '.join(ids)})",
                ids, {"course_code": code},
            ))
        if code in passed:
            conflicts.append(_conflict(
                "C5", "already_passed",
                f"เคยสอบผ่านรายวิชา {code} แล้ว ไม่สามารถลงทะเบียนซ้ำได้",
                ids, {"course_code": code},
            ))

    # ── C6 ที่นั่งเต็ม ──────────────────────────────────────────
    for sec in sections:
        total, taken = sec.get("seat_total"), sec.get("seat_taken")
        if total is not None and taken is not None and taken >= total:
            conflicts.append(_conflict(
                "C6", "seat_full",
                f"ที่นั่งในกลุ่ม {sec['id']} เต็มแล้ว ({taken}/{total} ที่นั่ง)",
                [sec["id"]], {"seat_total": total, "seat_taken": taken, "seat_left": 0},
                suggestions=_alt_sections(sec, None, sections, all_sections),
            ))

    warnings.extend(_quality_warnings(sections))

    return {
        "has_conflict": any(c["severity"] == "ERROR" for c in conflicts),
        "conflicts": conflicts,
        "warnings": warnings,
        "summary": _summary(sections, total_credits, lo, hi),
    }


def _alt_sections(a: dict, b: dict | None, chosen: list[dict], pool: list[dict] | None) -> list[dict]:
    """หาหมู่เรียนอื่นของวิชาเดียวกันที่ไม่ชนกับตัวที่เลือกไว้ — ช่วยให้ผู้ใช้แก้ได้ทันที"""
    if not pool:
        return []
    out: list[dict] = []
    for target in filter(None, [a, b]):
        others = [s for s in pool
                  if s["course_code"] == target["course_code"] and s["id"] != target["id"]]
        keep_mask = 0
        for s in chosen:
            if s["course_code"] != target["course_code"]:
                keep_mask |= section_mask(s)
        for alt in others:
            if section_mask(alt) & keep_mask:
                continue
            if alt.get("seat_total") is not None and alt.get("seat_taken", 0) >= alt["seat_total"]:
                continue
            out.append({"action": "change_section", "from": target["id"], "to": alt["id"],
                        "when": _when_text(alt)})
            break
    return out


def _when_text(sec: dict) -> str:
    parts = [f"{DAY_TH[m['day']]} {hhmm(m['start_min'])}-{hhmm(m['end_min'])}"
             for m in sec.get("meetings", []) if 0 <= m.get("day", -1) < 7]
    return " / ".join(parts)


def _quality_warnings(sections: list[dict]) -> list[dict]:
    """W1-W5 คำเตือนคุณภาพชีวิต (ลงได้แต่ควรรู้)"""
    warnings: list[dict] = []
    by_day: dict[int, list[tuple[int, int, str]]] = {}
    for s in sections:
        for m in s.get("meetings", []):
            d = m.get("day")
            if d is None or not (0 <= d < 7):
                continue
            by_day.setdefault(d, []).append((m["start_min"], m["end_min"], s["id"]))

    for day, slots in sorted(by_day.items()):
        slots.sort()
        span = slots[-1][1] - slots[0][0]
        if span >= 6 * 60:
            warnings.append(_conflict(
                "W1", "long_stretch",
                f"วัน{DAY_TH[day]}อยู่มหาวิทยาลัยยาว {span // 60} ชั่วโมง "
                f"({hhmm(slots[0][0])}-{hhmm(slots[-1][1])})",
                [s[2] for s in slots], {"day": day, "span_minutes": span}, "WARNING",
            ))
        for (s1, e1, id1), (s2, e2, id2) in zip(slots, slots[1:]):
            gap = s2 - e1
            if gap >= 4 * 60:
                warnings.append(_conflict(
                    "W2", "large_gap",
                    f"วัน{DAY_TH[day]}มีช่องว่าง {gap // 60} ชั่วโมง ระหว่าง {hhmm(e1)} ถึง {hhmm(s2)}",
                    [id1, id2], {"day": day, "gap_minutes": gap}, "WARNING",
                ))
        if slots[0][0] < 9 * 60:
            warnings.append(_conflict(
                "W3", "early_class",
                f"วัน{DAY_TH[day]}มีคาบเรียนตั้งแต่ {hhmm(slots[0][0])}",
                [slots[0][2]], {"day": day, "start_min": slots[0][0]}, "WARNING",
            ))

    days_on_campus = len(by_day)
    if days_on_campus >= 6:
        warnings.append(_conflict(
            "W5", "heavy_days",
            f"ต้องมามหาวิทยาลัย {days_on_campus} วันต่อสัปดาห์",
            [], {"days": days_on_campus}, "WARNING",
        ))
    return warnings


def _summary(sections: list[dict], total_credits: int, lo: int, hi: int) -> dict:
    days = sorted({m["day"] for s in sections for m in s.get("meetings", [])
                   if 0 <= m.get("day", -1) < 7})
    return {
        "total_courses": len({s["course_code"] for s in sections}),
        "total_sections": len(sections),
        "total_credits": total_credits,
        "min_credits": lo,
        "max_credits": hi,
        "credit_status": "over" if total_credits > hi else ("under" if total_credits < lo else "ok"),
        "days_on_campus": len(days),
        "free_days": [DAY_TH[d] for d in range(7) if d not in days],
    }
