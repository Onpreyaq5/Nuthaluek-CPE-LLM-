"""Tests for 182-bitmask collision logic"""
from src.core.bitmask import (
    TOTAL_BITS,
    SLOTS_PER_DAY,
    time_range_to_bitmask,
    check_clash,
    decode_overlap,
    get_schedule_profile,
)


def test_bitmask_total_slots():
    assert TOTAL_BITS == 182
    assert SLOTS_PER_DAY == 26


def test_touching_head_to_tail_no_clash():
    """คาบที่ติดกันพอดีหัวท้าย เช่น 09:00-11:00 กับ 11:00-13:00 ต้องไม่ชนกัน"""
    # 09:00 = 540 นาที, 11:00 = 660 นาที, 13:00 = 780 นาที
    mask1 = time_range_to_bitmask(day=0, start_min=540, end_min=660)
    mask2 = time_range_to_bitmask(day=0, start_min=660, end_min=780)

    assert not check_clash(mask1, mask2)
    assert decode_overlap(mask1, mask2) == []


def test_overlapping_classes_clash():
    """คาบที่ทับซ้อนกันบางส่วน เช่น 09:00-11:30 กับ 11:00-13:00 ต้องชนกันที่ 11:00-11:30"""
    mask1 = time_range_to_bitmask(day=0, start_min=540, end_min=690)  # 09:00 - 11:30
    mask2 = time_range_to_bitmask(day=0, start_min=660, end_min=780)  # 11:00 - 13:00

    assert check_clash(mask1, mask2)
    overlaps = decode_overlap(mask1, mask2)
    assert len(overlaps) == 1
    assert overlaps[0]["day"] == "MON"
    assert overlaps[0]["overlap_start"] == "11:00"
    assert overlaps[0]["overlap_end"] == "11:30"


def test_different_days_no_clash():
    """เวลาเดียวกันคนละวัน ต้องไม่ชนกัน"""
    mask_mon = time_range_to_bitmask(day=0, start_min=540, end_min=720)
    mask_tue = time_range_to_bitmask(day=1, start_min=540, end_min=720)

    assert not check_clash(mask_mon, mask_tue)


def test_spanning_noon():
    """คาบคร่อมเที่ยง 11:30 - 13:30"""
    mask = time_range_to_bitmask(day=2, start_min=690, end_min=810)
    assert mask > 0


def test_schedule_profile_analysis():
    """ทดสอบการวิเคราะห์ Profile ของตาราง (วันว่าง, ช่องว่าง, คาบเช้า)"""
    # จันทร์ 08:00-10:00 (มีคาบเช้า) และ 15:00-17:00 (ช่องว่างระหว่างคาบ 5 ชม.)
    mask_morning = time_range_to_bitmask(day=0, start_min=480, end_min=600)
    mask_afternoon = time_range_to_bitmask(day=0, start_min=900, end_min=1020)
    total_mask = mask_morning | mask_afternoon

    profile = get_schedule_profile(total_mask)
    assert profile["active_days"] == ["MON"]
    assert "FRI" in profile["free_days"]
    assert profile["has_early_morning"] is True
    assert profile["max_gap_hours"] == 5.0  # 10:00 ถึง 15:00 = 5 ชั่วโมง
