"""06_schedule_conflict_engine - Module 03 (AI Router) Contract Schemas
Must support current 03_ai_router_agent requests and rich response contract
"""
from __future__ import annotations

from typing import Any
from pydantic import BaseModel, Field
from ..models.schemas import CandidatePlan, ConflictDetail, ValidationSummary, WarningDetail


class RouterCheckConflictsRequest(BaseModel):
    sections: list[str] = Field(..., min_length=1)
    student_id: str | None = None
    term: str = "1/2569"


class RouterConflictResponse(BaseModel):
    has_conflict: bool
    conflicts: list[ConflictDetail] = Field(default_factory=list)
    warnings: list[WarningDetail] = Field(default_factory=list)
    summary: ValidationSummary


class RouterStudentPreferences(BaseModel):
    free_days: list[str] = Field(default_factory=list)
    no_early_class: bool = False
    avoid_morning: bool = False
    max_credits: int | None = None
    min_credits: int | None = None


class RouterAutoPlanRequest(BaseModel):
    student_id: str
    term: str = "1/2569"
    preferences: RouterStudentPreferences | None = None


class RouterGenerateResponse(BaseModel):
    status: str
    term: str
    plans_count: int
    plans: list[CandidatePlan] = Field(default_factory=list)
    relaxed: bool = False
