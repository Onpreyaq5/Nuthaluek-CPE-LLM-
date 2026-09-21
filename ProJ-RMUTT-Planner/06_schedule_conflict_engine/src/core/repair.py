"""06_schedule_conflict_engine - Plan Repair Engine
ค้นหา Section ทางเลือกเพื่อซ่อมแซมตารางเรียนที่ชนกัน
"""
from __future__ import annotations

from typing import Any
from ..models.schemas import (
    RepairPlanResponse,
    SectionInput,
)
from .bitmask import check_clash, ensure_section_mask
from .conflict_detector import detect_conflicts


def repair_conflicting_schedule(
    current_sections: list[SectionInput],
    all_available_sections: list[SectionInput],
    term: str = "1/2569",
) -> RepairPlanResponse:
    """วิเคราะห์วิชาที่ชน และค้นหากลุ่มทางเลือก (alternative section) จากวิชาเดียวกันที่ไม่ชนกับวิชาอื่น"""
    conflicts = detect_conflicts(current_sections, term=term)
    if not conflicts:
        return RepairPlanResponse(has_repair=False, suggestions=[])

    # หารายชื่อ Section ที่เกี่ยวข้องกับความขัดแย้ง
    conflicted_sec_ids: set[str] = set()
    for conf in conflicts:
        if conf.code in ("C1", "C2", "C6"):
            conflicted_sec_ids.update(conf.subjects)

    if not conflicted_sec_ids:
        return RepairPlanResponse(has_repair=False, suggestions=[])

    suggestions: list[dict[str, Any]] = []

    # ลองหา section ทดแทนสำหรับแต่ละ section ที่ชน
    for bad_sec_id in conflicted_sec_ids:
        bad_sec = next((s for s in current_sections if s.id == bad_sec_id), None)
        if not bad_sec:
            continue

        # กลุ่มวิชาที่เหลือ (ไม่รวมตัวที่กำลังจะทดแทน)
        other_sections = [s for s in current_sections if s.id != bad_sec_id]

        # ค้นหากลุ่มอื่นของรายวิชาเดียวกันจาก all_available_sections
        candidates = [
            cand for cand in all_available_sections
            if cand.course_code == bad_sec.course_code and cand.id != bad_sec.id
        ]

        valid_alternatives: list[SectionInput] = []
        for cand in candidates:
            # ตรวจสอบที่นั่ง
            if cand.seat_total and cand.seat_taken and cand.seat_taken >= cand.seat_total:
                continue

            # ลองประกอบตารางชั่วคราว
            test_schedule = other_sections + [cand]
            new_conflicts = detect_conflicts(test_schedule, term=term)
            # ถ้าไม่มีความขัดแย้งประเภท C1, C2, C5, C6
            critical_conflicts = [c for c in new_conflicts if c.code in ("C1", "C2", "C5", "C6")]
            if not critical_conflicts:
                valid_alternatives.append(cand)

        for alt in valid_alternatives:
            suggestions.append({
                "action": "change_section",
                "course_code": bad_sec.course_code,
                "from_section": bad_sec.id,
                "to_section": alt.id,
                "reason": f"เปลี่ยนเป็นกลุ่ม {alt.section} จะไม่ชนกับวิชาอื่นในตาราง",
                "seat_available": (alt.seat_total - alt.seat_taken) if (alt.seat_total and alt.seat_taken) else None,
            })

    return RepairPlanResponse(
        has_repair=len(suggestions) > 0,
        suggestions=suggestions,
    )
