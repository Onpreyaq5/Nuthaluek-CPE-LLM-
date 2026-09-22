"""Tests for Google OR-Tools CP-SAT Auto Planner"""
from src.core.planner import generate_schedule_plans
from src.models.schemas import Meeting, SectionInput, StudentPreferences


def test_cp_sat_generates_valid_plans():
    """ทดสอบว่า CP-SAT สามารถสร้างแผนการเรียนที่ไม่ชนกันได้สำเร็จ"""
    available_sections = [
        SectionInput(
            id="CPE101-01",
            course_code="CPE101",
            section="01",
            credits=3,
            meetings=[Meeting(day=0, start_min=540, end_min=720)],  # จันทร์ 09:00-12:00
            priority_score=100,
        ),
        SectionInput(
            id="CPE101-02",
            course_code="CPE101",
            section="02",
            credits=3,
            meetings=[Meeting(day=1, start_min=540, end_min=720)],  # อังคาร 09:00-12:00
            priority_score=100,
        ),
        SectionInput(
            id="CPE102-01",
            course_code="CPE102",
            section="01",
            credits=3,
            meetings=[Meeting(day=0, start_min=540, end_min=720)],  # จันทร์ 09:00-12:00 (ชนกับ CPE101-01)
            priority_score=80,
        ),
        SectionInput(
            id="CPE102-02",
            course_code="CPE102",
            section="02",
            credits=3,
            meetings=[Meeting(day=2, start_min=540, end_min=720)],  # พุธ 09:00-12:00
            priority_score=80,
        ),
        SectionInput(
            id="CPE103-01",
            course_code="CPE103",
            section="01",
            credits=3,
            meetings=[Meeting(day=3, start_min=540, end_min=720)],  # พฤหัส 09:00-12:00
            priority_score=60,
        ),
        SectionInput(
            id="CPE104-01",
            course_code="CPE104",
            section="01",
            credits=3,
            meetings=[Meeting(day=4, start_min=540, end_min=720)],  # ศุกร์ 09:00-12:00
            priority_score=40,
        ),
    ]

    response = generate_schedule_plans(
        available_sections=available_sections,
        max_candidates=3,
    )

    assert response.status == "success"
    assert response.plans_count >= 1

    # ตรวจสอบว่าทุกแผนที่คืนกลับมาไม่มีเวลาชนกัน
    for plan in response.plans:
        assert plan.total_credits >= 9
        assert isinstance(plan.sections, list)
        assert all(isinstance(s, str) for s in plan.sections)
        sec_ids = plan.sections
        # ห้ามมีทั้ง CPE101-01 และ CPE102-01 ในแผนเดียวกันเพราะเวลาชนกัน
        assert not ("CPE101-01" in sec_ids and "CPE102-01" in sec_ids)
        assert len(plan.section_details) == len(plan.sections)


def test_cp_sat_respects_free_day_preference():
    """ทดสอบว่า CP-SAT พยายามจัดแผนโดยหลีกเลี่ยงวันที่ผู้ใช้ขอว่าง"""
    available_sections = [
        SectionInput(
            id="CPE101-01",
            course_code="CPE101",
            section="01",
            credits=3,
            meetings=[Meeting(day=4, start_min=540, end_min=720)],  # ศุกร์ 09:00-12:00
        ),
        SectionInput(
            id="CPE101-02",
            course_code="CPE101",
            section="02",
            credits=3,
            meetings=[Meeting(day=1, start_min=540, end_min=720)],  # อังคาร 09:00-12:00
        ),
        SectionInput(
            id="CPE102-01",
            course_code="CPE102",
            section="01",
            credits=3,
            meetings=[Meeting(day=2, start_min=540, end_min=720)],  # พุธ
        ),
        SectionInput(
            id="CPE103-01",
            course_code="CPE103",
            section="01",
            credits=3,
            meetings=[Meeting(day=3, start_min=540, end_min=720)],  # พฤหัส
        ),
    ]

    pref = StudentPreferences(free_days=["FRI"])
    response = generate_schedule_plans(
        available_sections=available_sections,
        preferences=pref,
        max_candidates=1,
    )

    assert response.plans_count >= 1
    best_plan = response.plans[0]
    assert all(isinstance(s, str) for s in best_plan.sections)
    best_sec_ids = best_plan.sections
    # แผนที่ดีที่สุดต้องเลือก CPE101-02 (วันอังคาร) แทน CPE101-01 (วันศุกร์)
    assert "CPE101-02" in best_sec_ids
    assert "CPE101-01" not in best_sec_ids
