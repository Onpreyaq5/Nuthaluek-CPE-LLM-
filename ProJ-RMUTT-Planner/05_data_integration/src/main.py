"""05_data_integration — FastAPI Service (Port 8500)
- User Data & Student Context Engine
- Prerequisite DAG & Critical Path
- Course & Schedule Time Slot Normalization (182-bit Bitmask)
- Transcript Parser & Degree Plan Candidates
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

from prometheus_fastapi_instrumentator import Instrumentator
from fastapi import FastAPI, HTTPException, Query, Request
from pydantic import BaseModel, Field

from .degree_plan import build_candidates, build_plan_input
from .graduate_check import parse_graduate_check
from .normalizer import (
    CourseItem,
    CourseSearchIndex,
    CreditDetail,
    extract_base_code,
    normalize_course_code,
    parse_credit_detail,
)
from .prereq_graph import PrerequisiteDAG
from .student_context import (
    StudentContext,
    StudentPreferences,
    StudentProfile,
    build_student_context_from_audit,
    build_student_context_from_transcript,
)
from .time_slot import (
    check_clash,
    decode_overlap,
    meetings_to_bitmask,
    parse_schedule_string,
)
from .transcript_parser import (
    TranscriptRecord,
    build_transcript_summary,
    parse_transcript_csv,
    parse_transcript_text,
)

app = FastAPI(
    title="05_data_integration",
    description="Data Cleaning, Course Normalization, Time Slot Bitmasks, Prereq DAG & Student Context Service",
    version="1.0.0",
)

# /metrics ให้ Prometheus (ช่อง Monitoring ในแผนภาพ)
Instrumentator().instrument(app).expose(app, endpoint="/metrics", include_in_schema=False)

# In-memory stores
prereq_dag = PrerequisiteDAG()
course_index = CourseSearchIndex()
student_contexts: dict[str, StudentContext] = {}

# โหลดข้อมูลตัวอย่างเริ่มต้น (Sample / Mock)
def _init_sample_data():
    # เพิ่มวิชาตัวอย่างใน CPE
    sample_courses = [
        CourseItem(code="04000201-62", name_th="ฟิสิกส์ 1", name_en="Physics I", credits=3, credit_detail="3(3-0-6)", category="ศึกษาทั่วไป"),
        CourseItem(code="04000202-62", name_th="เคมีสำหรับวิศวกร", name_en="Chemistry for Engineers", credits=3, credit_detail="3(3-0-6)", category="ศึกษาทั่วไป"),
        CourseItem(code="04000203-62", name_th="แคลคูลัส 1", name_en="Calculus I", credits=3, credit_detail="3(3-0-6)", category="ศึกษาทั่วไป"),
        CourseItem(code="04000204-62", name_th="แคลคูลัส 2", name_en="Calculus II", credits=3, credit_detail="3(3-0-6)", category="ศึกษาทั่วไป"),
        CourseItem(code="040603001", name_th="การเขียนโปรแกรมคอมพิวเตอร์", name_en="Computer Programming", credits=3, credit_detail="3(2-2-5)", category="เฉพาะด้าน"),
        CourseItem(code="040603002", name_th="โครงสร้างข้อมูลและขั้นตอนวิธี", name_en="Data Structures and Algorithms", credits=3, credit_detail="3(3-0-6)", category="เฉพาะด้าน"),
        CourseItem(code="040603003", name_th="ระบบฐานข้อมูล", name_en="Database Systems", credits=3, credit_detail="3(3-0-6)", category="เฉพาะด้าน"),
        CourseItem(code="040603004", name_th="โครงงานวิศวกรรมคอมพิวเตอร์", name_en="Computer Engineering Project", credits=3, credit_detail="3(0-6-3)", category="เฉพาะด้าน"),
    ]
    for c in sample_courses:
        course_index.add_course(c)
        prereq_dag.add_course(c.code, name_th=c.name_th, credits=c.credits)

    # ความสัมพันธ์ Prereq
    # แคลคูลัส 1 -> แคลคูลัส 2
    prereq_dag.add_prerequisite("04000204-62", "04000203-62")
    # การเขียนโปรแกรม -> โครงสร้างข้อมูล
    prereq_dag.add_prerequisite("040603002", "040603001")
    # โครงสร้างข้อมูล -> ระบบฐานข้อมูล
    prereq_dag.add_prerequisite("040603003", "040603002")
    # ระบบฐานข้อมูล -> โครงงาน
    prereq_dag.add_prerequisite("040603004", "040603003")

    # ลองโหลด sample audit fixture ถ้ามี
    fixture_path = Path(__file__).resolve().parents[1] / "tests" / "fixtures" / "graduate_check_sample.html"
    if fixture_path.exists():
        try:
            audit = parse_graduate_check(fixture_path.read_bytes())
            ctx = build_student_context_from_audit(audit, prereq_dag=prereq_dag)
            student_contexts[audit.student_id] = ctx
            student_contexts["sample"] = ctx
        except Exception:
            pass


_init_sample_data()


# ---------------------------------------------------------------------------
# Pydantic Request / Response Models
# ---------------------------------------------------------------------------
class TranscriptParseRequest(BaseModel):
    content: str = Field(..., description="ข้อมูล CSV หรือข้อความผลการเรียน")
    format: str = Field("csv", description="'csv' หรือ 'text'")


class MeetingInput(BaseModel):
    day: Any = Field(..., description="0..6 หรือ 'จ.', 'พฤ.' หรือ 'MON'")
    start_min: Any = Field(None, description="นาทีจากเที่ยงคืน หรือ '09:00'")
    end_min: Any = Field(None, description="นาทีจากเที่ยงคืน หรือ '12:00'")
    time_str: str | None = Field(None, description="ข้อความช่วงเวลา เช่น 'จ. 09:00-12:00'")
    room: str | None = None
    building: str | None = None
    meeting_type: str | None = "lecture"


class SectionInput(BaseModel):
    section: str
    term: str = "1/2569"
    meetings: list[MeetingInput] = Field(default_factory=list)
    teachers: list[str] = Field(default_factory=list)
    seat_total: int | None = None
    seat_taken: int | None = None
    campus: str | None = None


class CourseRawInput(BaseModel):
    code: str
    name_th: str
    name_en: str | None = ""
    credits: int | None = None
    credit_detail: str | None = None
    category: str | None = "major"
    sections: list[SectionInput] = Field(default_factory=list)
    prerequisites: list[str] = Field(default_factory=list)


class NormalizeCoursesRequest(BaseModel):
    courses: list[CourseRawInput]


class ClashCheckRequest(BaseModel):
    mask_a: int | None = None
    mask_b: int | None = None
    meetings_a: list[MeetingInput] | None = None
    meetings_b: list[MeetingInput] | None = None


class PlanCandidatesRequest(BaseModel):
    student_id: str
    search_rows: list[dict[str, Any]] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------
@app.get("/health")
def health():
    return {"ok": True, "service": "05_data_integration"}


@app.get("/context/{student_id}")
def get_student_context(student_id: str):
    """ดึงข้อมูล Context ของนักศึกษาสำหรับส่งต่อให้โมดูล 03, 06, 07"""
    norm_id = student_id.strip()
    if norm_id in student_contexts:
        return student_contexts[norm_id].to_dict()

    # หากไม่มี ให้สร้าง Context เบื้องต้นขึ้นมา
    profile = StudentProfile(student_id=norm_id)
    ctx = StudentContext(
        profile=profile,
        preferences=StudentPreferences(),
        total_credits_earned=0,
        min_total_credits=143,
        remaining_total_credits=143,
        gpax=None,
        passed_courses=[],
        failed_courses=[],
        category_progress=[],
        unlocked_courses=prereq_dag.get_eligible_courses(set()),
    )
    return ctx.to_dict()


@app.get("/prereq/{course_code}")
def get_course_prereq(course_code: str):
    """ดึงข้อมูลวิชาบังคับก่อน และวิชาที่วิชานี้ปลดล็อกได้"""
    norm_code = normalize_course_code(course_code)
    info = prereq_dag.get_course_prereq_info(norm_code)
    return info


@app.get("/eligible/{student_id}")
def get_eligible_courses(student_id: str, term: str | None = Query(None)):
    """ดึงรายชื่อวิชาที่นักศึกษามีสิทธิ์ลงเรียนได้ในเทอมนี้ (ผ่าน prereq ครบแล้ว)"""
    norm_id = student_id.strip()
    passed_courses = set()
    if norm_id in student_contexts:
        passed_courses = set(student_contexts[norm_id].passed_courses)

    eligible = prereq_dag.get_eligible_courses(passed_courses)
    critical_scores = prereq_dag.calculate_critical_path_scores()

    results = []
    for code in eligible:
        c_item = course_index.courses_by_code.get(code)
        results.append({
            "course_code": code,
            "name_th": c_item.name_th if c_item else "",
            "name_en": c_item.name_en if c_item else "",
            "credits": c_item.credits if c_item else 3,
            "critical_path_score": critical_scores.get(code, 0),
        })

    # เรียงลำดับตามคะแนน critical path จากมากไปน้อย
    results.sort(key=lambda x: x["critical_path_score"], reverse=True)
    return {
        "student_id": norm_id,
        "term": term,
        "eligible_count": len(results),
        "eligible_courses": results,
    }


@app.post("/transcript/parse")
def parse_transcript(req: TranscriptParseRequest):
    """แปลงข้อมูลผลการเรียนจาก CSV หรือ Text"""
    if req.format.lower() == "text":
        summary = parse_transcript_text(req.content)
    else:
        summary = parse_transcript_csv(req.content)
    return summary.to_dict()


@app.post("/normalize/courses")
def normalize_courses(req: NormalizeCoursesRequest):
    """รับข้อมูลดิบจาก 04 นำมาทำความสะอาด แยกหน่วยกิต และคำนวณ 182-bit slot mask"""
    normalized_courses = []

    for raw in req.courses:
        norm_code = normalize_course_code(raw.code)
        cr_detail = parse_credit_detail(raw.credit_detail or (str(raw.credits) if raw.credits else "3"))
        
        # เพิ่มใน search index และ prereq DAG
        course_item = CourseItem(
            code=norm_code,
            name_th=raw.name_th,
            name_en=raw.name_en or "",
            credits=cr_detail.credits,
            credit_detail=cr_detail.raw,
            category=raw.category or "major",
        )
        course_index.add_course(course_item)
        prereq_dag.add_course(norm_code, name_th=raw.name_th, credits=cr_detail.credits)

        # เชื่อม prereq
        for p in raw.prerequisites:
            prereq_dag.add_prerequisite(norm_code, normalize_course_code(p))

        # ประมวลผล sections และคำนวณ bitmask
        clean_sections = []
        for sec in raw.sections:
            sec_meetings = [m.model_dump() for m in sec.meetings]
            mask = meetings_to_bitmask(sec_meetings)
            clean_sections.append({
                "section": sec.section,
                "term": sec.term,
                "slots_mask": mask,
                "slots_binary": f"{mask:0182b}"[-182:],
                "meetings": sec_meetings,
                "teachers": sec.teachers,
                "seat_total": sec.seat_total,
                "seat_taken": sec.seat_taken,
                "campus": sec.campus,
            })

        normalized_courses.append({
            "code": norm_code,
            "base_code": extract_base_code(norm_code),
            "name_th": raw.name_th,
            "name_en": raw.name_en or "",
            "credits": cr_detail.credits,
            "credit_detail": cr_detail.to_dict(),
            "category": raw.category,
            "sections": clean_sections,
            "prerequisites": [normalize_course_code(p) for p in raw.prerequisites],
        })

    return {
        "status": "success",
        "processed_count": len(normalized_courses),
        "courses": normalized_courses,
    }


@app.post("/plan/candidates")
def plan_candidates(req: PlanCandidatesRequest):
    """สร้างรายการ candidate รายวิชาจัดลำดับความสำคัญ (P0, P1, P2, P3) เพื่อส่งต่อให้โมดูล 06"""
    norm_id = req.student_id.strip()
    ctx = student_contexts.get(norm_id)
    if not ctx:
        raise HTTPException(status_code=404, detail=f"ไม่พบข้อมูลนักศึกษารหัส {norm_id}")

    # คำนวณ candidates ตาม priority
    critical_scores = prereq_dag.calculate_critical_path_scores()
    candidates = []

    # 1. P0: Retake courses (วิชาที่เคยได้ F/W)
    for code in ctx.failed_courses:
        candidates.append({
            "code": code,
            "priority": 0,
            "priority_label": "P0_RETAKE",
            "reason": "เคยลงแล้วไม่ผ่าน (F/W) ต้องลงใหม่",
            "critical_path_score": critical_scores.get(code, 0),
        })

    # 2. P1 & P2 & P3: วิชาที่ปลดล็อกได้ในเทอมนี้
    passed_set = set(ctx.passed_courses)
    eligible_codes = prereq_dag.get_eligible_courses(passed_set)

    for code in eligible_codes:
        if code in ctx.failed_courses:
            continue
        c_score = critical_scores.get(code, 0)
        unlocks_count = len(prereq_dag.get_all_unlocks(code))

        if unlocks_count > 0:
            pr = 2
            pr_label = "P2_UNLOCK"
            reason = f"ปลดล็อกวิชาอื่นอีก {unlocks_count} วิชา (Critical Path Score: {c_score})"
        else:
            pr = 3
            pr_label = "P3_OTHER"
            reason = "วิชาตามโครงสร้างหลักสูตร / วิชาเลือก"

        candidates.append({
            "code": code,
            "priority": pr,
            "priority_label": pr_label,
            "reason": reason,
            "critical_path_score": c_score,
        })

    # เรียงลำดับตาม priority (P0 -> P1 -> P2 -> P3) และคะแนน critical_path_score
    candidates.sort(key=lambda x: (x["priority"], -x["critical_path_score"]))

    return {
        "student_id": norm_id,
        "total_candidates": len(candidates),
        "candidates": candidates,
    }


@app.post("/slots/clash-check")
def clash_check(req: ClashCheckRequest):
    """ทดสอบและตรวจสอบการชนกันของตารางเวลา"""
    mask_a = req.mask_a
    mask_b = req.mask_b

    if mask_a is None and req.meetings_a:
        mask_a = meetings_to_bitmask([m.model_dump() for m in req.meetings_a])
    if mask_b is None and req.meetings_b:
        mask_b = meetings_to_bitmask([m.model_dump() for m in req.meetings_b])

    mask_a = mask_a or 0
    mask_b = mask_b or 0

    has_clash = check_clash(mask_a, mask_b)
    overlaps = decode_overlap(mask_a, mask_b) if has_clash else []

    return {
        "has_clash": has_clash,
        "mask_a": mask_a,
        "mask_b": mask_b,
        "overlap_count": len(overlaps),
        "overlaps": overlaps,
    }


@app.get("/search/courses")
def search_courses(q: str = Query(..., min_length=1), limit: int = Query(5, ge=1, le=20)):
    """ค้นหารายวิชาด้วย RapidFuzz แม้พิมพ์ตกหรือสะกดผิด"""
    results = course_index.search(query=q, limit=limit)
    return {
        "query": q,
        "count": len(results),
        "results": results,
    }


@app.get("/students/{student_id}/context")
def get_student_context_for_02(student_id: str):
    """Alias ของ /context/{id} สำหรับ 02_api_backend"""
    return get_student_context(student_id)


@app.get("/students/{student_id}/transcript")
def get_student_transcript_for_02(student_id: str):
    """สร้าง TranscriptResponse-shaped output ({courses, credits_by_category}) จาก context
    ที่มีอยู่แล้วในหน่วยความจำ ตามสัญญาที่ 02's schemas/students.py::TranscriptResponse ต้องการ"""
    norm_id = student_id.strip()
    ctx = student_contexts.get(norm_id)
    if not ctx:
        raise HTTPException(status_code=404, detail=f"ไม่พบข้อมูลนักศึกษารหัส {norm_id}")
    courses = [
        {
            "course_code": code,
            "course_name_th": (course_index.courses_by_code.get(code).name_th
                                if course_index.courses_by_code.get(code) else ""),
            "credits": (course_index.courses_by_code.get(code).credits
                        if course_index.courses_by_code.get(code) else 0),
            "grade": "ผ่าน" if code in ctx.passed_courses else "ไม่ผ่าน",
            "term": "1/2569",
        }
        for code in (ctx.passed_courses + ctx.failed_courses)
    ]
    credits_by_category = {c.category_id: c.passed_credits for c in ctx.category_progress}
    return {"courses": courses, "credits_by_category": credits_by_category}


def _build_import_result(audit) -> dict:
    """คำนวณผลลัพธ์ shape เดียวกับ 02's schemas/students.py::ImportResult
    ({imported_courses, retake_required, credits_remaining, warnings})"""
    plan_input = build_plan_input(audit)
    return {
        "imported_courses": len(audit.all_courses()),
        "retake_required": [course.code for _, course in audit.failed_courses()],
        "credits_remaining": plan_input.remaining_total or 0,
        "warnings": [],
    }


@app.post("/import/graduate-check")
async def import_graduate_check_http(request: Request):
    """นำเข้าผลการตรวจสอบจบผ่าน HTTP และบันทึกลง student_contexts"""
    raw = await request.body()
    audit = parse_graduate_check(raw)
    # 02 ส่งรหัสของคนที่ login มาเสมอ ใช้ตัวนั้นก่อน: ไฟล์บางแบบไม่มีรหัสนักศึกษา
    # เดิมเก็บตามรหัสในไฟล์อย่างเดียว ไฟล์ไม่มีรหัส = นำเข้าแล้วหายไปเฉย ๆ โปรไฟล์ไม่เปลี่ยน
    owner = (request.query_params.get("student_id") or "").strip() or audit.student_id
    if owner and not audit.student_id:
        audit.student_id = owner
    ctx = build_student_context_from_audit(audit, prereq_dag=prereq_dag)
    if owner:
        ctx.profile.student_id = owner
        student_contexts[owner] = ctx
    return _build_import_result(audit)

