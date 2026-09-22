"""06_schedule_conflict_engine - Planning Service
Orchestrates section retrieval, CP-SAT optimization, and response mapping for 02 and 03
"""
from __future__ import annotations

from typing import Any
from ..adapters.providers import SectionProvider
from ..api.schemas_backend import (
    BackendGeneratedPlan,
    BackendGenerateResponse,
)
from ..api.schemas_router import RouterGenerateResponse
from ..config import get_settings
from ..core.planner import generate_schedule_plans
from ..models.schemas import (
    GeneratePlanResponse,
    SectionInput,
    StudentContextInput,
    StudentPreferences,
)


async def run_planning(
    term: str,
    section_provider: SectionProvider,
    preferences: StudentPreferences | None = None,
    student: StudentContextInput | None = None,
    must_include: list[str] | None = None,
    exclude: list[str] | None = None,
    available_sections: list[SectionInput] | None = None,
) -> GeneratePlanResponse:
    """รัน Auto Planner ด้วย CP-SAT โดยดึง Section จริงจาก provider"""
    settings = get_settings()

    candidate_sections: list[SectionInput] = []
    if available_sections:
        candidate_sections = available_sections
    else:
        # ดึง open sections จาก provider
        candidate_sections = await section_provider.search_open_sections(term=term)

    if not candidate_sections:
        if not settings.demo_mode:
            # ใน Production หากไม่มี section ให้คืนแผนว่าง ไม่สร้าง mock หลอก
            return GeneratePlanResponse(
                status="no_sections_available",
                term=term,
                plans_count=0,
                plans=[],
                relaxed=False,
            )

    response = generate_schedule_plans(
        available_sections=candidate_sections,
        term=term,
        preferences=preferences,
        student=student,
        must_include=must_include or [],
        exclude=exclude or [],
        max_candidates=settings.max_plan_candidates,
    )
    return response


def map_plans_for_backend(response: GeneratePlanResponse) -> BackendGenerateResponse:
    """แปลงผลการจัดตารางให้ตรงกับ Pydantic Schema ของ 02 (GeneratedPlan)"""
    backend_plans: list[BackendGeneratedPlan] = []

    for plan in response.plans:
        backend_plans.append(
            BackendGeneratedPlan(
                sections=[s if isinstance(s, str) else s.id for s in plan.sections],  # ต้องเป็น string ID เท่านั้น
                total_credits=plan.total_credits,
                relaxed_constraints=plan.tradeoffs_made,
                explanation=None,  # หน้าที่สร้างคำอธิบายเป็นของ 07
                warnings=[w.message_th for w in plan.warnings],  # ต้องเป็น list[str]
            )
        )

    return BackendGenerateResponse(plans=backend_plans)


def map_plans_for_router(response: GeneratePlanResponse) -> RouterGenerateResponse:
    """แปลงผลการจัดตารางให้ตรงกับ Rich Response ของ 03 (RouterGenerateResponse)"""
    return RouterGenerateResponse(
        status=response.status,
        term=response.term,
        plans_count=response.plans_count,
        plans=response.plans,
        relaxed=response.relaxed,
    )
