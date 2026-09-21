from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from src.schemas.chat import SourceItem, StudentPreferences
from src.schemas.common import TermStr


class StudentProfile(BaseModel):
    student_id: str
    program_id: str
    program_name: str
    year_level: int
    gpax: float
    credits_earned: int
    credits_remaining: int


class TranscriptCourse(BaseModel):
    course_code: str
    course_name_th: str
    credits: int
    grade: str
    term: TermStr


class TranscriptResponse(BaseModel):
    courses: list[TranscriptCourse]
    credits_by_category: dict[str, int]


class ImportResult(BaseModel):
    imported_courses: int
    retake_required: list[str] = Field(default_factory=list)
    credits_remaining: int
    warnings: list[str] = Field(default_factory=list)


class AutoPlanRequest(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={"example": {"term": "1/2569", "must_include": [], "exclude": []}}
    )

    term: TermStr
    preferences: StudentPreferences | None = None
    must_include: list[str] = Field(default_factory=list)
    exclude: list[str] = Field(default_factory=list)


class GeneratedPlan(BaseModel):
    sections: list[str]
    total_credits: int
    relaxed_constraints: list[str] = Field(default_factory=list)
    explanation: str | None = None
    warnings: list[str] = Field(default_factory=list)


class AutoPlanResponse(BaseModel):
    plans: list[GeneratedPlan]


class ExplainResponse(BaseModel):
    explanation: str
    sources: list[SourceItem] = Field(default_factory=list)
