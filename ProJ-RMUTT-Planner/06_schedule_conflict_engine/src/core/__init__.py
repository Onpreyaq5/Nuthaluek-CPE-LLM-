"""Core engine package"""
from .bitmask import (
    TOTAL_BITS,
    SLOTS_PER_DAY,
    TOTAL_DAYS,
    DAY_NAMES,
    DAY_NAMES_TH,
    time_range_to_bitmask,
    meetings_to_bitmask,
    check_clash,
    decode_overlap,
    get_schedule_profile,
)

__all__ = [
    "TOTAL_BITS",
    "SLOTS_PER_DAY",
    "TOTAL_DAYS",
    "DAY_NAMES",
    "DAY_NAMES_TH",
    "time_range_to_bitmask",
    "meetings_to_bitmask",
    "check_clash",
    "decode_overlap",
    "get_schedule_profile",
    "ensure_section_mask",
]
