"""จัดตารางเรียนอัตโนมัติแบบ greedy

ต่างจากโมดูล 06 ที่ใช้ CP-SAT (ortools): ตัวนั้นหาคำตอบที่ดีที่สุดเชิงคณิตศาสตร์
แต่ ortools ~180 MB เกินโควตาฟังก์ชันของ Vercel จึงใช้ greedy ที่ให้ผลใกล้เคียง
สำหรับข้อมูลขนาดนี้ (หนึ่งเทอมมีไม่เกิน ~70 หมู่เรียน)

ลำดับที่ใช้เลือก
  1. วิชาที่ค้างจากเทอมก่อน (เคยได้ F/W) มาก่อนเสมอ
  2. วิชาตามแผนของชั้นปีนั้น
  3. วิชาบังคับอื่นตาม priority_score
  4. วิชาเลือก
ภายในวิชาเดียวกัน เลือกหมู่ที่ตรงเงื่อนไขผู้ใช้มากที่สุดและยังมีที่นั่ง
"""
from __future__ import annotations

from .conflicts import (
    DAY_TH,
    DEFAULT_MAX_CREDITS,
    DEFAULT_MIN_CREDITS,
    SUMMER_MAX_CREDITS,
    detect_conflicts,
    section_mask,
)

DAY_INDEX = {name: i for i, name in enumerate(DAY_TH)}
DAY_INDEX.update({"MON": 0, "TUE": 1, "WED": 2, "THU": 3, "FRI": 4, "SAT": 5, "SUN": 6})


def exams_clash(a: dict, b: dict) -> bool:
    """สองหมู่เรียนนี้มีเวลาสอบทับกันไหม (ประเภทเดียวกัน วันเดียวกัน ช่วงซ้อนกัน)"""
    for ea in a.get("exams", []):
        for eb in b.get("exams", []):
            if ea.get("exam_type") != eb.get("exam_type"):
                continue
            if ea.get("exam_date") != eb.get("exam_date"):
                continue
            if ea["start_min"] < eb["end_min"] and eb["start_min"] < ea["end_min"]:
                return True
    return False


def _clamp_credits(value, fallback: int, lo: int, hi: int) -> int:
    """แปลงค่าหน่วยกิตจากผู้ใช้ให้เป็นจำนวนเต็มในกรอบที่ระเบียบอนุญาต

    ค่าที่แปลงไม่ได้ (ส่ง string หรือ null มา) ให้ใช้ค่าตั้งต้น ไม่ใช่โยน error
    เพราะเป็นแค่ความชอบส่วนตัว ไม่ควรทำให้จัดตารางไม่ได้ทั้งแผน
    """
    try:
        n = int(value)
    except (TypeError, ValueError):
        return fallback
    return max(lo, min(hi, n))


def _section_score(sec: dict, prefs: dict, used_days: set[int]) -> float:
    """คะแนนความเหมาะสมของหมู่เรียน ยิ่งสูงยิ่งดี"""
    score = 0.0
    days = {m["day"] for m in sec.get("meetings", []) if 0 <= m.get("day", -1) < 7}

    # ที่นั่งเหลือเยอะ = เสี่ยงน้อยกว่า
    total, taken = sec.get("seat_total"), sec.get("seat_taken")
    if total:
        score += 2.0 * ((total - (taken or 0)) / total)

    # ไม่เอาคาบเช้า
    if prefs.get("avoid_morning"):
        earliest = min((m["start_min"] for m in sec.get("meetings", [])), default=9 * 60)
        if earliest < 9 * 60:
            score -= 4.0

    # วันที่ขอว่าง
    raw_free = prefs.get("free_days")
    free = {DAY_INDEX[d] for d in (raw_free if isinstance(raw_free, list) else []) if d in DAY_INDEX}
    if free & days:
        score -= 8.0

    # รวมวันให้กระจุก จะได้มีวันว่างเต็มวัน
    if days & used_days:
        score += 1.5

    # อาจารย์ที่ชอบ
    liked = set(prefs.get("preferred_teachers", []))
    if liked & set(sec.get("teachers", [])):
        score += 3.0

    return score


def generate_plan(
    all_sections: list[dict],
    *,
    term: str = "1/2569",
    passed_courses: list[str] | None = None,
    retake_courses: list[str] | None = None,
    student_year: int | None = None,
    preferences: dict | None = None,
    locked_section_ids: list[str] | None = None,
) -> dict:
    """จัดตารางให้ 1 แผน คืนแผน + ผลตรวจ + เหตุผลที่ไม่ได้ลงบางวิชา"""
    prefs = preferences or {}
    passed = set(passed_courses or [])
    retake = list(retake_courses or [])
    locked = set(locked_section_ids or [])

    is_summer = term.startswith("3/")
    ceiling = SUMMER_MAX_CREDITS if is_summer else DEFAULT_MAX_CREDITS
    floor = 0 if is_summer else DEFAULT_MIN_CREDITS
    # ค่าจากผู้ใช้เชื่อตรง ๆ ไม่ได้: ถ้าส่ง max_credits=99 มา ระบบจะจัดแผนเกินเพดานระเบียบให้
    # ซึ่งค้านกับสิ่งที่แอปรับปากไว้ทั้งหมด จึงบังคับให้อยู่ในกรอบเสมอ
    lo = _clamp_credits(prefs.get("min_credits"), floor, 0, ceiling)
    hi = _clamp_credits(prefs.get("max_credits"), ceiling, 1, ceiling)
    if lo > hi:
        lo = hi

    by_course: dict[str, list[dict]] = {}
    for s in all_sections:
        by_course.setdefault(s["course_code"], []).append(s)

    def course_rank(code: str) -> tuple:
        secs = by_course[code]
        year = secs[0].get("suggested_year")
        priority = max(s.get("priority_score", 0) for s in secs)
        return (
            0 if code in retake else 1,                       # วิชาค้างมาก่อน
            0 if (student_year and year == student_year) else 1,  # ตามชั้นปี
            -priority,
            code,
        )

    chosen: list[dict] = []
    skipped: list[dict] = []
    used_mask = 0
    used_days: set[int] = set()
    credits = 0

    # วิชาที่ผู้ใช้ล็อกไว้เอง ต้องอยู่ในแผนเสมอ
    for sid in locked:
        sec = next((s for s in all_sections if s["id"] == sid), None)
        if not sec or (used_mask & section_mask(sec)):
            continue
        if not any(exams_clash(sec, c) for c in chosen):
            chosen.append(sec)
            used_mask |= section_mask(sec)
            used_days |= {m["day"] for m in sec.get("meetings", [])}
            credits += int(sec.get("credits", 0))

    for code in sorted(by_course, key=course_rank):
        if any(s["course_code"] == code for s in chosen):
            continue
        if code in passed and code not in retake:
            continue
        cost = int(by_course[code][0].get("credits", 0))
        if credits + cost > hi:
            skipped.append({"course_code": code, "reason": f"ลงแล้วจะเกิน {hi} หน่วยกิต"})
            continue

        # วิชาบังคับก่อนยังไม่ผ่าน -> ข้าม
        missing = [p for p in by_course[code][0].get("prerequisites", []) if p not in passed]
        if missing:
            skipped.append({"course_code": code,
                            "reason": f"ยังไม่ผ่านวิชาบังคับก่อน {', '.join(missing)}"})
            continue

        options = [s for s in by_course[code]
                   if not (used_mask & section_mask(s))
                   and not (s.get("seat_total") is not None
                            and s.get("seat_taken", 0) >= s["seat_total"])
                   # ต้องเช็คเวลาสอบด้วย ไม่ใช่แค่เวลาเรียน ไม่งั้นจะจัดแผนที่
                   # ตัวเองตรวจแล้วไม่ผ่าน (ติด C2) ส่งกลับไปให้ผู้ใช้
                   and not any(exams_clash(s, picked) for picked in chosen)]
        if not options:
            skipped.append({"course_code": code,
                            "reason": "ทุกหมู่ชนกับวิชาที่เลือกไว้ (เวลาเรียนหรือเวลาสอบ) หรือที่นั่งเต็ม"})
            continue

        best = max(options, key=lambda s: _section_score(s, prefs, used_days))
        chosen.append(best)
        used_mask |= section_mask(best)
        used_days |= {m["day"] for m in best.get("meetings", [])}
        credits += cost

        if credits >= hi:
            break

    result = detect_conflicts(
        chosen, passed_courses=list(passed), term=term,
        min_credits=lo, max_credits=hi, all_sections=all_sections,
    )
    result["plan"] = chosen
    result["skipped"] = skipped
    result["reached_minimum"] = credits >= lo
    return result
