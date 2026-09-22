"""06_schedule_conflict_engine - Module 02 (API Backend) Contract Schemas
Must strictly match 02_api_backend's PlanValidateResponse and GeneratedPlan
"""
from __future__ import annotations

from typing import Any
from pydantic import BaseModel, Field


# --- Student & Preference Request Schemas for 02 ---

class BackendStudentPreference(BaseModel):
    free_days: list[str] = Field(default_factory=list)
    no_early_class: bool = False
    max_credits: int | None = None


class BackendStudentContext(BaseModel):
    student_id: str | None = None
    id_hash: str | None = None
    program_id: str | None = None
    program_name: str | None = None
    curriculum_year: int | None = None
    year_level: int | None = None
    credits_earned: int | None = None
    credits_remaining: int | None = None
    gpax: float | None = None
    completed_course_codes: list[str] = Field(default_factory=list)
    preferences: BackendStudentPreference | None = None


# --- 02 /validate Contract ---

class BackendValidateRequest(BaseModel):
    term: str = Field(..., pattern=r"^[1-3]/\d{4}$")
    section_ids: list[str] = Field(min_length=1, max_length=15)
    student: BackendStudentContext | None = None


class BackendConflictItem(BaseModel):
    type: str
    message: str
    section_ids: list[str] = Field(default_factory=list)
    details: dict[str, Any] = Field(default_factory=dict)


class BackendWarningItem(BaseModel):
    type: str
    message: str
    details: dict[str, Any] = Field(default_factory=dict)


class BackendValidateSummary(BaseModel):
    total_credits: int
    section_count: int
    is_valid: bool


class BackendValidateResponse(BaseModel):
    conflicts: list[BackendConflictItem] = Field(default_factory=list)
    warnings: list[BackendWarningItem] = Field(default_factory=list)
    summary: BackendValidateSummary


# --- 02 /generate Contract ---

class BackendGenerateRequest(BaseModel):
    term: str = Field(..., pattern=r"^[1-3]/\d{4}$")
    preferences: BackendStudentPreference | None = None
    student: BackendStudentContext | None = None
    must_include: list[str] = Field(default_factory=list)
    exclude: list[str] = Field(default_factory=list)


class BackendGeneratedPlan(BaseModel):
    sections: list[str]
    total_credits: int
    relaxed_constraints: list[str] = Field(default_factory=list)
    explanation: str | None = None
    warnings: list[str] = Field(default_factory=list)


class BackendGenerateResponse(BaseModel):
    plans: list[BackendGeneratedPlan] = Field(default_factory=list)
