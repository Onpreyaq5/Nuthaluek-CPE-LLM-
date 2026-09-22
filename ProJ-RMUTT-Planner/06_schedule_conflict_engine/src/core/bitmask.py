"""06_schedule_conflict_engine - 182-Bitmask Collision Logic
7 วัน x 26 ช่อง 30 นาที (08:00 - 21:00) = 182 บิต
คำนวณการชนกันของเวลาเรียนในระดับ O(1) ด้วย bitwise AND
"""
from __future__ import annotations

from typing import Any
from ..models.schemas import Meeting

SLOT_MINUTES = 30
DAY_START_HOUR = 8
DAY_START_MIN = DAY_START_HOUR * 60       # 480 นาที
DAY_END_HOUR = 21
DAY_END_MIN = DAY_END_HOUR * 60           # 1260 นาที
SLOTS_PER_DAY = (DAY_END_MIN - DAY_START_MIN) // SLOT_MINUTES  # 26 ช่องต่อวัน
TOTAL_DAYS = 7
TOTAL_BITS = TOTAL_DAYS * SLOTS_PER_DAY   # 182 บิต

DAY_NAMES = ["MON", "TUE", "WED", "THU", "FRI", "SAT", "SUN"]
DAY_NAMES_TH = ["จันทร์", "อังคาร", "พุธ", "พฤหัสบดี", "ศุกร์", "เสาร์", "อาทิตย์"]


def ensure_section_mask(section: Any) -> int:
    """คำนวณและตรวจสอบว่า section มี slots_mask หรือไม่ ถ้าไม่มีให้คำนวณจาก meetings"""
    if getattr(section, "slots_mask", None) is not None:
        return section.slots_mask
    if getattr(section, "is_online", False):
        section.slots_mask = 0
        return 0
    meetings = getattr(section, "meetings", [])
    mask = meetings_to_bitmask(meetings)
    section.slots_mask = mask
    return mask


def time_range_to_bitmask(day: int, start_min: int, end_min: int) -> int:
    """แปลงช่วงเวลาของวันหนึ่งให้เป็น bitmask ในระบบ 182-bit
    - day: 0 (MON) .. 6 (SUN)
    - start_min, end_min: นาทีจากเที่ยงคืน (เช่น 540=09:00, 720=12:00)
    """
    if day < 0 or day >= TOTAL_DAYS:
        return 0

    s = max(start_min, DAY_START_MIN)
    e = min(end_min, DAY_END_MIN)
    if s >= e:
        return 0

    start_slot = (s - DAY_START_MIN) // SLOT_MINUTES
    # กรณี e อยู่บนขอบเขตพอดี เช่น 11:00 (660) (660-480+29)//30 = 6
    end_slot = (e - DAY_START_MIN + SLOT_MINUTES - 1) // SLOT_MINUTES
    end_slot = min(end_slot, SLOTS_PER_DAY)

    day_offset = day * SLOTS_PER_DAY
    mask = 0
    for slot in range(start_slot, end_slot):
        mask |= (1 << (day_offset + slot))

    return mask


def meetings_to_bitmask(meetings: list[Meeting | dict[str, Any]]) -> int:
    """รวม bitmask จากทุก meeting ใน section"""
    total_mask = 0
    for m in meetings:
        if isinstance(m, Meeting):
            total_mask |= time_range_to_bitmask(m.day, m.start_min, m.end_min)
        elif isinstance(m, dict):
            day = m.get("day", m.get("day_of_week"))
            s = m.get("start_min")
            e = m.get("end_min")
            if day is not None and s is not None and e is not None:
                total_mask |= time_range_to_bitmask(int(day), int(s), int(e))
    return total_mask


def check_clash(mask_a: int, mask_b: int) -> bool:
    """ตรวจสอบว่าเวลาชนกันหรือไม่ O(1)"""
    return (mask_a & mask_b) != 0


def decode_overlap(mask_a: int, mask_b: int) -> list[dict[str, Any]]:
    """ถอดรหัสบิตที่ซ้อนทับกันเป็นช่วงเวลาจริง (วัน/เวลาเริ่มต้น-สิ้นสุด)"""
    overlap_mask = mask_a & mask_b
    if overlap_mask == 0:
        return []

    results: list[dict[str, Any]] = []
    for day in range(TOTAL_DAYS):
        day_offset = day * SLOTS_PER_DAY
        in_overlap = False
        start_slot = 0

        for slot in range(SLOTS_PER_DAY):
            bit_pos = day_offset + slot
            is_set = bool(overlap_mask & (1 << bit_pos))

            if is_set and not in_overlap:
                in_overlap = True
                start_slot = slot
            elif not is_set and in_overlap:
                in_overlap = False
                end_slot = slot
                s_min = DAY_START_MIN + start_slot * SLOT_MINUTES
                e_min = DAY_START_MIN + end_slot * SLOT_MINUTES
                results.append({
                    "day": DAY_NAMES[day],
                    "day_th": DAY_NAMES_TH[day],
                    "overlap_start": f"{s_min // 60:02d}:{s_min % 60:02d}",
                    "overlap_end": f"{e_min // 60:02d}:{e_min % 60:02d}",
                    "start_min": s_min,
                    "end_min": e_min,
                })

        if in_overlap:
            end_slot = SLOTS_PER_DAY
            s_min = DAY_START_MIN + start_slot * SLOT_MINUTES
            e_min = DAY_START_MIN + end_slot * SLOT_MINUTES
            results.append({
                "day": DAY_NAMES[day],
                "day_th": DAY_NAMES_TH[day],
                "overlap_start": f"{s_min // 60:02d}:{s_min % 60:02d}",
                "overlap_end": f"{e_min // 60:02d}:{e_min % 60:02d}",
                "start_min": s_min,
                "end_min": e_min,
            })

    return results


def get_schedule_profile(mask: int) -> dict[str, Any]:
    """วิเคราะห์ลักษณะของตารางเวลาจาก bitmask รวม:
    - active_days (วันที่มีเรียน)
    - free_days (วันที่ว่าง)
    - max_consecutive_hours (เรียนติดกันยาวสุดกี่ชั่วโมงในวันเดียว)
    - max_gap_hours (ช่องว่างยาวสุดระหว่างคาบในวันเดียว)
    - has_early_morning (มีคาบเช้า 08:00 - 09:00 หรือไม่)
    - days_on_campus (จำนวนวันที่ต้องมาเรียน)
    """
    active_days: list[str] = []
    free_days: list[str] = []
    day_details: dict[str, Any] = {}

    max_consecutive_slots_overall = 0
    max_gap_slots_overall = 0
    has_early_morning_overall = False

    for day in range(TOTAL_DAYS):
        day_offset = day * SLOTS_PER_DAY
        slots_set = [slot for slot in range(SLOTS_PER_DAY) if (mask & (1 << (day_offset + slot)))]

        day_name = DAY_NAMES[day]
        if not slots_set:
            free_days.append(day_name)
            continue

        active_days.append(day_name)

        # ตรวจสอบคาบเช้า (08:00 - 09:00 คือ slot 0 และ slot 1)
        if 0 in slots_set or 1 in slots_set:
            has_early_morning_overall = True

        # คำนวณช่วงเรียนติดกันยาวสุด
        cur_consecutive = 1
        max_consecutive = 1
        for i in range(1, len(slots_set)):
            if slots_set[i] == slots_set[i - 1] + 1:
                cur_consecutive += 1
                if cur_consecutive > max_consecutive:
                    max_consecutive = cur_consecutive
            else:
                cur_consecutive = 1
        max_consecutive_slots_overall = max(max_consecutive_slots_overall, max_consecutive)

        # คำนวณช่องว่างระหว่างคาบ (gaps)
        max_gap = 0
        for i in range(1, len(slots_set)):
            gap = slots_set[i] - slots_set[i - 1] - 1
            if gap > max_gap:
                max_gap = gap
        max_gap_slots_overall = max(max_gap_slots_overall, max_gap)

        day_details[day_name] = {
            "slots_count": len(slots_set),
            "earliest_slot": slots_set[0],
            "latest_slot": slots_set[-1],
            "max_consecutive_slots": max_consecutive,
            "max_gap_slots": max_gap,
        }

    return {
        "active_days": active_days,
        "free_days": free_days,
        "days_on_campus": len(active_days),
        "max_consecutive_hours": (max_consecutive_slots_overall * SLOT_MINUTES) / 60.0,
        "max_gap_hours": (max_gap_slots_overall * SLOT_MINUTES) / 60.0,
        "has_early_morning": has_early_morning_overall,
        "day_details": day_details,
    }
