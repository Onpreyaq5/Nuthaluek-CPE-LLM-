from __future__ import annotations

from itertools import combinations

from src.schemas.chat import StudentPreferences
from src.schemas.common import hhmm_to_minutes
from src.schemas.courses import Section
from src.schemas.plans import ConflictItem, PlanValidateResponse, ValidateSummary, WarningItem
from src.schemas.students import GeneratedPlan

from ..interfaces import StudentContext
from .data import COURSES, SECTIONS

MAX_CREDITS = 21


def _overlaps(a: Section, b: Section) -> bool:
    for slot_a in a.meetings:
        for slot_b in b.meetings:
            if slot_a.day != slot_b.day:
                continue
            start_a, end_a = hhmm_to_minutes(slot_a.start), hhmm_to_minutes(slot_a.end)
            start_b, end_b = hhmm_to_minutes(slot_b.start), hhmm_to_minutes(slot_b.end)
            if start_a < end_b and start_b < end_a:
                return True
    return False


class MockPlanEngine:
    """ยืนอิงกติกาแบบง่ายของ 06 จริง: C1 เวลาทับ, C3 prereq ไม่ครบ, C4 หน่วยกิตเกิน 21, C6 ที่นั่งเต็ม
    (ยังไม่มีสัญญา field จริงจากทีม 06 — โครง ConflictItem/WarningItem เป็นข้อสันนิษฐาน ดูสรุปท้าย Prompt 3)
    """

    async def validate(
        self, term: str, section_ids: list[str], student: StudentContext
    ) -> PlanValidateResponse:
        sections = [SECTIONS[sid] for sid in section_ids if sid in SECTIONS]
        missing = [sid for sid in section_ids if sid not in SECTIONS]

        conflicts: list[ConflictItem] = []
        warnings: list[WarningItem] = []

        if missing:
            conflicts.append(
                ConflictItem(
                    type="SECTION_NOT_FOUND",
                    message="ไม่พบ section บางรายการ",
                    section_ids=missing,
                )
            )

        for a, b in combinations(sections, 2):
            if _overlaps(a, b):
                conflicts.append(
                    ConflictItem(
                        type="TIME_OVERLAP",
                        message=f"เวลาเรียนของ {a.section_id} และ {b.section_id} ชนกัน",
                        section_ids=[a.section_id, b.section_id],
                    )
                )

        for section in sections:
            course = COURSES.get(section.course_code)
            if not course:
                continue
            missing_prereqs = [p for p in course.prerequisites if p not in student.completed_course_codes]
            if missing_prereqs:
                conflicts.append(
                    ConflictItem(
                        type="PREREQUISITE_MISSING",
                        message=f"{section.course_code} ต้องผ่านวิชา {', '.join(missing_prereqs)} ก่อน",
                        section_ids=[section.section_id],
                        details={"missing_prerequisites": missing_prereqs},
                    )
                )

        total_credits = sum(s.credits for s in sections)
        if total_credits > MAX_CREDITS:
            conflicts.append(
                ConflictItem(
                    type="CREDIT_LIMIT_EXCEEDED",
                    message=f"หน่วยกิตรวม {total_credits} เกินกำหนด {MAX_CREDITS} หน่วยกิต",
                    section_ids=[s.section_id for s in sections],
                    details={"limit": MAX_CREDITS, "total": total_credits},
                )
            )

        for section in sections:
            if section.seats_available <= 0:
                conflicts.append(
                    ConflictItem(
                        type="SEAT_FULL",
                        message=f"{section.section_id} ที่นั่งเต็มแล้ว",
                        section_ids=[section.section_id],
                    )
                )

        summary = ValidateSummary(
            total_credits=total_credits, section_count=len(sections), is_valid=not conflicts
        )
        return PlanValidateResponse(conflicts=conflicts, warnings=warnings, summary=summary)

    async def generate(
        self,
        term: str,
        preferences: StudentPreferences | None,
        student: StudentContext,
        must_include: list[str],
        exclude: list[str],
    ) -> list[GeneratedPlan]:
        prefs = preferences or student.preferences
        free_days = set(prefs.free_days)
        max_credits = prefs.max_credits or MAX_CREDITS

        def is_eligible(section: Section) -> bool:
            course = COURSES[section.course_code]
            missing_prereqs = any(p not in student.completed_course_codes for p in course.prerequisites)
            on_free_day = any(m.day in free_days for m in section.meetings)
            return (
                section.section_id not in exclude
                and section.seats_available > 0
                and not on_free_day
                and not missing_prereqs
            )

        must_have_sections = [SECTIONS[sid] for sid in must_include if sid in SECTIONS]
        pool = [s for s in SECTIONS.values() if is_eligible(s) and s.section_id not in must_include]

        plans: list[GeneratedPlan] = []
        for _ in range(3):
            combo: list[Section] = list(must_have_sections)
            for candidate in pool:
                if any(_overlaps(candidate, chosen) for chosen in combo):
                    continue
                if sum(c.credits for c in combo) + candidate.credits > max_credits:
                    continue
                combo.append(candidate)
            if combo:
                plans.append(
                    GeneratedPlan(
                        sections=[s.section_id for s in combo],
                        total_credits=sum(s.credits for s in combo),
                        relaxed_constraints=[],
                        explanation=None,
                        warnings=[],
                    )
                )
            pool = pool[1:] + pool[:1]  # หมุน pool เพื่อให้รอบถัดไปได้ชุดสลับกัน

        if not plans:
            plans.append(
                GeneratedPlan(
                    sections=[s.section_id for s in must_have_sections],
                    total_credits=sum(s.credits for s in must_have_sections),
                    relaxed_constraints=["no_eligible_sections"],
                    explanation=None,
                    warnings=["ไม่มี section ที่เข้าเงื่อนไขให้จัดแผนเพิ่ม"],
                )
            )
        return plans[:3]
