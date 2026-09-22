"""สร้างตารางสอนจำลอง สาขาวิศวกรรมคอมพิวเตอร์ (CPE) ครบทุกรายวิชาในหลักสูตร

ข้อมูลชุดนี้เป็น **ต้นแบบ (prototype)** ไม่ใช่ตารางสอนจริงของมหาวิทยาลัย
โครงสร้างผลลัพธ์ตรงกับ SectionInput ของโมดูล 06_schedule_conflict_engine
จึงส่งเข้า POST /conflicts/check และ /plans/auto ได้ทันที

รัน:  python generate_timetable.py
ผลลัพธ์:
    cpe_timetable_1_2569.json   ภาคการศึกษาที่ 1 (วิชาของเทอมคี่ทุกชั้นปี)
    cpe_timetable_2_2569.json   ภาคการศึกษาที่ 2 (วิชาของเทอมคู่ทุกชั้นปี)

หลักการจัดเวลา
  - วิชาที่อยู่ "ชั้นปีเดียวกัน เทอมเดียวกัน" จะไม่ชนกันในหมู่เรียนที่ 01
    เพื่อให้นักศึกษาลงตามแผนแนะนำได้จริงโดยไม่ติด C1
  - หมู่เรียนที่ 02 ขึ้นไปสลับวัน/เวลา เพื่อให้มีทางเลือกและเกิดเคสชนข้ามชั้นปี
  - ใส่เคสทดสอบไว้จงใจ: เวลาเรียนชน / เวลาสอบชน / ที่นั่งเต็ม (ดูท้ายไฟล์)
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

CAMPUS = "คลองหก"

# วันเปิดภาคการศึกษา (วันจันทร์) ตามปฏิทินการศึกษา 2569
TERM_START = {1: "2026-06-15", 2: "2026-11-23"}
PRIORITY = {"major": 80, "basic": 60, "general": 40, "elective": 30}


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
    return {"day": day, "start_min": hm(start), "end_min": hm(end),
            "room": room, "building": building, "meeting_type": kind}


def exam(kind: str, date: str, start: str, end: str, room: str) -> dict:
    return {"exam_type": kind, "exam_date": date,
            "start_min": hm(start), "end_min": hm(end), "room": room}


# ── แคตตาล็อกรายวิชา: รหัส -> (ชื่อ, หน่วยกิต, มีแลปไหม, บังคับก่อน, หมวด) ──
COURSES: dict[str, tuple[str, int, bool, list[str], str]] = {
    # ---- ชั้นปีที่ 1 ภาคการศึกษาที่ 1 ----
    "01000101-62": ("สังคมกับความยั่งยืน", 3, False, [], "general"),
    "01000201-62": ("ภาษาอังกฤษเพื่อการสื่อสาร 1", 3, True, [], "general"),
    "04000202-63": ("แคลคูลัสประยุกต์สำหรับงานวิศวกรรม", 3, False, [], "basic"),
    "04000203-63": ("ฟิสิกส์สำหรับงานวิศวกรรม", 3, False, [], "basic"),
    "04000204-63": ("ปฏิบัติการฟิสิกส์สำหรับงานวิศวกรรม", 1, True, [], "basic"),
    "04100101-66": ("การเขียนโปรแกรมคอมพิวเตอร์", 3, True, [], "major"),
    "04100102-66": ("พื้นฐานวิศวกรรมคอมพิวเตอร์", 3, False, [], "major"),
    # ---- ชั้นปีที่ 1 ภาคการศึกษาที่ 2 ----
    "01000202-62": ("ภาษาอังกฤษเพื่อการสื่อสาร 2", 3, True, ["01000201-62"], "general"),
    "01000102-62": ("พลเมืองดิจิทัล", 1, False, [], "general"),
    "04000205-63": ("แคลคูลัสประยุกต์สำหรับงานวิศวกรรม 2", 3, False, ["04000202-63"], "basic"),
    "04000206-63": ("เคมีสำหรับงานวิศวกรรม", 3, False, [], "basic"),
    "04100103-66": ("โครงสร้างข้อมูลและอัลกอริทึม", 3, True, ["04100101-66"], "major"),
    "04100104-66": ("ดิจิทัลลอจิกและการออกแบบ", 3, True, ["04100102-66"], "major"),
    "04100105-66": ("คณิตศาสตร์ดิสครีต", 3, False, [], "major"),
    # ---- ชั้นปีที่ 2 ภาคการศึกษาที่ 1 ----
    "04100201-66": ("สถาปัตยกรรมคอมพิวเตอร์", 3, False, ["04100104-66"], "major"),
    "04100202-66": ("การเขียนโปรแกรมเชิงวัตถุ", 3, True, ["04100103-66"], "major"),
    "04100203-66": ("ระบบฐานข้อมูล", 3, True, ["04100103-66"], "major"),
    "04100204-66": ("เครือข่ายคอมพิวเตอร์", 3, True, ["04100102-66"], "major"),
    "04000207-63": ("สถิติวิศวกรรม", 3, False, ["04000202-63"], "basic"),
    "01000301-62": ("วิทยาศาสตร์และเทคโนโลยีสมัยใหม่", 3, False, [], "general"),
    # ---- ชั้นปีที่ 2 ภาคการศึกษาที่ 2 ----
    "04100205-66": ("ระบบปฏิบัติการ", 3, False, ["04100201-66"], "major"),
    "04100206-66": ("วิศวกรรมซอฟต์แวร์", 3, False, ["04100202-66"], "major"),
    "04100207-66": ("ไมโครคอนโทรลเลอร์และระบบสมองกลฝังตัว", 3, True, ["04100201-66"], "major"),
    "04100208-66": ("การพัฒนาเว็บแอปพลิเคชัน", 3, True, ["04100203-66"], "major"),
    "04100209-66": ("ความน่าจะเป็นและสถิติสำหรับวิศวกรรมคอมพิวเตอร์", 3, False, ["04000207-63"], "major"),
    "01000203-62": ("ภาษาอังกฤษเชิงวิชาการ", 3, True, ["01000202-62"], "general"),
    # ---- ชั้นปีที่ 3 ภาคการศึกษาที่ 1 ----
    "04100301-66": ("ปัญญาประดิษฐ์", 3, True, ["04100103-66"], "major"),
    "04100302-66": ("การเรียนรู้ของเครื่อง", 3, True, ["04100209-66"], "major"),
    "04100303-66": ("ความมั่นคงปลอดภัยไซเบอร์", 3, False, ["04100204-66"], "major"),
    "04100304-66": ("การประมวลผลแบบกลุ่มเมฆ", 3, True, ["04100205-66"], "major"),
    "04100305-66": ("เตรียมโครงงานวิศวกรรมคอมพิวเตอร์", 1, True, [], "major"),
    "04000201-62": ("ภาษาอังกฤษสำหรับงานวิศวกรรม", 3, True, ["01000202-62"], "general"),
    "04100306-66": ("จริยธรรมและกฎหมายเทคโนโลยีสารสนเทศ", 2, False, [], "general"),
    # ---- ชั้นปีที่ 3 ภาคการศึกษาที่ 2 ----
    "04100307-66": ("โครงงานวิศวกรรมคอมพิวเตอร์ 1", 3, True, ["04100305-66"], "major"),
    "04100308-66": ("การประมวลผลภาษาธรรมชาติ", 3, True, ["04100302-66"], "major"),
    "04100309-66": ("อินเทอร์เน็ตของสรรพสิ่ง", 3, True, ["04100207-66"], "major"),
    "04100310-66": ("วิศวกรรมข้อมูลขนาดใหญ่", 3, True, ["04100203-66"], "major"),
    # ---- ชั้นปีที่ 4 ----
    "04100401-66": ("โครงงานวิศวกรรมคอมพิวเตอร์ 2", 3, True, ["04100307-66"], "major"),
    "04100402-66": ("หัวข้อพิเศษทางวิศวกรรมคอมพิวเตอร์", 3, False, [], "major"),
    "04100403-66": ("สหกิจศึกษาทางวิศวกรรมคอมพิวเตอร์", 6, True, [], "major"),
    # ---- วิชาชีพเลือก / เลือกเสรี (เปิดทั้งสองเทอม) ----
    "04100501-66": ("การพัฒนาแอปพลิเคชันบนอุปกรณ์เคลื่อนที่", 3, True, ["04100202-66"], "elective"),
    "04100502-66": ("คอมพิวเตอร์วิทัศน์", 3, True, ["04100302-66"], "elective"),
    "04100503-66": ("การทดสอบและประกันคุณภาพซอฟต์แวร์", 3, False, ["04100206-66"], "elective"),
    "04100504-66": ("บล็อกเชนและเทคโนโลยีบัญชีแยกประเภทแบบกระจาย", 3, False, ["04100204-66"], "elective"),
    "04100505-66": ("การออกแบบประสบการณ์ผู้ใช้", 3, True, [], "elective"),
    "04100506-66": ("ระบบสารสนเทศเพื่อการจัดการ", 3, False, [], "elective"),
}

# ── แผนการศึกษา: (ชั้นปี, เทอม) -> รายวิชา ──────────────────────────────
STUDY_PLAN: dict[tuple[int, int], list[str]] = {
    (1, 1): ["01000101-62", "01000201-62", "04000202-63", "04000203-63",
             "04000204-63", "04100101-66", "04100102-66"],
    (1, 2): ["01000202-62", "01000102-62", "04000205-63", "04000206-63",
             "04100103-66", "04100104-66", "04100105-66"],
    (2, 1): ["04100201-66", "04100202-66", "04100203-66", "04100204-66",
             "04000207-63", "01000301-62"],
    (2, 2): ["04100205-66", "04100206-66", "04100207-66", "04100208-66",
             "04100209-66", "01000203-62"],
    (3, 1): ["04100301-66", "04100302-66", "04100303-66", "04100304-66",
             "04100305-66", "04000201-62", "04100306-66"],
    (3, 2): ["04100307-66", "04100308-66", "04100309-66", "04100310-66"],
    (4, 1): ["04100401-66", "04100402-66"],
    (4, 2): ["04100403-66"],
}

ELECTIVES = ["04100501-66", "04100502-66", "04100503-66",
             "04100504-66", "04100505-66", "04100506-66"]

# ── ช่องเวลามาตรฐาน: วิชาลำดับที่ i ของชั้นปีนั้น ได้ช่องที่ i ──────────
# ออกแบบให้วิชาในชั้นปี+เทอมเดียวกัน ไม่ทับกันเลย (นักศึกษาลงตามแผนได้จริง)
BASE_SLOTS: list[tuple[int, str, str]] = [
    (MON, "09:00", "12:00"),
    (TUE, "09:00", "12:00"),
    (WED, "09:00", "12:00"),
    (THU, "09:00", "12:00"),
    (FRI, "09:00", "12:00"),
    (MON, "13:00", "16:00"),
    (TUE, "13:00", "16:00"),
    (WED, "13:00", "16:00"),
]
# หมู่เรียนที่ 2 ใช้ช่องบ่าย/เย็นสลับวัน เพื่อให้มีทางเลือก
ALT_SLOTS: list[tuple[int, str, str]] = [
    (THU, "13:00", "16:00"),
    (FRI, "13:00", "16:00"),
    (SAT, "09:00", "12:00"),
    (SAT, "13:00", "16:00"),
    (MON, "16:00", "19:00"),
    (TUE, "16:00", "19:00"),
    (WED, "16:00", "19:00"),
    (THU, "16:00", "19:00"),
]

BUILDINGS = {"major": ("ST1", "ST-1{n:03d}"), "basic": ("EN2", "EN-2{n:03d}"),
             "general": ("GE", "GE-{n:03d}"), "elective": ("ST2", "ST-2{n:03d}")}
TEACHERS = [
    "ผศ.ดร.ชัยวัฒน์ ภูมิรัตน์", "ดร.พิมพ์ชนก แสงทอง", "รศ.ดร.สุทธิพงษ์ จันทรา",
    "ผศ.ธนวัฒน์ เกียรติกุล", "อ.วราภรณ์ สุขสมบัติ", "อ.กมลชนก ทรัพย์เจริญ",
    "อ.ณัฐพงษ์ วารีรัตน์", "ผศ.ดร.อรรถพล มณีวงศ์", "อ.สุภาพร เรืองฤทธิ์",
    "ดร.ธีรเดช พงษ์ไพบูลย์", "อ.Sarah Mitchell", "อ.ปิยะดา ศรีสุวรรณ",
]

# ── เคสทดสอบที่จงใจใส่ไว้ ──────────────────────────────────────────────
# (รหัสวิชา, หมู่) -> ทำให้ที่นั่งเต็ม
FULL_SECTIONS = {("04100202-66", "03"), ("01000301-62", "02"), ("04100304-66", "02")}
# คู่วิชาที่จงใจให้เวลาเรียนชนกันในหมู่ 01 (คนละชั้นปี จึงไม่กระทบแผนแนะนำ)
FORCED_CLASH = {"04100202-66": ("04100201-66", 1)}   # ใช้ช่องเดียวกับ 04100201-66 หมู่ 01
# คู่วิชาที่จงใจให้สอบกลางภาคชนกัน
FORCED_EXAM_CLASH = {"04000207-63": "04100203-66"}


def _exam_dates(term: int, index: int) -> tuple[dict, dict]:
    """กระจายวันสอบตามลำดับวิชา ภายในช่วงสอบของปฏิทินการศึกษา"""
    if term == 1:
        mid_days = ["2569-09-03", "2569-09-04", "2569-09-05", "2569-09-07",
                    "2569-09-08", "2569-09-09", "2569-09-10", "2569-09-11", "2569-09-12"]
        fin_days = ["2569-10-26", "2569-10-27", "2569-10-28", "2569-10-29", "2569-10-30",
                    "2569-11-02", "2569-11-03", "2569-11-04", "2569-11-05", "2569-11-06"]
    else:
        mid_days = ["2570-02-08", "2570-02-09", "2570-02-10", "2570-02-11", "2570-02-12",
                    "2570-02-13", "2570-02-16", "2570-02-17"]
        fin_days = ["2570-03-29", "2570-03-30", "2570-03-31", "2570-04-01", "2570-04-02",
                    "2570-04-06", "2570-04-07", "2570-04-08", "2570-04-09"]
    slot = ["09:00", "13:00"][index % 2]
    end = "12:00" if slot == "09:00" else "16:00"
    return (
        exam("midterm", mid_days[index % len(mid_days)], slot, end, "N/A"),
        exam("final", fin_days[index % len(fin_days)], slot, end, "N/A"),
    )


def build_term(term: int) -> dict:
    """สร้างตารางสอนของภาคการศึกษาที่ระบุ (1 หรือ 2)"""
    sections: list[dict] = []
    room_no = 101
    exam_index = 0
    slot_of_course: dict[str, tuple[int, str, str]] = {}

    # รายวิชาของเทอมนี้: ทุกชั้นปี + วิชาเลือก
    plan_items: list[tuple[int, str]] = []
    for (year, t), codes in sorted(STUDY_PLAN.items()):
        if t != term:
            continue
        plan_items.extend((year, c) for c in codes)
    plan_items.extend((0, c) for c in ELECTIVES)

    # ให้แต่ละชั้นปีเริ่มนับช่องเวลาใหม่ -> วิชาในปีเดียวกันไม่ทับกัน
    per_year_index: dict[int, int] = {}

    for year, code in plan_items:
        name, credits, has_lab, prereq, category = COURSES[code]
        idx = per_year_index.get(year, 0)
        per_year_index[year] = idx + 1

        building, room_fmt = BUILDINGS[category]
        room = room_fmt.format(n=room_no)
        room_no += 1

        # ── หมู่ 01 ──
        if code in FORCED_CLASH:
            other, _ = FORCED_CLASH[code]
            day, start, end = slot_of_course[other]
        else:
            day, start, end = BASE_SLOTS[idx % len(BASE_SLOTS)]
        slot_of_course[code] = (day, start, end)

        mid, fin = _exam_dates(term, exam_index)
        exam_index += 1
        if code in FORCED_EXAM_CLASH:
            target = FORCED_EXAM_CLASH[code]
            mid = next(e for s in sections if s["course_code"] == target
                       for e in s["exams"] if e["exam_type"] == "midterm")

        variants = [("01", day, start, end, 40, 26)]
        alt = ALT_SLOTS[idx % len(ALT_SLOTS)]
        variants.append(("02", alt[0], alt[1], alt[2], 35, 14))
        if category == "major" and credits >= 3:
            alt2 = ALT_SLOTS[(idx + 3) % len(ALT_SLOTS)]
            variants.append(("03", alt2[0], alt2[1], alt2[2], 30, 30))

        for i, (sec, d, st, en, total, taken) in enumerate(variants):
            meetings = [meeting(d, st, en if not has_lab else _mid(st, en), room, building)]
            if has_lab:
                meetings.append(meeting(d, _mid(st, en), en, f"LAB-{building}", building, "lab"))
            if (code, sec) in FULL_SECTIONS:
                taken = total
            sections.append({
                "id": f"{code}-{sec}",
                "course_code": code,
                "section": sec,
                "course_name": name,
                "credits": credits,
                "category": category,
                "suggested_year": year or None,
                "slots_mask": slots_mask(meetings),
                "meetings": meetings,
                "exams": [mid, fin],
                "seat_total": total,
                "seat_taken": taken,
                "prerequisites": prereq,
                "campus": CAMPUS,
                "teachers": [TEACHERS[(room_no + i) % len(TEACHERS)]],
                "is_online": False,
                "priority_score": PRIORITY[category],
            })

    return {
        "term": f"{term}/2569",
        # วันจันทร์แรกของภาคการศึกษา ตรงกับปฏิทินการศึกษาใน data/knowledge
        # ใช้คำนวณวันที่จริงของแต่ละคาบตอนส่งออกไฟล์ปฏิทิน (.ics)
        "term_start": TERM_START[term],
        "weeks": 16,
        "program_id": "CPE-2566",
        "faculty": "คณะวิศวกรรมศาสตร์",
        "credit_rule": {"min_credits": 9, "max_credits": 21, "summer_max_credits": 9},
        "disclaimer": "ข้อมูลจำลองสำหรับต้นแบบ ไม่ใช่ตารางสอนจริงของมหาวิทยาลัย",
        "sections": sections,
    }


def _mid(start: str, end: str) -> str:
    """หาจุดกึ่งกลางของคาบ ใช้แบ่งบรรยาย/ปฏิบัติ"""
    total = (hm(start) + hm(end)) // 2
    total -= total % 30
    return f"{total // 60:02d}:{total % 60:02d}"


if __name__ == "__main__":
    for term in (1, 2):
        data = build_term(term)
        out = Path(__file__).with_name(f"cpe_timetable_{term}_2569.json")
        out.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        courses = {s["course_code"] for s in data["sections"]}
        print(f"เขียน {out.name}: {len(data['sections'])} หมู่เรียน จาก {len(courses)} รายวิชา")
