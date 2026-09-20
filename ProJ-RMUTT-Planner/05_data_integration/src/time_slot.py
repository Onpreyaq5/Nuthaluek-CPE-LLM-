"""Time Slot Model & Bitmask Collision Engine
- แปลงวัน-เวลาเรียนเป็น 182-bit mask (7 วัน x 26 ช่อง 30 นาที: 08:00 - 21:00)
- เช็คเวลาชน O(1) ด้วย bitwise AND
- ถอดรหัส bitmask กลับเป็นช่วงเวลาที่ทับซ้อนจริง (overlap intervals)
"""
from __future__ import annotations

import re
from dataclasses import dataclass

# ค่าคงที่ตาม 01_env.txt
SLOT_MINUTES = 30
DAY_START_HOUR = 8
DAY_START_MIN = DAY_START_HOUR * 60      # 480 นาที
DAY_END_HOUR = 21
DAY_END_MIN = DAY_END_HOUR * 60          # 1260 นาที
SLOTS_PER_DAY = (DAY_END_MIN - DAY_START_MIN) // SLOT_MINUTES  # 26 ช่อง
TOTAL_DAYS = 7
TOTAL_BITS = TOTAL_DAYS * SLOTS_PER_DAY  # 182 บิต

DAY_NAMES = ["MON", "TUE", "WED", "THU", "FRI", "SAT", "SUN"]
DAY_NAMES_TH = ["จันทร์", "อังคาร", "พุธ", "พฤหัสบดี", "ศุกร์", "เสาร์", "อาทิตย์"]

THAI_DAY_MAP = {
    "จ": 0, "จ.": 0, "จันทร์": 0, "mon": 0, "monday": 0,
    "อ": 1, "อ.": 1, "อังคาร": 1, "tue": 1, "tuesday": 1,
    "พ": 2, "พ.": 2, "พุธ": 2, "wed": 2, "wednesday": 2,
    "พฤ": 3, "พฤ.": 3, "พฤหัส": 3, "พฤหัสบดี": 3, "thu": 3, "thursday": 3,
    "ศ": 4, "ศ.": 4, "ศุกร์": 4, "fri": 4, "friday": 4,
    "ส": 5, "ส.": 5, "เสาร์": 5, "sat": 5, "saturday": 5,
    "อา": 6, "อา.": 6, "อาทิตย์": 6, "sun": 6, "sunday": 6,
}


@dataclass
class TimeSlot:
    day: int          # 0=MON .. 6=SUN
    start_min: int    # นาทีจากเที่ยงคืน เช่น 540 = 09:00
    end_min: int      # นาทีจากเที่ยงคืน เช่น 720 = 12:00

    @property
    def day_name(self) -> str:
        return DAY_NAMES[self.day] if 0 <= self.day < 7 else "UNKNOWN"

    @property
    def day_name_th(self) -> str:
        return DAY_NAMES_TH[self.day] if 0 <= self.day < 7 else "ไม่ทราบวัน"

    @property
    def start_time_str(self) -> str:
        return f"{self.start_min // 60:02d}:{self.start_min % 60:02d}"

    @property
    def end_time_str(self) -> str:
        return f"{self.end_min // 60:02d}:{self.end_min % 60:02d}"

    def to_bitmask(self) -> int:
        return time_range_to_bitmask(self.day, self.start_min, self.end_min)


def parse_time_str_to_minutes(t_str: str) -> int:
    """แปลง '09:00' -> 540 หรือ '9.00' -> 540"""
    m = re.match(r"(\d{1,2})[:.](\d{2})", t_str.strip())
    if not m:
        raise ValueError(f"รูปแบบเวลาไม่ถูกต้อง: {t_str}")
    h, m_val = int(m.group(1)), int(m.group(2))
    return h * 60 + m_val


def parse_day_str(day_str: str) -> int:
    """แปลง 'จ.', 'พฤ.', 'MON' -> 0..6"""
    clean_d = day_str.strip().lower()
    if clean_d in THAI_DAY_MAP:
        return THAI_DAY_MAP[clean_d]
    raise ValueError(f"ไม่พบชื่อวัน: {day_str}")


def parse_schedule_string(text: str) -> list[TimeSlot]:
    """แปลงข้อความ เช่น 'จ. 09:00-12:00' หรือ 'พฤ. 13:00 - 16:00, ศ. 09:00-12:00' -> list[TimeSlot]"""
    slots = []
    # แยกส่วนตาม comma หรือ newline หรือ semicolon
    parts = re.split(r"[,;\n]+", text.strip())
    pattern = re.compile(
        r"([ก-๙a-zA-Z.]+)\s*(\d{1,2}[:.]\d{2})\s*[-–~]\s*(\d{1,2}[:.]\d{2})"
    )
    for part in parts:
        part = part.strip()
        if not part:
            continue
        m = pattern.search(part)
        if m:
            day_text, start_s, end_s = m.group(1), m.group(2), m.group(3)
            try:
                day_val = parse_day_str(day_text)
                start_m = parse_time_str_to_minutes(start_s)
                end_m = parse_time_str_to_minutes(end_s)
                slots.append(TimeSlot(day=day_val, start_min=start_m, end_min=end_m))
            except ValueError:
                continue
    return slots


def time_range_to_bitmask(day: int, start_min: int, end_min: int) -> int:
    """แปลงช่วงเวลาของวันหนึ่งให้เป็น bitmask ในระบบ 182-bit
    - วัน: 0..6
    - ช่วงเวลา: ตัดให้อยู่ระหว่าง DAY_START_MIN (08:00) ถึง DAY_END_MIN (21:00)
    """
    if day < 0 or day >= TOTAL_DAYS:
        return 0

    # ปรับเวลาให้อยู่ในกรอบ 08:00 - 21:00
    s = max(start_min, DAY_START_MIN)
    e = min(end_min, DAY_END_MIN)
    if s >= e:
        return 0

    start_slot = (s - DAY_START_MIN) // SLOT_MINUTES
    # ถ้า end_min ไม่ลงตัวกับ 30 นาที ให้ปัดขึ้นเพื่อให้ครอบคลุม
    end_slot = (e - DAY_START_MIN + SLOT_MINUTES - 1) // SLOT_MINUTES
    end_slot = min(end_slot, SLOTS_PER_DAY)

    day_offset = day * SLOTS_PER_DAY
    mask = 0
    for slot in range(start_slot, end_slot):
        bit_pos = day_offset + slot
        mask |= (1 << bit_pos)

    return mask


def meetings_to_bitmask(meetings: list[dict | TimeSlot]) -> int:
    """รวม bitmask จากหลาย meeting (เช่น มีทั้งบรรยายและปฏิบัติ)"""
    total_mask = 0
    for m in meetings:
        if isinstance(m, TimeSlot):
            total_mask |= m.to_bitmask()
        elif isinstance(m, dict):
            # ตรวจสอบรูปแบบ dict: {day: 0, start_min: 540, end_min: 720}
            day = m.get("day", m.get("day_of_week"))
            start_min = m.get("start_min")
            end_min = m.get("end_min")

            if day is None or start_min is None or end_min is None:
                # ลองดูว่ามี raw string หรือไม่
                raw_time = m.get("time_str") or m.get("schedule")
                if raw_time:
                    for ts in parse_schedule_string(str(raw_time)):
                        total_mask |= ts.to_bitmask()
                    continue

            if isinstance(day, str):
                try:
                    day = parse_day_str(day)
                except ValueError:
                    continue

            if isinstance(start_min, str):
                start_min = parse_time_str_to_minutes(start_min)
            if isinstance(end_min, str):
                end_min = parse_time_str_to_minutes(end_min)

            if day is not None and start_min is not None and end_min is not None:
                total_mask |= time_range_to_bitmask(day, start_min, end_min)
    return total_mask


def check_clash(mask_a: int, mask_b: int) -> bool:
    """ตรวจสอบว่าตารางเวลาชนกันหรือไม่ O(1)"""
    return (mask_a & mask_b) != 0


def decode_overlap(mask_a: int, mask_b: int) -> list[dict]:
    """ถอดรหัส bitmask ที่ทับซ้อนกันกลับมาเป็นช่วงเวลา
    คืนค่า list ของ dict:
    [
        {
            "day": "MON",
            "day_th": "จันทร์",
            "overlap_start": "09:00",
            "overlap_end": "10:30",
            "start_min": 540,
            "end_min": 630
        }
    ]
    """
    overlap_mask = mask_a & mask_b
    if overlap_mask == 0:
        return []

    results: list[dict] = []
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


def bitmask_to_binary_string(mask: int) -> str:
    """แปลง bitmask เป็น binary string ความยาว 182 ตัวอักษร (จาก bit 0 ถึง bit 181)"""
    return "".join("1" if (mask & (1 << i)) else "0" for i in range(TOTAL_BITS))


def binary_string_to_bitmask(b_str: str) -> int:
    """แปลง binary string กลับเป็น bitmask int"""
    mask = 0
    for i, ch in enumerate(b_str):
        if ch == "1":
            mask |= (1 << i)
    return mask
