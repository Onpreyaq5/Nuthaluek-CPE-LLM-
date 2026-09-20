"""Unit tests for Time Slot Model & Bitmask Collision Engine"""
import pytest
from src.time_slot import (
    TOTAL_BITS,
    check_clash,
    decode_overlap,
    meetings_to_bitmask,
    parse_schedule_string,
    time_range_to_bitmask,
)


def test_bitmask_size_and_bounds():
    # 08:00 - 09:00 ในวันจันทร์ (day=0) -> 2 slots (slot 0 และ 1)
    mask = time_range_to_bitmask(0, 8 * 60, 9 * 60)
    assert mask == (1 << 0) | (1 << 1)
    assert mask.bit_length() <= TOTAL_BITS


def test_no_clash_different_time_same_day():
    # จันทร์ 09:00 - 12:00
    mask_a = time_range_to_bitmask(0, 9 * 60, 12 * 60)
    # จันทร์ 13:00 - 16:00
    mask_b = time_range_to_bitmask(0, 13 * 60, 16 * 60)

    assert not check_clash(mask_a, mask_b)
    assert decode_overlap(mask_a, mask_b) == []


def test_no_clash_different_day_same_time():
    # จันทร์ 09:00 - 12:00
    mask_a = time_range_to_bitmask(0, 9 * 60, 12 * 60)
    # อังคาร 09:00 - 12:00
    mask_b = time_range_to_bitmask(1, 9 * 60, 12 * 60)

    assert not check_clash(mask_a, mask_b)
    assert decode_overlap(mask_a, mask_b) == []


def test_clash_detection_and_overlap_decode():
    # จันทร์ 09:00 - 12:00 (540 ถึง 720)
    mask_a = time_range_to_bitmask(0, 540, 720)
    # จันทร์ 10:30 - 13:30 (630 ถึง 810)
    mask_b = time_range_to_bitmask(0, 630, 810)

    assert check_clash(mask_a, mask_b)
    overlaps = decode_overlap(mask_a, mask_b)
    assert len(overlaps) == 1
    assert overlaps[0]["day"] == "MON"
    assert overlaps[0]["overlap_start"] == "10:30"
    assert overlaps[0]["overlap_end"] == "12:00"


def test_parse_schedule_string():
    # ทดสอบการแปลงข้อความภาษาไทย
    slots = parse_schedule_string("จ. 09:00-12:00, พฤ. 13:00 - 16:00")
    assert len(slots) == 2
    assert slots[0].day == 0  # จันทร์
    assert slots[0].start_min == 540
    assert slots[0].end_min == 720
    assert slots[1].day == 3  # พฤหัส
    assert slots[1].start_min == 780
    assert slots[1].end_min == 960


def test_meetings_to_bitmask_multiple():
    meetings = [
        {"day": "จ.", "start_min": "09:00", "end_min": "11:00"},
        {"day": "พุธ", "start_min": "13:00", "end_min": "15:00"},
    ]
    mask = meetings_to_bitmask(meetings)
    assert mask > 0

    # ชนเฉพาะวันจันทร์ 10:00 - 12:00
    mon_clash = time_range_to_bitmask(0, 600, 720)
    assert check_clash(mask, mon_clash)

    # ไม่ชนในวันศุกร์
    fri_mask = time_range_to_bitmask(4, 540, 720)
    assert not check_clash(mask, fri_mask)
