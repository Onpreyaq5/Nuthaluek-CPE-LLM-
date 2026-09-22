"""06_schedule_conflict_engine - Demo & Synthetic Test Fixtures
Used exclusively when DEMO_MODE=true or in integration tests
"""
from ..models.schemas import Exam, Meeting, SectionInput


def get_demo_sections() -> list[SectionInput]:
    """ชุดข้อมูลจำลองสำหรับโหมดสาธิต (Synthetic Demo Data)
    ห้ามนำมาใช้เป็น Default Fallback ใน Production เด็ดขาด
    """
    return [
        SectionInput(
            id="01000101-01",
            course_code="01000101",
            section="01",
            course_name="Computer Programming",
            credits=3,
            meetings=[Meeting(day=0, start_min=540, end_min=720)],  # จันทร์ 09:00-12:00
            seat_total=40,
            seat_taken=30,
            priority_score=100,
        ),
        SectionInput(
            id="01000101-02",
            course_code="01000101",
            section="02",
            course_name="Computer Programming",
            credits=3,
            meetings=[Meeting(day=1, start_min=780, end_min=960)],  # อังคาร 13:00-16:00
            seat_total=40,
            seat_taken=20,
            priority_score=100,
        ),
        SectionInput(
            id="01000102-01",
            course_code="01000102",
            section="01",
            course_name="Data Structures",
            credits=3,
            meetings=[Meeting(day=0, start_min=780, end_min=960)],  # จันทร์ 13:00-16:00
            seat_total=35,
            seat_taken=25,
            priority_score=80,
        ),
        SectionInput(
            id="01000103-01",
            course_code="01000103",
            section="01",
            course_name="Calculus I",
            credits=3,
            meetings=[Meeting(day=2, start_min=540, end_min=720)],  # พุธ 09:00-12:00
            seat_total=50,
            seat_taken=40,
            priority_score=80,
        ),
        SectionInput(
            id="01000104-01",
            course_code="01000104",
            section="01",
            course_name="Physics I",
            credits=3,
            meetings=[Meeting(day=3, start_min=540, end_min=720)],  # พฤหัส 09:00-12:00
            seat_total=45,
            seat_taken=30,
            priority_score=60,
        ),
        SectionInput(
            id="01000105-01",
            course_code="01000105",
            section="01",
            course_name="Digital Logic Design",
            credits=3,
            meetings=[Meeting(day=3, start_min=780, end_min=960)],  # พฤหัส 13:00-16:00
            seat_total=40,
            seat_taken=20,
            priority_score=60,
        ),
        SectionInput(
            id="01000106-01",
            course_code="01000106",
            section="01",
            course_name="English for Communication",
            credits=3,
            meetings=[Meeting(day=1, start_min=540, end_min=720)],  # อังคาร 09:00-12:00
            seat_total=30,
            seat_taken=15,
            priority_score=40,
        ),
    ]
