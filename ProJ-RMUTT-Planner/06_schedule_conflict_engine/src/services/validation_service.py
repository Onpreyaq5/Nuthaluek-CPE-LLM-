"""06_schedule_conflict_engine - Validation Service
Orchestrates section resolution, hard conflict detection, and soft rule evaluation
"""
from __future__ import annotations

from typing import Any
from ..adapters.providers import SectionProvider
from ..api.schemas_backend import (
    BackendConflictItem,
    BackendValidateResponse,
    BackendValidateSummary,
    BackendWarningItem,
)
from ..api.schemas_router import RouterConflictResponse
from ..core.conflict_detector import detect_conflicts
from ..core.quality_evaluator import evaluate_quality
from ..models.schemas import (
    ConflictDetail,
    SectionInput,
    StudentContextInput,
    StudentPreferences,
    ValidationSummary,
    WarningDetail,
)


class ValidationResult:
    def __init__(
        self,
        sections: list[SectionInput],
        conflicts: list[ConflictDetail],
        warnings: list[WarningDetail],
        summary: ValidationSummary,
    ):
        self.sections = sections
        self.conflicts = conflicts
        self.warnings = warnings
        self.summary = summary


async def run_validation(
    section_ids: list[str],
    term: str,
    section_provider: SectionProvider,
    student: StudentContextInput | None = None,
    preferences: StudentPreferences | None = None,
) -> ValidationResult:
    """ประมวลผลการตรวจสอบตารางเรียน: resolve ข้อมูลจริง -> ตรวจ C1-C6 -> ตรวจ W1-W5"""
    # 1. Resolve sections จาก provider จริง (ห้ามเดาหรือสร้าง mock ว่าง)
    sections = await section_provider.get_sections_by_ids(section_ids, term)

    # 2. ตรวจสอบ Hard Conflicts C1-C6
    conflicts = detect_conflicts(sections, term=term, student=student)

    # 3. ประเมิน Soft Rules W1-W5
    warnings, profile = evaluate_quality(sections, preferences=preferences)

    total_cr = sum(s.credits for s in sections)
    has_err = any(c.severity == "ERROR" for c in conflicts)

    summary = ValidationSummary(
        total_credits=total_cr,
        section_count=len(sections),
        is_valid=(not has_err),
        days_on_campus=profile.get("days_on_campus", 0),
        free_days=profile.get("free_days", []),
    )

    return ValidationResult(
        sections=sections,
        conflicts=conflicts,
        warnings=warnings,
        summary=summary,
    )


def map_validation_for_backend(result: ValidationResult) -> BackendValidateResponse:
    """แปลงผลลัพธ์ภายในให้ตรงกับ Pydantic Schema ของ 02_api_backend แบบ 1:1"""
    backend_conflicts = [
        BackendConflictItem(
            type=c.message_key,
            message=c.message_th,
            section_ids=c.subjects,
            details=c.detail,
        )
        for c in result.conflicts
    ]

    backend_warnings = [
        BackendWarningItem(
            type=w.message_key,
            message=w.message_th,
            details=w.detail,
        )
        for w in result.warnings
    ]

    backend_summary = BackendValidateSummary(
        total_credits=result.summary.total_credits,
        section_count=result.summary.section_count,
        is_valid=result.summary.is_valid,
    )

    return BackendValidateResponse(
        conflicts=backend_conflicts,
        warnings=backend_warnings,
        summary=backend_summary,
    )


def map_validation_for_router(result: ValidationResult) -> RouterConflictResponse:
    """แปลงผลลัพธ์ภายในให้ตรงกับ Rich Response ของ 03_ai_router_agent"""
    return RouterConflictResponse(
        has_conflict=len(result.conflicts) > 0,
        conflicts=result.conflicts,
        warnings=result.warnings,
        summary=result.summary,
    )
