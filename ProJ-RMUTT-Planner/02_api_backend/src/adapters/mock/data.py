from __future__ import annotations

from src.schemas.common import Day
from src.schemas.courses import Course, MeetingSlot, Section

TERM = "1/2569"

# ~8 วิชา: มี prerequisite ต่อกัน (CPE201 -> CPE301 -> CPE401), บางคู่ section เวลาชนกันโดยตั้งใจ
COURSES: dict[str, Course] = {
    "CPE201": Course(
        code="CPE201", name_th="โครงสร้างข้อมูลเบื้องต้น",
        name_en="Introduction to Data Structures", credits=3, prerequisites=[],
    ),
    "CPE301": Course(
        code="CPE301", name_th="โครงสร้างข้อมูลและขั้นตอนวิธี",
        name_en="Data Structures and Algorithms", credits=3, prerequisites=["CPE201"],
    ),
    "CPE302": Course(
        code="CPE302", name_th="ระบบปฏิบัติการ",
        name_en="Operating Systems", credits=3, prerequisites=["CPE201"],
    ),
    "CPE303": Course(
        code="CPE303", name_th="ระบบฐานข้อมูล",
        name_en="Database Systems", credits=3, prerequisites=["CPE201"],
    ),
    "CPE305": Course(
        code="CPE305", name_th="เครือข่ายคอมพิวเตอร์",
        name_en="Computer Networks", credits=3, prerequisites=[],
    ),
    "GE101": Course(
        code="GE101", name_th="ภาษาอังกฤษพื้นฐาน",
        name_en="Basic English", credits=3, prerequisites=[],
    ),
    "GE102": Course(
        code="GE102", name_th="คณิตศาสตร์ทั่วไป",
        name_en="General Mathematics", credits=3, prerequisites=[],
    ),
    "CPE401": Course(
        code="CPE401", name_th="ปัญญาประดิษฐ์เบื้องต้น",
        name_en="Introduction to Artificial Intelligence", credits=3, prerequisites=["CPE301"],
    ),
}

SECTIONS: dict[str, Section] = {
    "CPE201-01": Section(
        section_id="CPE201-01", course_code="CPE201", course_name_th=COURSES["CPE201"].name_th,
        teacher="อ.กานดา มีสุข", credits=3, seats_available=10, seats_total=40,
        meetings=[MeetingSlot(day=Day.MON, start="09:00", end="11:50", room="ENG-201")],
    ),
    "CPE301-01": Section(  # จงใจให้เวลาชนกับ CPE201-01 (ทดสอบ C1)
        section_id="CPE301-01", course_code="CPE301", course_name_th=COURSES["CPE301"].name_th,
        teacher="อ.สมชาย ใจดี", credits=3, seats_available=5, seats_total=40,
        meetings=[MeetingSlot(day=Day.MON, start="09:00", end="11:50", room="ENG-301")],
    ),
    "CPE301-02": Section(
        section_id="CPE301-02", course_code="CPE301", course_name_th=COURSES["CPE301"].name_th,
        teacher="อ.สมชาย ใจดี", credits=3, seats_available=8, seats_total=40,
        meetings=[MeetingSlot(day=Day.TUE, start="13:00", end="15:50", room="ENG-302")],
    ),
    "CPE302-01": Section(  # ที่นั่งเต็ม (ทดสอบ C6)
        section_id="CPE302-01", course_code="CPE302", course_name_th=COURSES["CPE302"].name_th,
        teacher="อ.รักชาติ วงศ์ดี", credits=3, seats_available=0, seats_total=40,
        meetings=[MeetingSlot(day=Day.WED, start="09:00", end="11:50", room="ENG-303")],
    ),
    "CPE302-02": Section(
        section_id="CPE302-02", course_code="CPE302", course_name_th=COURSES["CPE302"].name_th,
        teacher="อ.รักชาติ วงศ์ดี", credits=3, seats_available=12, seats_total=40,
        meetings=[MeetingSlot(day=Day.THU, start="13:00", end="15:50", room="ENG-304")],
    ),
    "CPE303-01": Section(
        section_id="CPE303-01", course_code="CPE303", course_name_th=COURSES["CPE303"].name_th,
        teacher="อ.นภา แจ่มใส", credits=3, seats_available=20, seats_total=35,
        meetings=[MeetingSlot(day=Day.FRI, start="09:00", end="11:50", room="ENG-305")],
    ),
    "CPE305-01": Section(
        section_id="CPE305-01", course_code="CPE305", course_name_th=COURSES["CPE305"].name_th,
        teacher="อ.วิชัย เก่งกล้า", credits=3, seats_available=15, seats_total=40,
        meetings=[MeetingSlot(day=Day.MON, start="13:00", end="15:50", room="ENG-306")],
    ),
    "GE101-01": Section(
        section_id="GE101-01", course_code="GE101", course_name_th=COURSES["GE101"].name_th,
        teacher="Mr. John Smith", credits=3, seats_available=30, seats_total=60,
        meetings=[MeetingSlot(day=Day.TUE, start="09:00", end="11:50", room="GE-101")],
    ),
    "GE102-01": Section(
        section_id="GE102-01", course_code="GE102", course_name_th=COURSES["GE102"].name_th,
        teacher="อ.มานี ตั้งใจ", credits=3, seats_available=25, seats_total=60,
        meetings=[MeetingSlot(day=Day.WED, start="13:00", end="15:50", room="GE-102")],
    ),
    "CPE401-01": Section(  # ต้องผ่าน CPE301 ก่อน (ทดสอบ C3 เมื่อ student ยังไม่ผ่าน)
        section_id="CPE401-01", course_code="CPE401", course_name_th=COURSES["CPE401"].name_th,
        teacher="ดร.ปัญญา ฉลาดคิด", credits=3, seats_available=5, seats_total=30,
        meetings=[MeetingSlot(day=Day.FRI, start="13:00", end="15:50", room="ENG-401")],
    ),
}
