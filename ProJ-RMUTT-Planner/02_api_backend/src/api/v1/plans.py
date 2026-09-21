from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from src.adapters import get_course_catalog, get_explainer, get_plan_engine, get_student_data
from src.adapters.interfaces import CourseCatalog, Explainer, PlanEngine, StudentData
from src.api.deps import CurrentUser, current_user
from src.core.db import get_db
from src.core.envelope import success_envelope
from src.core.log_queue import get_log_queue
from src.core.pagination import decode_cursor, encode_cursor
from src.repositories import student_repository
from src.schemas.chat import StudentPreferences
from src.schemas.envelope import SuccessEnvelope
from src.schemas.plans import (
    PlanCreateRequest,
    PlanCreateResponse,
    PlanDetail,
    PlanListResponse,
    PlanSummary,
    PlanValidateRequest,
    PlanValidateResponse,
)
from src.schemas.students import AutoPlanRequest, AutoPlanResponse, ExplainResponse
from src.services import plan_service

router = APIRouter(prefix="/plans", tags=["plans"])


@router.post("/validate", response_model=SuccessEnvelope[PlanValidateResponse])
async def validate_plan(
    payload: PlanValidateRequest,
    user: CurrentUser = Depends(current_user),
    catalog: CourseCatalog = Depends(get_course_catalog),
    student_data: StudentData = Depends(get_student_data),
    plan_engine: PlanEngine = Depends(get_plan_engine),
) -> dict:
    result = await plan_service.validate_plan(
        term=payload.term,
        section_ids=payload.section_ids,
        student_id=user.student_id,
        catalog=catalog,
        student_data=student_data,
        plan_engine=plan_engine,
    )
    get_log_queue().enqueue(
        {
            "event": "plan_validate",
            "id_hash": user.id_hash,
            "term": payload.term,
            "section_count": len(payload.section_ids),
            "is_valid": result.summary.is_valid,
        }
    )
    return success_envelope(result.model_dump(mode="json"))


@router.post("/auto", response_model=SuccessEnvelope[AutoPlanResponse])
async def auto_plan(
    payload: AutoPlanRequest,
    user: CurrentUser = Depends(current_user),
    db: AsyncSession = Depends(get_db),
    student_data: StudentData = Depends(get_student_data),
    plan_engine: PlanEngine = Depends(get_plan_engine),
    explainer: Explainer = Depends(get_explainer),
) -> dict:
    # ไม่ใช้ payload.preferences เลย ตาม Prompt 9 ("ไม่ส่ง preferences ใช้ของ DB") — ยึด
    # student_preferences ในฐานข้อมูลของ 02 เองเสมอ
    stored_preferences = await student_repository.get_preferences_by_student_id(db, user.student_id)
    preferences = (
        StudentPreferences(
            free_days=stored_preferences.free_days,
            no_early_class=stored_preferences.no_early_class,
            max_credits=stored_preferences.max_credits,
        )
        if stored_preferences is not None
        else StudentPreferences()
    )

    plans = await plan_service.generate_auto_plans(
        term=payload.term,
        must_include=payload.must_include,
        exclude=payload.exclude,
        student_id=user.student_id,
        preferences=preferences,
        student_data=student_data,
        plan_engine=plan_engine,
        explainer=explainer,
    )
    get_log_queue().enqueue(
        {"event": "plan_auto", "id_hash": user.id_hash, "term": payload.term, "plan_count": len(plans)}
    )
    data = AutoPlanResponse(plans=plans)
    return success_envelope(data.model_dump(mode="json"))


@router.post("", response_model=SuccessEnvelope[PlanCreateResponse])
async def create_plan(
    payload: PlanCreateRequest,
    user: CurrentUser = Depends(current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    plan = await plan_service.create_plan(
        db,
        student_id=user.student_id,
        term=payload.term,
        name=payload.name,
        section_ids=payload.section_ids,
    )
    data = PlanCreateResponse(plan_id=plan.id)
    return success_envelope(data.model_dump())


@router.get("", response_model=SuccessEnvelope[PlanListResponse])
async def list_plans(
    term: str | None = None,
    cursor: str | None = None,
    limit: int = 20,
    user: CurrentUser = Depends(current_user),
    db: AsyncSession = Depends(get_db),
    catalog: CourseCatalog = Depends(get_course_catalog),
) -> dict:
    offset = decode_cursor(cursor)
    summaries, total = await plan_service.list_plans(
        db, student_id=user.student_id, term=term, offset=offset, limit=limit, catalog=catalog
    )
    next_offset = offset + limit
    next_cursor = encode_cursor(next_offset) if next_offset < total else None
    data = PlanListResponse(
        items=[PlanSummary(**summary) for summary in summaries], next_cursor=next_cursor
    )
    return success_envelope(data.model_dump(mode="json"))


@router.get("/{plan_id}", response_model=SuccessEnvelope[PlanDetail])
async def get_plan(
    plan_id: int,
    user: CurrentUser = Depends(current_user),
    db: AsyncSession = Depends(get_db),
    catalog: CourseCatalog = Depends(get_course_catalog),
) -> dict:
    detail = await plan_service.get_plan_detail(
        db, plan_id=plan_id, student_id=user.student_id, catalog=catalog
    )
    data = PlanDetail(**detail)
    return success_envelope(data.model_dump(mode="json"))


@router.delete("/{plan_id}", response_model=SuccessEnvelope[dict])
async def delete_plan(
    plan_id: int, user: CurrentUser = Depends(current_user), db: AsyncSession = Depends(get_db)
) -> dict:
    await plan_service.delete_plan(db, plan_id=plan_id, student_id=user.student_id)
    return success_envelope({})


@router.get("/{plan_id}/explain", response_model=SuccessEnvelope[ExplainResponse])
async def explain_plan(
    plan_id: int,
    user: CurrentUser = Depends(current_user),
    db: AsyncSession = Depends(get_db),
    student_data: StudentData = Depends(get_student_data),
    explainer: Explainer = Depends(get_explainer),
) -> dict:
    data = await plan_service.explain_plan(
        db, plan_id=plan_id, student_id=user.student_id, student_data=student_data, explainer=explainer
    )
    return success_envelope(data.model_dump(mode="json"))
