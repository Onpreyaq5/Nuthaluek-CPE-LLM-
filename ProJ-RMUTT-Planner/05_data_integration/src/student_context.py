"""Student Context Engine
- รวบรวมและสร้างก้อน Context สมบูรณ์ของนักศึกษา:
  Profile + Transcript + Degree Audit + ความชอบ (Preferences)
- คำนวณหน่วยกิตสะสม, GPAX, หน่วยกิตคงเหลือแยกตามหมวด (ศึกษาทั่วไป / เฉพาะด้าน / เสรี), และปีที่คาดว่าจะจบ
- เตรียมโครงสร้างข้อมูล JSON สำหรับส่งต่อให้ 03_ai_router_agent, 06_schedule_conflict_engine, 07_rag_llm_engine
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any

from .degree_plan import DegreePlanInput, build_candidates
from .graduate_check import DegreeAudit
from .normalizer import extract_base_code, normalize_course_code
from .prereq_graph import PrerequisiteDAG
from .transcript_parser import TranscriptSummary


@dataclass
class StudentProfile:
    student_id: str
    name_th: str = ""
    program_id: str = "CPE-2566"
    entry_year: int = 2566
    curriculum_year: int = 2566

    @property
    def student_year(self) -> int:
        """ปีการศึกษาปัจจุบันของนักศึกษาโดยประมาณ (อิงปีปัจจุบัน 2569)"""
        return max(1, 2569 - self.entry_year + 1)


@dataclass
class StudentPreferences:
    no_early_class: bool = False       # ไม่เอาคาบก่อน 09:00
    free_days: list[int] = field(default_factory=list)  # [4] = ว่างวันศุกร์
    max_credits: int = 21              # เพดานหน่วยกิต มทร.ธัญบุรี
    min_credits: int = 9
    avoid_gaps: bool = True            # หลีกเลี่ยงคาบว่างยาว
    preferred_teachers: list[str] = field(default_factory=list)
    campus: str = "ศูนย์รังสิต"

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class CategoryProgress:
    category_id: str             # "1", "2.1", "3"
    name: str                   # "ศึกษาทั่วไป", "กลุ่มวิชาเฉพาะด้าน"
    min_credits: int
    passed_credits: int
    remaining_credits: int
    is_completed: bool

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


_PROGRAM_NAMES = {
    "CPE-2563": "วิศวกรรมคอมพิวเตอร์",
    "CPE-2564": "วิศวกรรมคอมพิวเตอร์",
    "CPE-2565": "วิศวกรรมคอมพิวเตอร์",
    "CPE-2566": "วิศวกรรมคอมพิวเตอร์",
    "CPE-2567": "วิศวกรรมคอมพิวเตอร์",
    "CPE-2568": "วิศวกรรมคอมพิวเตอร์",
    "CPE-2569": "วิศวกรรมคอมพิวเตอร์",
}


@dataclass
class StudentContext:
    profile: StudentProfile
    preferences: StudentPreferences
    total_credits_earned: int
    min_total_credits: int
    remaining_total_credits: int
    gpax: float | None
    passed_courses: list[str]
    failed_courses: list[str]
    category_progress: list[CategoryProgress]
    unlocked_courses: list[str] = field(default_factory=list)
    expected_grad_year: int = 2570

    def to_dict(self) -> dict[str, Any]:
        day_names = ["MON", "TUE", "WED", "THU", "FRI", "SAT", "SUN"]
        preferences_dict = self.preferences.to_dict()
        preferences_dict["free_days"] = [
            day_names[d] if isinstance(d, int) and 0 <= d <= 6 else str(d)
            for d in self.preferences.free_days
        ]

        return {
            "student_id": self.profile.student_id,
            "id_hash": self.profile.student_id,
            "name_th": self.profile.name_th,
            "program_id": self.profile.program_id,
            "program_name": _PROGRAM_NAMES.get(self.profile.program_id, self.profile.program_id),
            "entry_year": self.profile.entry_year,
            "student_year": self.profile.student_year,
            "year_level": self.profile.student_year,
            "curriculum_year": self.profile.curriculum_year,
            "expected_grad_year": self.expected_grad_year,
            "credits_earned": self.total_credits_earned,
            "credits_remaining": self.remaining_total_credits,
            "gpax": self.gpax,
            "academic_summary": {
                "total_credits_earned": self.total_credits_earned,
                "min_total_credits": self.min_total_credits,
                "remaining_total_credits": self.remaining_total_credits,
                "gpax": self.gpax,
                "passed_courses_count": len(self.passed_courses),
                "failed_courses_count": len(self.failed_courses),
            },
            "passed_courses": self.passed_courses,
            "completed_course_codes": self.passed_courses,
            "failed_courses": self.failed_courses,
            "unlocked_courses": self.unlocked_courses,
            "category_progress": [c.to_dict() for c in self.category_progress],
            "preferences": preferences_dict,
        }


def build_student_context_from_audit(
    audit: DegreeAudit,
    preferences: StudentPreferences | None = None,
    prereq_dag: PrerequisiteDAG | None = None,
) -> StudentContext:
    """สร้าง StudentContext จาก DegreeAudit (หน้าตรวจสอบจบ)"""
    prefs = preferences or StudentPreferences()
    sid = audit.student_id or "unknown"
    
    # ดึงปีเข้าจากรหัสนักศึกษา 1166... -> 2566
    entry_year = 2566
    if len(sid) >= 4 and sid[:2] == "11" and sid[2:4].isdigit():
        entry_year = 2500 + int(sid[2:4])

    profile = StudentProfile(
        student_id=sid,
        name_th=audit.student_name,
        program_id=f"CPE-{entry_year}",
        entry_year=entry_year,
        curriculum_year=entry_year,
    )

    passed_courses = []
    failed_courses = []
    for c in audit.all_courses():
        norm_c = normalize_course_code(c.code)
        if c.passed:
            passed_courses.append(norm_c)
        elif c.taken:
            failed_courses.append(norm_c)

    categories = []
    for cat in audit.categories:
        if cat.min_credits is None:
            continue
        passed_cr = cat.passed_credits if cat.passed_credits is not None else sum(
            c.credits for c in cat.courses if c.passed
        )
        rem_cr = cat.remaining_credits if cat.remaining_credits is not None else max(cat.min_credits - passed_cr, 0)
        is_comp = cat.is_passed is True or (rem_cr == 0)
        categories.append(CategoryProgress(
            category_id=cat.number,
            name=cat.name,
            min_credits=cat.min_credits,
            passed_credits=passed_cr,
            remaining_credits=rem_cr,
            is_completed=is_comp,
        ))

    min_tot = audit.min_total_credits or 143
    earned_tot = audit.total_passed_credits
    if earned_tot is None:
        top_cats = [cat for cat in audit.categories if cat.depth == 1 and cat.passed_credits is not None]
        if top_cats:
            earned_tot = sum(cat.passed_credits for cat in top_cats)
        else:
            earned_tot = sum(c.credits for c in audit.all_courses() if c.passed)
    rem_tot = max(min_tot - earned_tot, 0)

    # คำนวณปีที่คาดว่าจะจบ: ปีเข้า + 4 ปี (หลักสูตร 4 ปี)
    expected_grad = entry_year + 4

    # คำนวณวิชาที่ปลดล็อกถ้ามี DAG
    unlocked = []
    if prereq_dag:
        unlocked = prereq_dag.get_eligible_courses(set(passed_courses))

    return StudentContext(
        profile=profile,
        preferences=prefs,
        total_credits_earned=earned_tot,
        min_total_credits=min_tot,
        remaining_total_credits=rem_tot,
        gpax=audit.gpa,
        passed_courses=sorted(list(set(passed_courses))),
        failed_courses=sorted(list(set(failed_courses))),
        category_progress=categories,
        unlocked_courses=unlocked,
        expected_grad_year=expected_grad,
    )


def build_student_context_from_transcript(
    profile: StudentProfile,
    transcript: TranscriptSummary,
    preferences: StudentPreferences | None = None,
    prereq_dag: PrerequisiteDAG | None = None,
    min_total_credits: int = 143,
) -> StudentContext:
    """สร้าง StudentContext จากผลการเรียนใน TranscriptSummary"""
    prefs = preferences or StudentPreferences()
    earned = transcript.total_credits_passed
    rem = max(min_total_credits - earned, 0)
    expected_grad = profile.entry_year + 4

    unlocked = []
    if prereq_dag:
        unlocked = prereq_dag.get_eligible_courses(set(transcript.passed_courses))

    return StudentContext(
        profile=profile,
        preferences=prefs,
        total_credits_earned=earned,
        min_total_credits=min_total_credits,
        remaining_total_credits=rem,
        gpax=transcript.gpax,
        passed_courses=transcript.passed_courses,
        failed_courses=transcript.failed_courses,
        category_progress=[],
        unlocked_courses=unlocked,
        expected_grad_year=expected_grad,
    )
