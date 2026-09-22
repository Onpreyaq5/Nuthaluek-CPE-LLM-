from __future__ import annotations

from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from src.adapters.interfaces import CourseCatalog, Explainer, PlanEngine, StudentData
from src.core.errors import Conflict409Error, Forbidden403Error, NotFound404Error, Upstream502Error
from src.models import Plan
from src.repositories import plan_repository
from src.schemas.chat import StudentPreferences
from src.schemas.plans import PlanValidateResponse
from src.schemas.students import GeneratedPlan

_DUPLICATE_NAME_MESSAGE = "มีแผนชื่อนี้อยู่แล้วในภาคการศึกษานี้"
_PLAN_NOT_FOUND_MESSAGE = "ไม่พบแผนนี้"
_PLAN_FORBIDDEN_MESSAGE = "ไม่มีสิทธิ์เข้าถึงแผนนี้"
_EXPLAIN_UNAVAILABLE_WARNING = "ไม่สามารถอธิบายแผนนี้ได้ในขณะนี้ (โมดูล 07 ไม่ตอบสนอง)"


def _ensure_owner_or_raise(plan: Plan, student_id: str) -> None:
    if plan.student_id != student_id:
        raise Forbidden403Error(_PLAN_FORBIDDEN_MESSAGE, details={"plan_id": plan.id})


async def _get_owned_plan(db: AsyncSession, *, plan_id: int, student_id: str) -> Plan:
    plan = await plan_repository.get_by_id(db, plan_id)
    if plan is None:
        raise NotFound404Error(_PLAN_NOT_FOUND_MESSAGE, details={"plan_id": plan_id})
    _ensure_owner_or_raise(plan, student_id)
    return plan


async def validate_plan(
    *,
    term: str,
    section_ids: list[str],
    student_id: str,
    catalog: CourseCatalog,
    student_data: StudentData,
    plan_engine: PlanEngine,
) -> PlanValidateResponse:
    await catalog.get_sections_by_ids(section_ids)  # raise NotFound404Error ถ้ามี id ไม่มีจริง
    student = await student_data.get_context(student_id)
    return await plan_engine.validate(term, section_ids, student)


async def create_plan(
    db: AsyncSession, *, student_id: str, term: str, name: str, section_ids: list[str]
) -> Plan:
    existing = await plan_repository.get_by_student_term_name(
        db, student_id=student_id, term=term, name=name
    )
    if existing is not None:
        raise Conflict409Error(_DUPLICATE_NAME_MESSAGE, details={"term": term, "name": name})
    return await plan_repository.create_with_items(
        db, student_id=student_id, term=term, name=name, section_ids=section_ids
    )


async def list_plans(
    db: AsyncSession,
    *,
    student_id: str,
    term: str | None,
    offset: int,
    limit: int,
    catalog: CourseCatalog,
) -> tuple[list[dict[str, Any]], int]:
    plans, total = await plan_repository.list_by_student(
        db, student_id=student_id, term=term, offset=offset, limit=limit
    )

    summaries: list[dict[str, Any]] = []
    for plan in plans:
        section_ids = [item.section_id for item in plan.items]
        total_credits = 0
        if section_ids:
            sections = await catalog.get_sections_by_ids(section_ids)
            total_credits = sum(s.credits for s in sections)
        summaries.append(
            {
                "id": plan.id,
                "term": plan.term,
                "name": plan.name,
                "total_credits": total_credits,
                "updated_at": plan.updated_at,
            }
        )
    return summaries, total


async def get_plan_detail(
    db: AsyncSession, *, plan_id: int, student_id: str, catalog: CourseCatalog
) -> dict[str, Any]:
    plan = await _get_owned_plan(db, plan_id=plan_id, student_id=student_id)

    section_ids = [item.section_id for item in plan.items]
    sections = await catalog.get_sections_by_ids(section_ids) if section_ids else []
    return {
        "id": plan.id,
        "term": plan.term,
        "name": plan.name,
        "sections": sections,
        "last_validation": plan.last_validation,
    }


async def delete_plan(db: AsyncSession, *, plan_id: int, student_id: str) -> None:
    plan = await _get_owned_plan(db, plan_id=plan_id, student_id=student_id)
    await plan_repository.delete(db, plan)


async def generate_auto_plans(
    *,
    term: str,
    must_include: list[str],
    exclude: list[str],
    student_id: str,
    preferences: StudentPreferences,
    student_data: StudentData,
    plan_engine: PlanEngine,
    explainer: Explainer,
) -> list[GeneratedPlan]:
    """05 context -> 06 generate -> 07 explain ทีละแผน ไม่ส่ง preferences จาก request ใช้ของ DB เสมอ
    (payload.preferences ถูก caller ทิ้งไปแล้วก่อนเรียกฟังก์ชันนี้) · 07 ล่ม -> explanation=null + warning
    ไม่ retry (ตาราง 3.3 กำหนด write timeout ไว้ที่ retries=0 อยู่แล้ว) ไม่ล้มทั้ง request
    """
    student = await student_data.get_context(student_id)
    plans = await plan_engine.generate(term, preferences, student, must_include, exclude)

    explained: list[GeneratedPlan] = []
    for plan in plans:
        try:
            explanation = await explainer.explain_plan(term, plan.sections, student)
        except Upstream502Error:
            explained.append(
                plan.model_copy(
                    update={"explanation": None, "warnings": [*plan.warnings, _EXPLAIN_UNAVAILABLE_WARNING]}
                )
            )
        else:
            explained.append(plan.model_copy(update={"explanation": explanation.explanation}))
    return explained


async def explain_plan(
    db: AsyncSession,
    *,
    plan_id: int,
    student_id: str,
    student_data: StudentData,
    explainer: Explainer,
) -> Any:
    plan = await _get_owned_plan(db, plan_id=plan_id, student_id=student_id)
    section_ids = [item.section_id for item in plan.items]
    student = await student_data.get_context(student_id)
    return await explainer.explain_plan(plan.term, section_ids, student)
