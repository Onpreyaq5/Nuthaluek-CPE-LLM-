"""06_schedule_conflict_engine - FastAPI Endpoints
Separates contracts for 02_api_backend and 03_ai_router_agent cleanly
"""
from __future__ import annotations

from typing import Any
from fastapi import APIRouter, Depends, HTTPException, status
from ..adapters.course_data import HttpSectionProvider
from ..adapters.providers import (
    DataIncompleteError,
    SectionNotFoundError,
    SectionProvider,
    StudentContextNotFoundError,
    StudentContextProvider,
    UpstreamServiceError,
)
from ..adapters.student_data import HttpStudentContextProvider
from ..config import get_settings
from ..core.bitmask import check_clash, decode_overlap, ensure_section_mask
from ..models.schemas import (
    GeneratePlanRequest,
    GeneratePlanResponse,
    SectionInput,
    StudentContextInput,
    StudentPreferences,
)
from ..services.planning_service import (
    map_plans_for_backend,
    map_plans_for_router,
    run_planning,
)
from ..services.validation_service import (
    map_validation_for_backend,
    map_validation_for_router,
    run_validation,
)
from .schemas_backend import (
    BackendGenerateRequest,
    BackendGenerateResponse,
    BackendValidateRequest,
    BackendValidateResponse,
)
from .schemas_router import (
    RouterAutoPlanRequest,
    RouterCheckConflictsRequest,
    RouterConflictResponse,
    RouterGenerateResponse,
)

router = APIRouter()

# Dependency Providers
_section_provider: SectionProvider | None = None
_student_provider: StudentContextProvider | None = None


def get_section_provider() -> SectionProvider:
    global _section_provider
    if _section_provider is None:
        _section_provider = HttpSectionProvider()
    return _section_provider


def get_student_provider() -> StudentContextProvider:
    global _student_provider
    if _student_provider is None:
        _student_provider = HttpStudentContextProvider()
    return _student_provider


def set_test_providers(
    section_provider: SectionProvider | None = None,
    student_provider: StudentContextProvider | None = None,
) -> None:
    """Helper สำหรับ inject memory providers ระหว่างการรัน Unit/Contract Tests"""
    global _section_provider, _student_provider
    if section_provider is not None:
        _section_provider = section_provider
    if student_provider is not None:
        _student_provider = student_provider


# =====================================================================
# 1. Endpoints สำหรับ 02_api_backend (Strict Schema Mirror)
# =====================================================================

@router.post("/validate", response_model=BackendValidateResponse)
async def validate_for_backend(
    req: BackendValidateRequest,
    provider: SectionProvider = Depends(get_section_provider),
) -> BackendValidateResponse:
    """Endpoint สำหรับโมดูล 02: ตรวจสอบความถูกต้องของแผนการเรียน
    คืนค่าที่ validate ผ่าน Pydantic Schema ของ 02 (PlanValidateResponse) 100%
    """
    try:
        # แปลง Student Context จาก 02
        student_input: StudentContextInput | None = None
        pref_input: StudentPreferences | None = None

        if req.student:
            student_input = StudentContextInput(
                student_id=req.student.student_id or req.student.id_hash or "unknown",
                passed_courses=req.student.completed_course_codes,
                gpax=req.student.gpax,
            )
            if req.student.preferences:
                pref_input = StudentPreferences(
                    free_days=req.student.preferences.free_days,
                    avoid_morning=req.student.preferences.no_early_class,
                    max_credits=req.student.preferences.max_credits,
                )

        result = await run_validation(
            section_ids=req.section_ids,
            term=req.term,
            section_provider=provider,
            student=student_input,
            preferences=pref_input,
        )
        return map_validation_for_backend(result)

    except SectionNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={"code": "SECTION_NOT_FOUND", "message": str(exc), "section_id": exc.section_id},
        )
    except DataIncompleteError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={"code": "DATA_INCOMPLETE", "message": str(exc), "section_id": exc.section_id},
        )
    except UpstreamServiceError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail={"code": "UPSTREAM_ERROR", "service": exc.service, "message": str(exc)},
        )


@router.post("/generate", response_model=BackendGenerateResponse)
async def generate_for_backend(
    req: BackendGenerateRequest,
    provider: SectionProvider = Depends(get_section_provider),
) -> BackendGenerateResponse:
    """Endpoint สำหรับโมดูล 02: สร้างแผนการเรียนอัตโนมัติ
    คืนค่าเฉพาะ field ที่กำหนดใน GeneratedPlan ของ 02 (sections เป็น string IDs เท่านั้น)
    """
    try:
        student_input: StudentContextInput | None = None
        pref_input: StudentPreferences | None = None

        if req.student:
            student_input = StudentContextInput(
                student_id=req.student.student_id or req.student.id_hash or "unknown",
                passed_courses=req.student.completed_course_codes,
                gpax=req.student.gpax,
            )

        if req.preferences:
            pref_input = StudentPreferences(
                free_days=req.preferences.free_days,
                avoid_morning=req.preferences.no_early_class,
                max_credits=req.preferences.max_credits,
            )

        plan_res = await run_planning(
            term=req.term,
            section_provider=provider,
            preferences=pref_input,
            student=student_input,
            must_include=req.must_include,
            exclude=req.exclude,
        )
        return map_plans_for_backend(plan_res)

    except UpstreamServiceError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail={"code": "UPSTREAM_ERROR", "service": exc.service, "message": str(exc)},
        )


# =====================================================================
# 2. Endpoints สำหรับ 03_ai_router_agent (Tool Orchestration)
# =====================================================================

@router.post("/conflicts/check", response_model=RouterConflictResponse)
async def check_for_router(
    req: RouterCheckConflictsRequest,
    section_provider: SectionProvider = Depends(get_section_provider),
    student_provider: StudentContextProvider = Depends(get_student_provider),
) -> RouterConflictResponse:
    """Endpoint สำหรับโมดูล 03: Tool check_conflicts
    ตรวจจับข้อขัดแย้งจาก section IDs จริง พร้อมคืน Rich Response
    """
    try:
        student_input: StudentContextInput | None = None
        if req.student_id:
            try:
                student_input = await student_provider.get_context(req.student_id)
            except StudentContextNotFoundError:
                # ส่ง error ชัดเจน ห้ามเดาหรือสร้าง mock
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail={"code": "STUDENT_NOT_FOUND", "message": f"Student identifier '{req.student_id}' not found"},
                )

        result = await run_validation(
            section_ids=req.sections,
            term=req.term,
            section_provider=section_provider,
            student=student_input,
        )
        return map_validation_for_router(result)

    except SectionNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={"code": "SECTION_NOT_FOUND", "message": str(exc), "section_id": exc.section_id},
        )
    except DataIncompleteError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={"code": "DATA_INCOMPLETE", "message": str(exc), "section_id": exc.section_id},
        )
    except UpstreamServiceError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail={"code": "UPSTREAM_ERROR", "service": exc.service, "message": str(exc)},
        )


@router.post("/plans/auto", response_model=RouterGenerateResponse)
async def auto_plan_for_router(
    req: RouterAutoPlanRequest,
    section_provider: SectionProvider = Depends(get_section_provider),
    student_provider: StudentContextProvider = Depends(get_student_provider),
) -> RouterGenerateResponse:
    """Endpoint สำหรับโมดูล 03: Tool generate_plan
    จัดตารางอัตโนมัติโดยใช้ student hash และ preferences จริง
    """
    try:
        student_input = await student_provider.get_context(req.student_id)
    except StudentContextNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={"code": "STUDENT_NOT_FOUND", "message": f"Student identifier '{req.student_id}' not found"},
        )
    except UpstreamServiceError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail={"code": "UPSTREAM_ERROR", "service": exc.service, "message": str(exc)},
        )

    pref_input: StudentPreferences | None = None
    if req.preferences:
        pref_input = StudentPreferences(
            free_days=req.preferences.free_days,
            avoid_morning=req.preferences.no_early_class or req.preferences.avoid_morning,
            max_credits=req.preferences.max_credits,
            min_credits=req.preferences.min_credits,
        )

    try:
        plan_res = await run_planning(
            term=req.term,
            section_provider=section_provider,
            preferences=pref_input,
            student=student_input,
        )
        return map_plans_for_router(plan_res)
    except UpstreamServiceError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail={"code": "UPSTREAM_ERROR", "service": exc.service, "message": str(exc)},
        )


# =====================================================================
# 3. Fast Preview & Internal Endpoints
# =====================================================================

@router.post("/conflicts/preview")
def preview_conflict_endpoint(payload: dict[str, Any]) -> dict[str, Any]:
    """ตรวจสอบตารางชนแบบรวดเร็วพิเศษ (< 50ms) สำหรับการลากวาง (Drag & Drop) ใน 01_web_app
    รับ payload ที่มี section objects พร้อม meetings โดยตรง
    """
    raw_sections = payload.get("sections") or []
    sections: list[SectionInput] = []
    for s in raw_sections:
        if isinstance(s, dict):
            sec = SectionInput.model_validate(s)
            ensure_section_mask(sec)
            sections.append(sec)

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
async def generate_plan_internal(
    req: GeneratePlanRequest,
    provider: SectionProvider = Depends(get_section_provider),
) -> GeneratePlanResponse:
    """Internal Rich Planning Endpoint สำหรับทดสอบหรือเรียกใช้ภายใน 06"""
    plan_res = await run_planning(
        term=req.term,
        section_provider=provider,
        preferences=req.preferences,
        student=req.student,
        must_include=req.must_include,
        exclude=req.exclude,
        available_sections=req.available_sections,
    )
    return plan_res
