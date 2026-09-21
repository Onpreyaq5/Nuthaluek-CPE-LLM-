"""06_schedule_conflict_engine - FastAPI Endpoints
รองรับทั้งสัญญากลางของโมดูล 06, 02_api_backend และ 03_ai_router_agent
"""
from __future__ import annotations

from typing import Any
from fastapi import APIRouter, Body, HTTPException
from ..config import get_settings
from ..core.bitmask import check_clash, decode_overlap, ensure_section_mask, get_schedule_profile
from ..core.conflict_detector import detect_conflicts
from ..core.planner import generate_schedule_plans
from ..core.quality_evaluator import evaluate_quality
from ..core.repair import repair_conflicting_schedule
from ..models.schemas import (
    CheckConflictsRequest,
    CheckConflictsResponse,
    ComparePlansRequest,
    ComparePlansResponse,
    ConflictDetail,
    GeneratePlanRequest,
    GeneratePlanResponse,
    RepairPlanRequest,
    RepairPlanResponse,
    SectionInput,
    StudentContextInput,
    ValidationSummary,
)

router = APIRouter()


def _normalize_sections_input(raw_sections: list[Any]) -> list[SectionInput]:
    """แปลงรายการ sections ให้เป็น list[SectionInput] อย่างปลอดภัย"""
    parsed: list[SectionInput] = []
    for s in raw_sections:
        if isinstance(s, SectionInput):
            ensure_section_mask(s)
            parsed.append(s)
        elif isinstance(s, dict):
            sec = SectionInput.model_validate(s)
            ensure_section_mask(sec)
            parsed.append(sec)
        elif isinstance(s, str):
            # กรณีส่งมาเป็น string ID เช่น "CPE101-01" หรือ "01"
            parts = s.split("-")
            c_code = parts[0] if len(parts) > 1 else s
            sec_num = parts[1] if len(parts) > 1 else "01"
            sec = SectionInput(
                id=s,
                course_code=c_code,
                section=sec_num,
                credits=3,
                meetings=[],
            )
            parsed.append(sec)
    return parsed


@router.post("/conflicts/check", response_model=CheckConflictsResponse)
@router.post("/validate", response_model=CheckConflictsResponse)
def check_conflicts_endpoint(payload: dict[str, Any] = Body(...)) -> CheckConflictsResponse:
    """ตรวจสอบข้อขัดแย้งของตารางเรียน (C1-C6 และ W1-W5)
    รองรับทั้ง Request จาก 01, 02 (/validate) และ 03 (/conflicts/check)
    """
    term = payload.get("term", "1/2569")
    raw_sections = payload.get("sections") or payload.get("section_ids") or []
    sections = _normalize_sections_input(raw_sections)

    # student context
    raw_student = payload.get("student")
    student: StudentContextInput | None = None
    if isinstance(raw_student, dict):
        student = StudentContextInput.model_validate(raw_student)
    elif payload.get("student_id"):
        student = StudentContextInput(student_id=str(payload.get("student_id")))

    # ตรวจสอบ Hard Conflicts (C1 - C6)
    conflicts = detect_conflicts(sections, term=term, student=student)

    # ประเมิน Soft Rules (W1 - W5)
    raw_pref = payload.get("preferences")
    pref = None
    if isinstance(raw_pref, dict):
        from ..models.schemas import StudentPreferences
        pref = StudentPreferences.model_validate(raw_pref)

    warnings, profile = evaluate_quality(sections, preferences=pref)

    total_cr = sum(s.credits for s in sections)
    has_err = any(c.severity == "ERROR" for c in conflicts)

    summary = ValidationSummary(
        total_credits=total_cr,
        section_count=len(sections),
        is_valid=(not has_err),
        days_on_campus=profile.get("days_on_campus", 0),
        free_days=profile.get("free_days", []),
    )

    return CheckConflictsResponse(
        has_conflict=len(conflicts) > 0,
        conflicts=conflicts,
        warnings=warnings,
        summary=summary,
    )


@router.post("/conflicts/preview")
def preview_conflict_endpoint(payload: dict[str, Any] = Body(...)) -> dict[str, Any]:
    """ตรวจสอบตารางชนแบบรวดเร็วพิเศษ (< 50ms) สำหรับการลากวาง (Drag & Drop) ใน 01_web_app"""
    raw_sections = payload.get("sections") or []
    sections = _normalize_sections_input(raw_sections)

    # ตรวจสอบเฉพาะ Bitmask Clash อย่างรวดเร็ว
    masks = [ensure_section_mask(s) for s in sections]
    n = len(sections)
    clashes = []

    for i in range(n):
        for j in range(i + 1, n):
            if masks[i] != 0 and masks[j] != 0 and check_clash(masks[i], masks[j]):
                overlaps = decode_overlap(masks[i], masks[j])
                clashes.append({
                    "subject_a": sections[i].id,
                    "subject_b": sections[j].id,
                    "overlaps": overlaps,
                })

    return {
        "has_clash": len(clashes) > 0,
        "clash_count": len(clashes),
        "clashes": clashes,
    }


@router.post("/plan/generate", response_model=GeneratePlanResponse)
@router.post("/plans/auto", response_model=GeneratePlanResponse)
@router.post("/generate", response_model=GeneratePlanResponse)
def generate_plan_endpoint(payload: dict[str, Any] = Body(...)) -> GeneratePlanResponse:
    """จัดตารางเรียนอัตโนมัติด้วย Google OR-Tools CP-SAT Solver
    สร้าง 3 - 5 แผนการเรียนทางเลือก พร้อมรองรับการคลายเงื่อนไข (Relaxation)
    """
    settings = get_settings()
    term = payload.get("term", "1/2569")
    must_include = payload.get("must_include") or []
    exclude = payload.get("exclude") or []

    # Student context
    raw_student = payload.get("student")
    student: StudentContextInput | None = None
    if isinstance(raw_student, dict):
        student = StudentContextInput.model_validate(raw_student)
    elif payload.get("student_id"):
        student = StudentContextInput(student_id=str(payload.get("student_id")))

    # Preferences
    raw_pref = payload.get("preferences")
    pref = None
    if isinstance(raw_pref, dict):
        from ..models.schemas import StudentPreferences
        pref = StudentPreferences.model_validate(raw_pref)

    # Available sections
    raw_avail = payload.get("available_sections") or []
    available_sections = _normalize_sections_input(raw_avail)

    # หากไม่มี available_sections ส่งมาใน payload ให้สร้าง Mock สำหรับ Demonstration/Testing
    if not available_sections:
        # Mock sample sections สำหรับเทอมปกติ เพื่อให้ endpoint ใช้งานได้ทันที
        available_sections = _generate_mock_sections_for_demo()

    response = generate_schedule_plans(
        available_sections=available_sections,
        term=term,
        preferences=pref,
        student=student,
        must_include=must_include,
        exclude=exclude,
        max_candidates=settings.max_plan_candidates,
    )

    return response


@router.post("/plan/repair", response_model=RepairPlanResponse)
def repair_plan_endpoint(payload: dict[str, Any] = Body(...)) -> RepairPlanResponse:
    """วิเคราะห์แผนที่ชนและเสนอทางเลือกในการเปลี่ยน Section"""
    term = payload.get("term", "1/2569")
    current_secs = _normalize_sections_input(payload.get("sections") or [])
    all_avail = _normalize_sections_input(payload.get("all_available_sections") or [])

    if not all_avail:
        all_avail = _generate_mock_sections_for_demo()

    return repair_conflicting_schedule(
        current_sections=current_secs,
        all_available_sections=all_avail,
        term=term,
    )


@router.post("/plan/compare", response_model=ComparePlansResponse)
def compare_plans_endpoint(payload: dict[str, Any] = Body(...)) -> ComparePlansResponse:
    """เปรียบเทียบตารางเรียน 2 แผน (Plan A vs Plan B)"""
    plan_a = _normalize_sections_input(payload.get("plan_a") or [])
    plan_b = _normalize_sections_input(payload.get("plan_b") or [])

    tot_cr_a = sum(s.credits for s in plan_a)
    tot_cr_b = sum(s.credits for s in plan_b)

    mask_a = 0
    for s in plan_a:
        mask_a |= ensure_section_mask(s)
    mask_b = 0
    for s in plan_b:
        mask_b |= ensure_section_mask(s)

    prof_a = get_schedule_profile(mask_a)
    prof_b = get_schedule_profile(mask_b)

    conf_a = detect_conflicts(plan_a)
    conf_b = detect_conflicts(plan_b)

    notes = []
    if tot_cr_a != tot_cr_b:
        notes.append(f"แผน A มี {tot_cr_a} หน่วยกิต ส่วนแผน B มี {tot_cr_b} หน่วยกิต")
    if prof_a["days_on_campus"] != prof_b["days_on_campus"]:
        notes.append(
            f"แผน A ต้องมาเรียน {prof_a['days_on_campus']} วัน ส่วนแผน B มาเรียน {prof_b['days_on_campus']} วัน"
        )
    if len(prof_a["free_days"]) != len(prof_b["free_days"]):
        notes.append(
            f"แผน A มีวันว่าง {len(prof_a['free_days'])} วัน ส่วนแผน B มีวันว่าง {len(prof_b['free_days'])} วัน"
        )

    return ComparePlansResponse(
        credits_a=tot_cr_a,
        credits_b=tot_cr_b,
        days_a=prof_a["days_on_campus"],
        days_b=prof_b["days_on_campus"],
        free_days_a=prof_a["free_days"],
        free_days_b=prof_b["free_days"],
        overlap_a=any(c.code == "C1" for c in conf_a),
        overlap_b=any(c.code == "C1" for c in conf_b),
        comparison_notes=notes,
    )


def _generate_mock_sections_for_demo() -> list[SectionInput]:
    """สร้างรายการตัวอย่างรายวิชาที่ครอบคลุมสำหรับทดสอบและการรันตัวอย่าง"""
    from ..models.schemas import Meeting
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
