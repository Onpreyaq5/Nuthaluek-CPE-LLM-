from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from src.schemas.common import Page, TermStr
from src.schemas.courses import Section


class ConflictItem(BaseModel):
    """ต้องตรงกับ RESPONSE CONTRACT ของ 06 — 02 ไม่ตัดสินเอง

    code/severity/message_key/message_th/message_en/subjects/detail/suggestions เพิ่มเข้ามาเพื่อส่งต่อให้
    07's ExplainPlanRequest.conflicts (ConflictIn) ได้ครบ — ของเดิมมีแค่ type/message/section_ids/details
    ทำให้ 02 รับ response จาก 06 มาไม่ครบตั้งแต่ต้น แล้วส่งต่อให้ 07 ไม่ได้เลย"""

    type: str
    message: str
    section_ids: list[str] = Field(default_factory=list)
    details: dict = Field(default_factory=dict)
    code: str = ""
    severity: str = "ERROR"
    message_key: str = ""
    message_th: str = ""
    message_en: str = ""
    subjects: list[str] = Field(default_factory=list)
    detail: dict = Field(default_factory=dict)
    suggestions: list[dict] = Field(default_factory=list)


class WarningItem(BaseModel):
    type: str
    message: str
    details: dict = Field(default_factory=dict)
    code: str = ""
    severity: str = "WARNING"
    message_key: str = ""
    message_th: str = ""
    message_en: str = ""
    subjects: list[str] = Field(default_factory=list)
    detail: dict = Field(default_factory=dict)
    suggestions: list[dict] = Field(default_factory=list)


class ValidateSummary(BaseModel):
    total_credits: int
    section_count: int
    is_valid: bool


class PlanValidateRequest(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={"example": {"term": "1/2569", "section_ids": ["CPE301-01", "CPE302-02"]}}
    )

    term: TermStr
    section_ids: list[str] = Field(min_length=1, max_length=15)


class PlanValidateResponse(BaseModel):
    conflicts: list[ConflictItem] = Field(default_factory=list)
    warnings: list[WarningItem] = Field(default_factory=list)
    summary: ValidateSummary


class PlanCreateRequest(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "example": {"term": "1/2569", "name": "แผนหลัก", "section_ids": ["CPE301-01", "CPE302-02"]}
        }
    )

    term: TermStr
    name: str
    section_ids: list[str] = Field(min_length=1, max_length=15)


class PlanCreateResponse(BaseModel):
    plan_id: int


class PlanSummary(BaseModel):
    id: int
    term: TermStr
    name: str
    total_credits: int
    updated_at: datetime


class PlanListResponse(Page[PlanSummary]):
    pass


class PlanDetail(BaseModel):
    id: int
    term: TermStr
    name: str
    sections: list[Section]
    last_validation: PlanValidateResponse | None = None
