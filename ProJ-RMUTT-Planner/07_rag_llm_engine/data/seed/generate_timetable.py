"""สร้างตารางสอนจำลอง สาขาวิศวกรรมคอมพิวเตอร์ (CPE) ภาคการศึกษา 1/2569

ข้อมูลชุดนี้ใช้เป็น **ต้นแบบ (prototype)** เท่านั้น ไม่ใช่ตารางสอนจริงของมหาวิทยาลัย
โครงสร้างผลลัพธ์ตรงกับ SectionInput ของโมดูล 06_schedule_conflict_engine
จึงส่งเข้า POST /conflicts/check และ /plans/auto ได้ทันที

รัน:  python generate_timetable.py
ผลลัพธ์: cpe_timetable_1_2569.json
"""
from __future__ import annotations

import json
from pathlib import Path

# ── ค่าคงที่ของกริดเวลา (ตรงกับ 05_data_integration และ 06) ──────────────
DAY_START_MIN = 8 * 60      # 08:00
SLOT_MINUTES = 30
SLOTS_PER_DAY = 26          # 08:00–21:00
TOTAL_SLOTS = 7 * SLOTS_PER_DAY   # 182 bit

MON, TUE, WED, THU, FRI, SAT, SUN = range(7)
DAY_TH = ["จันทร์", "อังคาร", "พุธ", "พฤหัสบดี", "ศุกร์", "เสาร์", "อาทิตย์"]


def hm(text: str) -> int:
    """'09:00' -> 540 (นาทีจากเที่ยงคืน)"""
    h, m = text.split(":")
    return int(h) * 60 + int(m)


def slots_mask(meetings: list[dict]) -> int:
    """แปลงคาบเรียนทั้งหมดเป็น bitmask 182 บิต — ใช้เช็คตารางชนด้วย AND"""
    mask = 0
    for mt in meetings:
        start_idx = (mt["start_min"] - DAY_START_MIN) // SLOT_MINUTES
        end_idx = (mt["end_min"] - DAY_START_MIN + SLOT_MINUTES - 1) // SLOT_MINUTES
        for s in range(max(start_idx, 0), min(end_idx, SLOTS_PER_DAY)):
            mask |= 1 << (mt["day"] * SLOTS_PER_DAY + s)
    return mask


def meeting(day: int, start: str, end: str, room: str, building: str, kind: str = "lecture") -> dict:
    return {
        "day": day,
        "start_min": hm(start),
        "end_min": hm(end),
        "room": room,
        "building": building,
        "meeting_type": kind,
    }


def exam(kind: str, date: str, start: str, end: str, room: str) -> dict:
    return {
        "exam_type": kind,
        "exam_date": date,
        "start_min": hm(start),
        "end_min": hm(end),
        "room": room,
    }


# ── นิยามรายวิชา: (รหัส, ชื่อ, หน่วยกิต, วิชาบังคับก่อน, หมวด) ──────────────
COURSES = {
    "04100201-66": ("สถาปัตยกรรมคอมพิวเตอร์", 3, ["04100104-66"], "major"),
    "04100202-66": ("การเขียนโปรแกรมเชิงวัตถุ", 3, ["04100103-66"], "major"),
    "04100203-66": ("ระบบฐานข้อมูล", 3, ["04100103-66"], "major"),
    "04100204-66": ("เครือข่ายคอมพิวเตอร์", 3, ["04100102-66"], "major"),
    "04000207-63": ("สถิติวิศวกรรม", 3, ["04000202-63"], "basic"),
    "01000301-62": ("วิทยาศาสตร์และเทคโนโลยีสมัยใหม่", 3, [], "general"),
    "01000202-62": ("ภาษาอังกฤษเพื่อการสื่อสาร 2", 3, ["01000201-62"], "general"),
    "04000203-63": ("ฟิสิกส์สำหรับงานวิศวกรรม", 3, [], "basic"),
    "04100103-66": ("โครงสร้างข้อมูลและอัลกอริทึม", 3, ["04100101-66"], "major"),
    "04100105-66": ("คณิตศาสตร์ดิสครีต", 3, [], "major"),
    "04100208-66": ("การพัฒนาเว็บแอปพลิเคชัน", 3, ["04100203-66"], "major"),
    "04100306-66": ("จริยธรรมและกฎหมายเทคโนโลยีสารสนเทศ", 2, [], "general"),
}

# ── หมู่เรียน: รหัส -> [(sec, meetings, ที่นั่งเปิด, ที่นั่งลง, อาจารย์)] ────────
# ตั้งใจให้บางคู่ "ชนกัน" เพื่อให้ตัวตรวจตารางชนมีเคสจริงให้จับ
SECTIONS: dict[str, list[tuple]] = {
    "04100201-66": [
        ("01", [meeting(MON, "09:00", "12:00", "ST-1301", "ST1")], 40, 38, ["ผศ.ดร.ชัยวัฒน์ ภูมิรัตน์"]),
        ("02", [meeting(WED, "13:00", "16:00", "ST-1301", "ST1")], 40, 22, ["ผศ.ดร.ชัยวัฒน์ ภูมิรัตน์"]),
    ],
    "04100202-66": [
        # sec 01 ชนกับ 04100201-66 sec 01 (จันทร์เช้า) โดยตั้งใจ
        ("01", [meeting(MON, "09:00", "11:00", "ST-1402", "ST1"),
                meeting(MON, "13:00", "16:00", "LAB-CPE1", "ST1", "lab")], 35, 30, ["ดร.พิมพ์ชนก แสงทอง"]),
        ("02", [meeting(TUE, "09:00", "11:00", "ST-1402", "ST1"),
                meeting(TUE, "13:00", "16:00", "LAB-CPE1", "ST1", "lab")], 35, 12, ["ดร.พิมพ์ชนก แสงทอง"]),
        ("03", [meeting(THU, "09:00", "11:00", "ST-1402", "ST1"),
                meeting(THU, "13:00", "16:00", "LAB-CPE2", "ST1", "lab")], 35, 35, ["อ.ณัฐพงษ์ วารีรัตน์"]),
    ],
    "04100203-66": [
        ("01", [meeting(TUE, "09:00", "11:00", "ST-1403", "ST1"),
                meeting(TUE, "13:00", "16:00", "LAB-CPE2", "ST1", "lab")], 35, 28, ["รศ.ดร.สุทธิพงษ์ จันทรา"]),
        ("02", [meeting(WED, "09:00", "11:00", "ST-1403", "ST1"),
                meeting(WED, "13:00", "16:00", "LAB-CPE2", "ST1", "lab")], 35, 15, ["รศ.ดร.สุทธิพงษ์ จันทรา"]),
    ],
    "04100204-66": [
        ("01", [meeting(THU, "09:00", "11:00", "ST-1404", "ST1"),
                meeting(THU, "13:00", "16:00", "LAB-NET", "ST2", "lab")], 30, 27, ["ผศ.ธนวัฒน์ เกียรติกุล"]),
        ("02", [meeting(FRI, "09:00", "11:00", "ST-1404", "ST1"),
                meeting(FRI, "13:00", "16:00", "LAB-NET", "ST2", "lab")], 30, 8, ["ผศ.ธนวัฒน์ เกียรติกุล"]),
    ],
    "04000207-63": [
        ("01", [meeting(MON, "13:00", "16:00", "EN-2201", "EN2")], 60, 45, ["อ.วราภรณ์ สุขสมบัติ"]),
        ("02", [meeting(FRI, "09:00", "12:00", "EN-2201", "EN2")], 60, 31, ["อ.วราภรณ์ สุขสมบัติ"]),
    ],
    "01000301-62": [
        ("01", [meeting(WED, "09:00", "12:00", "GE-101", "GE")], 80, 62, ["อ.กมลชนก ทรัพย์เจริญ"]),
        ("02", [meeting(FRI, "13:00", "16:00", "GE-101", "GE")], 80, 80, ["อ.กมลชนก ทรัพย์เจริญ"]),
    ],
    "01000202-62": [
        ("01", [meeting(TUE, "16:00", "18:00", "LA-301", "LA"),
                meeting(THU, "16:00", "18:00", "LA-301", "LA")], 40, 33, ["อ.Sarah Mitchell"]),
        ("02", [meeting(MON, "16:00", "18:00", "LA-302", "LA"),
                meeting(WED, "16:00", "18:00", "LA-302", "LA")], 40, 19, ["อ.ปิยะดา ศรีสุวรรณ"]),
    ],
    "04000203-63": [   # วิชาปี 1 สำหรับคนที่ต้องลงซ้ำ
        ("01", [meeting(TUE, "09:00", "12:00", "SC-201", "SC")], 50, 40, ["อ.ธีรเดช พงษ์ไพบูลย์"]),
        ("05", [meeting(SAT, "09:00", "12:00", "SC-201", "SC")], 50, 20, ["อ.ธีรเดช พงษ์ไพบูลย์"]),
    ],
    "04100103-66": [   # วิชาปี 1 สำหรับคนที่ต้องลงซ้ำ
        ("01", [meeting(WED, "09:00", "11:00", "ST-1201", "ST1"),
                meeting(WED, "13:00", "16:00", "LAB-CPE1", "ST1", "lab")], 35, 33, ["ดร.พิมพ์ชนก แสงทอง"]),
    ],
    "04100105-66": [
        ("01", [meeting(FRI, "13:00", "16:00", "ST-1202", "ST1")], 45, 20, ["ผศ.ดร.อรรถพล มณีวงศ์"]),
    ],
    "04100208-66": [   # วิชาชีพเลือก (ต้องผ่านฐานข้อมูลก่อน)
        ("01", [meeting(SAT, "09:00", "11:00", "ST-1405", "ST1"),
                meeting(SAT, "13:00", "16:00", "LAB-CPE1", "ST1", "lab")], 30, 11, ["อ.ณัฐพงษ์ วารีรัตน์"]),
    ],
    "04100306-66": [
        ("01", [meeting(MON, "16:00", "18:00", "ST-1101", "ST1")], 60, 24, ["อ.สุภาพร เรืองฤทธิ์"]),
    ],
}

# ── ตารางสอบ: รหัสวิชา -> (กลางภาค, ปลายภาค) ────────────────────────────
# 04100203-66 กับ 04000207-63 ตั้งใจให้ "สอบกลางภาคชนกัน" เพื่อทดสอบ C2
EXAMS = {
    "04100201-66": (exam("midterm", "2569-09-03", "09:00", "12:00", "ST-1301"),
                    exam("final", "2569-10-26", "09:00", "12:00", "ST-1301")),
    "04100202-66": (exam("midterm", "2569-09-04", "09:00", "12:00", "ST-1402"),
                    exam("final", "2569-10-27", "09:00", "12:00", "ST-1402")),
    "04100203-66": (exam("midterm", "2569-09-07", "13:00", "16:00", "ST-1403"),
                    exam("final", "2569-10-29", "13:00", "16:00", "ST-1403")),
    "04100204-66": (exam("midterm", "2569-09-08", "09:00", "12:00", "ST-1404"),
                    exam("final", "2569-10-30", "09:00", "12:00", "ST-1404")),
    "04000207-63": (exam("midterm", "2569-09-07", "13:00", "16:00", "EN-2201"),
                    exam("final", "2569-11-02", "13:00", "16:00", "EN-2201")),
    "01000301-62": (exam("midterm", "2569-09-09", "09:00", "11:00", "GE-101"),
                    exam("final", "2569-11-03", "09:00", "11:00", "GE-101")),
    "01000202-62": (exam("midterm", "2569-09-10", "13:00", "15:00", "LA-301"),
                    exam("final", "2569-11-04", "13:00", "15:00", "LA-301")),
    "04000203-63": (exam("midterm", "2569-09-11", "09:00", "12:00", "SC-201"),
                    exam("final", "2569-11-05", "09:00", "12:00", "SC-201")),
    "04100103-66": (exam("midterm", "2569-09-12", "09:00", "12:00", "ST-1201"),
                    exam("final", "2569-11-06", "09:00", "12:00", "ST-1201")),
    "04100105-66": (exam("midterm", "2569-09-09", "13:00", "16:00", "ST-1202"),
                    exam("final", "2569-11-03", "13:00", "16:00", "ST-1202")),
    "04100208-66": (exam("midterm", "2569-09-05", "09:00", "12:00", "ST-1405"),
                    exam("final", "2569-10-28", "09:00", "12:00", "ST-1405")),
    "04100306-66": (exam("midterm", "2569-09-10", "16:00", "18:00", "ST-1101"),
                    exam("final", "2569-11-04", "16:00", "18:00", "ST-1101")),
}

# ลำดับความสำคัญสำหรับ CP-SAT ของโมดูล 06 (P0=100 .. P3=30)
PRIORITY = {"major": 80, "basic": 60, "general": 40}


def build() -> dict:
    sections = []
    for code, secs in SECTIONS.items():
        name, credits, prereq, category = COURSES[code]
        mid, final = EXAMS[code]
        for sec, meetings, seat_total, seat_taken, teachers in secs:
            sections.append({
                "id": f"{code}-{sec}",
                "course_code": code,
                "section": sec,
                "course_name": name,
                "credits": credits,
                "category": category,
                "slots_mask": slots_mask(meetings),
                "meetings": meetings,
                "exams": [mid, final],
                "seat_total": seat_total,
                "seat_taken": seat_taken,
                "prerequisites": prereq,
                "campus": "คลองหก",
                "teachers": teachers,
                "is_online": False,
                "priority_score": PRIORITY[category],
            })
    return {
        "term": "1/2569",
        "program_id": "CPE-2566",
        "faculty": "คณะวิศวกรรมศาสตร์",
        "credit_rule": {"min_credits": 9, "max_credits": 21, "summer_max_credits": 9},
        "disclaimer": "ข้อมูลจำลองสำหรับต้นแบบ ไม่ใช่ตารางสอนจริงของมหาวิทยาลัย",
        "sections": sections,
    }


if __name__ == "__main__":
    data = build()
    out = Path(__file__).with_name("cpe_timetable_1_2569.json")
    out.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"เขียน {out.name}: {len(data['sections'])} หมู่เรียน "
          f"จาก {len(SECTIONS)} รายวิชา")
