"""06_schedule_conflict_engine - Pydantic Data Models & Schemas
Compatible with 06 contract, 02_api_backend, and 03_ai_router_agent
"""
from __future__ import annotations

from typing import Any, Literal
from pydantic import BaseModel, ConfigDict, Field


class Meeting(BaseModel):
    """คาบเรียน 1 คาบ (เช่น บรรยายวันจันทร์ 09:00-12:00)"""
    day: int = Field(..., ge=0, le=6, description="0=MON .. 6=SUN")
    start_min: int = Field(..., ge=0, le=1440, description="นาทีจากเที่ยงคืน เช่น 540=09:00")
    end_min: int = Field(..., ge=0, le=1440, description="นาทีจากเที่ยงคืน เช่น 720=12:00")
    room: str | None = None
    building: str | None = None
    meeting_type: str = "lecture"  # lecture | lab


class Exam(BaseModel):
    """ตารางสอบ"""
    exam_type: Literal["midterm", "final"]
    exam_date: str = Field(..., description="YYYY-MM-DD")
    start_min: int = Field(..., ge=0, le=1440)
    end_min: int = Field(..., ge=0, le=1440)
    room: str | None = None


class SectionInput(BaseModel):
    """ข้อมูล Section ที่ผู้ใช้เลือกหรือเปิดสอน"""
    id: str = Field(..., description="เช่น CPE101-01")
    course_code: str = Field(..., description="เช่น CPE101")
    section: str = Field(..., description="เช่น 01")
    course_name: str | None = None
    credits: int = Field(default=3, ge=0, le=12)
    slots_mask: int | None = Field(default=None, description="182-bit integer mask")
    meetings: list[Meeting] = Field(default_factory=list)
    exams: list[Exam] = Field(default_factory=list)
    seat_total: int | None = None
    seat_taken: int | None = None
    prerequisites: list[str] = Field(default_factory=list)
    campus: str | None = None
    teachers: list[str] = Field(default_factory=list)
    is_online: bool = False
    priority_score: int = 0  # สำหรับ CP-SAT solver (P0=100, P1=80, P2=60, P3=30)


class StudentPreferences(BaseModel):
    """ความชอบในการจัดตารางของนักศึกษา"""
    avoid_morning: bool = False  # หลีกเลี่ยงคาบเรียนก่อน 09:00 (หรือ 08:00)
    free_days: list[str] = Field(default_factory=list)  # เช่น ["FRI", "WED"]
    min_credits: int | None = None
    max_credits: int | None = None
    target_credits: int | None = None
    preferred_teachers: list[str] = Field(default_factory=list)
    avoid_long_gap: bool = True  # หลีกเลี่ยงช่องว่างเกิน 4 ชม.


class StudentContextInput(BaseModel):
    """ข้อมูลประวัติการเรียนของนักศึกษา"""
    student_id: str
    passed_courses: list[str] = Field(default_factory=list)
    failed_courses: list[str] = Field(default_factory=list)
    gpax: float | None = None


class ConflictDetail(BaseModel):
    """โครงสร้างข้อผิดพลาดตารางชนระดับ Hard Conflict (C1-C6)"""
    code: Literal["C1", "C2", "C3", "C4", "C5", "C6"]
    severity: Literal["ERROR", "WARNING"] = "ERROR"
    message_key: str  # time_clash | exam_clash | prereq_fail | credit_limit | duplicate | seat_full
    message_th: str
    message_en: str
    subjects: list[str] = Field(default_factory=list)
    detail: dict[str, Any] = Field(default_factory=dict)
    suggestions: list[dict[str, Any]] = Field(default_factory=list)

    # สำหรับความเข้ากันได้กับ 02_api_backend
    @property
    def type(self) -> str:
        return self.message_key

    @property
    def message(self) -> str:
        return self.message_th

    @property
    def section_ids(self) -> list[str]:
        return self.subjects

    @property
    def details(self) -> dict[str, Any]:
        return self.detail


class WarningDetail(BaseModel):
    """โครงสร้างคำเตือนคุณภาพชีวิต Soft Rules (W1-W5)"""
    code: Literal["W1", "W2", "W3", "W4", "W5"]
    severity: Literal["WARNING"] = "WARNING"
    message_key: str  # long_stretch | large_gap | early_class | rush_move | heavy_days
    message_th: str
    message_en: str
    detail: dict[str, Any] = Field(default_factory=dict)

    # สำหรับความเข้ากันได้กับ 02_api_backend
    @property
    def type(self) -> str:
        return self.message_key

    @property
    def message(self) -> str:
        return self.message_th

    @property
    def details(self) -> dict[str, Any]:
        return self.detail


class ValidationSummary(BaseModel):
    """สรุปผลการตรวจสอบตารางเรียน"""
    total_credits: int
    section_count: int
    is_valid: bool
    days_on_campus: int = 0
    free_days: list[str] = Field(default_factory=list)


class CheckConflictsRequest(BaseModel):
    """Request สำหรับตรวจสอบข้อขัดแย้งของตาราง"""
    model_config = ConfigDict(extra="ignore")
    student_id: str | None = None
    term: str = "1/2569"
    sections: list[SectionInput | str] = Field(default_factory=list)
    student: StudentContextInput | None = None


class CheckConflictsResponse(BaseModel):
    """Response ส่งกลับผลการตรวจสอบตารางชน"""
    has_conflict: bool
    conflicts: list[ConflictDetail] = Field(default_factory=list)
    warnings: list[WarningDetail] = Field(default_factory=list)
    summary: ValidationSummary


class GeneratePlanRequest(BaseModel):
    """Request จัดตารางอัตโนมัติ (CP-SAT)"""
    model_config = ConfigDict(extra="ignore")
    student_id: str | None = None
    term: str = "1/2569"
    preferences: StudentPreferences | None = None
    available_sections: list[SectionInput] = Field(default_factory=list)
    student: StudentContextInput | None = None
    must_include: list[str] = Field(default_factory=list)  # รหัสวิชาหรือ section ที่ต้องมี
    exclude: list[str] = Field(default_factory=list)       # รหัสวิชาหรือ section ที่ห้ามมี


class CandidatePlan(BaseModel):
    """หนึ่งในแผนทางเลือก 3-5 แผนที่ Solver เสนอ"""
    plan_index: int
    name: str
    total_credits: int
    score: float
    sections: list[SectionInput]
    summary: ValidationSummary
    warnings: list[WarningDetail] = Field(default_factory=list)
    tradeoffs_made: list[str] = Field(default_factory=list)


class GeneratePlanResponse(BaseModel):
    """Response ผลการจัดตารางอัตโนมัติ"""
    status: str = "success"
    term: str
    plans_count: int
    plans: list[CandidatePlan] = Field(default_factory=list)
    relaxed: bool = False


class RepairPlanRequest(BaseModel):
    """Request เสนอวิธีซ่อมแซมตารางที่ชน"""
    term: str = "1/2569"
    sections: list[SectionInput]
    all_available_sections: list[SectionInput] = Field(default_factory=list)


class RepairPlanResponse(BaseModel):
    has_repair: bool
    suggestions: list[dict[str, Any]] = Field(default_factory=list)


class ComparePlansRequest(BaseModel):
    """Request เปรียบเทียบ 2 แผน"""
    plan_a: list[SectionInput]
    plan_b: list[SectionInput]


class ComparePlansResponse(BaseModel):
    credits_a: int
    credits_b: int
    days_a: int
    days_b: int
    free_days_a: list[str]
    free_days_b: list[str]
    overlap_a: bool
    overlap_b: bool
    comparison_notes: list[str]
