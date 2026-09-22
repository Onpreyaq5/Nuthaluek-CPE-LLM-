"""06_schedule_conflict_engine - Conflict Detector (Hard Rules C1 - C6)
100% Deterministic Rule Engine
"""
from __future__ import annotations

from typing import Any
from ..config import get_settings
from ..models.schemas import (
    ConflictDetail,
    SectionInput,
    StudentContextInput,
)
from .bitmask import (
    check_clash,
    decode_overlap,
    meetings_to_bitmask,
)


def ensure_section_mask(section: SectionInput) -> int:
    """คำนวณและตรวจสอบว่า section มี slots_mask หรือไม่ ถ้าไม่มีให้คำนวณจาก meetings"""
    if section.slots_mask is not None:
        return section.slots_mask
    if section.is_online:
        return 0
    mask = meetings_to_bitmask(section.meetings)
    section.slots_mask = mask
    return mask


def detect_conflicts(
    sections: list[SectionInput],
    term: str = "1/2569",
    student: StudentContextInput | None = None,
) -> list[ConflictDetail]:
    """ตรวจสอบเงื่อนไขความขัดแย้งของตารางเรียนทั้ง 6 รูปแบบ (C1 - C6)
    คืนค่ารายการ ConflictDetail ที่ตรวจพบทั้งหมด
    """
    settings = get_settings()
    conflicts: list[ConflictDetail] = []
    is_summer = "3" in term or "summer" in term.lower()

    # เตรียม Mask ให้กับทุก section
    masks = [ensure_section_mask(sec) for sec in sections]

    # C1: TIME_CLASH (เวลาเรียนชนกัน)
    n = len(sections)
    for i in range(n):
        for j in range(i + 1, n):
            sec_a, sec_b = sections[i], sections[j]
            mask_a, mask_b = masks[i], masks[j]

            if mask_a == 0 or mask_b == 0:
                continue

            if check_clash(mask_a, mask_b):
                overlaps = decode_overlap(mask_a, mask_b)
                for ov in overlaps:
                    conflicts.append(
                        ConflictDetail(
                            code="C1",
                            severity="ERROR",
                            message_key="time_clash",
                            message_th=(
                                f"เวลาเรียนวิชา {sec_a.id} ชนกับ {sec_b.id} "
                                f"วัน{ov['day_th']} เวลา {ov['overlap_start']}-{ov['overlap_end']}"
                            ),
                            message_en=(
                                f"Time clash between {sec_a.id} and {sec_b.id} "
                                f"on {ov['day']} from {ov['overlap_start']} to {ov['overlap_end']}"
                            ),
                            subjects=[sec_a.id, sec_b.id],
                            detail=ov,
                            suggestions=[],
                        )
                    )

    # C2: EXAM_CLASH (เวลาสอบชนกัน ทั้ง Midterm และ Final)
    for i in range(n):
        for j in range(i + 1, n):
            sec_a, sec_b = sections[i], sections[j]
            for ex_a in sec_a.exams:
                for ex_b in sec_b.exams:
                    if ex_a.exam_type == ex_b.exam_type and ex_a.exam_date == ex_b.exam_date:
                        # ตรวจสอบช่วงเวลาสอบทับซ้อน
                        start_ov = max(ex_a.start_min, ex_b.start_min)
                        end_ov = min(ex_a.end_min, ex_b.end_min)
                        if start_ov < end_ov:
                            exam_type_th = "กลางภาค" if ex_a.exam_type == "midterm" else "ปลายภาค"
                            s_str = f"{start_ov // 60:02d}:{start_ov % 60:02d}"
                            e_str = f"{end_ov // 60:02d}:{end_ov % 60:02d}"
                            conflicts.append(
                                ConflictDetail(
                                    code="C2",
                                    severity="ERROR",
                                    message_key="exam_clash",
                                    message_th=(
                                        f"เวลาสอบ{exam_type_th}วิชา {sec_a.id} ชนกับ {sec_b.id} "
                                        f"วันที่ {ex_a.exam_date} เวลา {s_str}-{e_str}"
                                    ),
                                    message_en=(
                                        f"{ex_a.exam_type.capitalize()} exam clash between {sec_a.id} and {sec_b.id} "
                                        f"on {ex_a.exam_date} at {s_str}-{e_str}"
                                    ),
                                    subjects=[sec_a.id, sec_b.id],
                                    detail={
                                        "exam_type": ex_a.exam_type,
                                        "exam_date": ex_a.exam_date,
                                        "overlap_start": s_str,
                                        "overlap_end": e_str,
                                    },
                                )
                            )

    # C3: PREREQ_FAIL (ยังไม่ผ่านวิชาบังคับก่อน)
    passed_courses = set(student.passed_courses) if student else set()
    for sec in sections:
        for prereq in sec.prerequisites:
            prereq_clean = prereq.strip()
            if student and prereq_clean not in passed_courses:
                conflicts.append(
                    ConflictDetail(
                        code="C3",
                        severity="ERROR",
                        message_key="prereq_fail",
                        message_th=f"ยังไม่ผ่านวิชาบังคับก่อน ({prereq_clean}) ของวิชา {sec.course_code}",
                        message_en=f"Prerequisite course {prereq_clean} not satisfied for {sec.course_code}",
                        subjects=[sec.id],
                        detail={"course_code": sec.course_code, "missing_prereq": prereq_clean},
                    )
                )

    # C4: CREDIT_LIMIT (หน่วยกิตเกินเพดาน หรือต่ำกว่าเกณฑ์)
    total_credits = sum(sec.credits for sec in sections)
    max_credits = settings.summer_max_credits if is_summer else settings.default_max_credits
    min_credits = 1 if is_summer else settings.default_min_credits

    if total_credits > max_credits:
        conflicts.append(
            ConflictDetail(
                code="C4",
                severity="ERROR",
                message_key="credit_limit_exceeded",
                message_th=f"หน่วยกิตรวม ({total_credits}) เกินเพดานสูงสุดที่กำหนด ({max_credits} หน่วยกิต)",
                message_en=f"Total credits ({total_credits}) exceeds maximum limit ({max_credits})",
                subjects=[s.id for s in sections],
                detail={"total_credits": total_credits, "max_credits": max_credits},
            )
        )
    elif total_credits < min_credits and len(sections) > 0:
        conflicts.append(
            ConflictDetail(
                code="C4",
                severity="WARNING",
                message_key="credit_limit_under",
                message_th=f"หน่วยกิตรวม ({total_credits}) ต่ำกว่าเกณฑ์ขั้นต่ำของมหาวิทยาลัย ({min_credits} หน่วยกิต)",
                message_en=f"Total credits ({total_credits}) is below minimum limit ({min_credits})",
                subjects=[s.id for s in sections],
                detail={"total_credits": total_credits, "min_credits": min_credits},
            )
        )

    # C5: DUPLICATE (ลงวิชาเดิมซ้ำ / ลง 2 กลุ่มในวิชาเดียวกัน)
    course_counts: dict[str, list[str]] = {}
    for sec in sections:
        course_counts.setdefault(sec.course_code, []).append(sec.id)

    for c_code, sec_ids in course_counts.items():
        if len(sec_ids) > 1:
            conflicts.append(
                ConflictDetail(
                    code="C5",
                    severity="ERROR",
                    message_key="duplicate_section",
                    message_th=f"ลงทะเบียนวิชาเดียวกันซ้ำกันมากกว่าหนึ่งกลุ่ม: {c_code} ({', '.join(sec_ids)})",
                    message_en=f"Multiple sections selected for same course: {c_code} ({', '.join(sec_ids)})",
                    subjects=sec_ids,
                    detail={"course_code": c_code, "sections": sec_ids},
                )
            )
        if student and c_code in passed_courses:
            conflicts.append(
                ConflictDetail(
                    code="C5",
                    severity="ERROR",
                    message_key="already_passed",
                    message_th=f"เคยสอบผ่านรายวิชา {c_code} แล้ว ไม่สามารถลงทะเบียนซ้ำได้",
                    message_en=f"Course {c_code} already passed in previous term",
                    subjects=sec_ids,
                    detail={"course_code": c_code},
                )
            )

    # C6: SEAT_FULL (ที่นั่งในกลุ่มเต็ม)
    for sec in sections:
        if sec.seat_total is not None and sec.seat_taken is not None:
            if sec.seat_taken >= sec.seat_total:
                conflicts.append(
                    ConflictDetail(
                        code="C6",
                        severity="ERROR",
                        message_key="seat_full",
                        message_th=f"ที่นั่งในกลุ่ม {sec.id} เต็มแล้ว ({sec.seat_taken}/{sec.seat_total} ที่นั่ง)",
                        message_en=f"Section {sec.id} is full ({sec.seat_taken}/{sec.seat_total} seats)",
                        subjects=[sec.id],
                        detail={"seat_taken": sec.seat_taken, "seat_total": sec.seat_total},
                    )
                )

    return conflicts
