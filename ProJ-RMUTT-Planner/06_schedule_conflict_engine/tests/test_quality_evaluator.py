"""Tests for Soft Rules (W1 - W5)"""
from src.core.quality_evaluator import evaluate_quality
from src.models.schemas import Meeting, SectionInput, StudentPreferences


def test_w1_long_stretch():
    """เรียนติดต่อกันเกิน 6 ชม. ไม่มีพัก (เช่น 09:00 - 16:00 = 7 ชม.)"""
    sec = SectionInput(
        id="CPE101-01",
        course_code="CPE101",
        section="01",
        meetings=[Meeting(day=0, start_min=540, end_min=960)],  # 7 ชม.
    )
    warnings, profile = evaluate_quality([sec])
    w1 = [w for w in warnings if w.code == "W1"]
    assert len(w1) == 1
    assert w1[0].message_key == "long_stretch"


def test_w2_large_gap():
    """ช่องว่างระหว่างคาบเกิน 4 ชม."""
    sec1 = SectionInput(
        id="CPE101-01",
        course_code="CPE101",
        section="01",
        meetings=[Meeting(day=0, start_min=540, end_min=660)],  # 09:00 - 11:00
    )
    sec2 = SectionInput(
        id="CPE102-01",
        course_code="CPE102",
        section="01",
        meetings=[Meeting(day=0, start_min=960, end_min=1080)],  # 16:00 - 18:00 (ห่าง 5 ชม.)
    )
    warnings, profile = evaluate_quality([sec1, sec2])
    w2 = [w for w in warnings if w.code == "W2"]
    assert len(w2) == 1
    assert w2[0].message_key == "large_gap"


def test_w3_early_morning_and_free_days():
    """คาบเช้า 08:00 ในวันที่ขอว่าง หรือตั้ง avoid_morning"""
    sec = SectionInput(
        id="CPE101-01",
        course_code="CPE101",
        section="01",
        meetings=[Meeting(day=4, start_min=480, end_min=600)],  # ศุกร์ 08:00 - 10:00
    )
    pref = StudentPreferences(avoid_morning=True, free_days=["FRI"])
    warnings, profile = evaluate_quality([sec], preferences=pref)

    w3 = [w for w in warnings if w.code == "W3"]
    # ต้องมีทั้งแจ้งเตือนวันศุกร์มีเรียน และแจ้งเตือนมีคาบเช้า
    keys = {w.message_key for w in w3}
    assert "busy_preferred_free_day" in keys
    assert "early_morning_class" in keys


def test_w4_rush_building_move():
    """ต้องย้ายอาคารระหว่างคาบที่ติดกันน้อยกว่า 15 นาที"""
    sec1 = SectionInput(
        id="CPE101-01",
        course_code="CPE101",
        section="01",
        meetings=[Meeting(day=0, start_min=540, end_min=660, building="Building 1")],  # จันทร์ 09:00-11:00
    )
    sec2 = SectionInput(
        id="CPE102-01",
        course_code="CPE102",
        section="01",
        meetings=[Meeting(day=0, start_min=665, end_min=780, building="Building 2")],  # จันทร์ 11:05-13:00 (พัก 5 นาที)
    )
    warnings, _ = evaluate_quality([sec1, sec2])
    w4 = [w for w in warnings if w.code == "W4"]
    assert len(w4) == 1
    assert w4[0].detail["gap_minutes"] == 5


def test_w5_heavy_days():
    """เรียน 6 วันต่อสัปดาห์"""
    sections = [
        SectionInput(
            id=f"CPE10{i}-01",
            course_code=f"CPE10{i}",
            section="01",
            meetings=[Meeting(day=i, start_min=540, end_min=660)],
        )
        for i in range(6)  # จันทร์ ถึง เสาร์
    ]
    warnings, profile = evaluate_quality(sections)
    w5 = [w for w in warnings if w.code == "W5"]
    assert len(w5) == 1
    assert w5[0].detail["days_on_campus"] == 6
