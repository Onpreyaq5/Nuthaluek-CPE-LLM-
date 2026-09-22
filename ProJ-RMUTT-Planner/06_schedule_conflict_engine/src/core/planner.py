"""06_schedule_conflict_engine - Google OR-Tools CP-SAT Auto Planner
จัดตารางเรียนอัตโนมัติด้วย Constraint Programming (CP-SAT Solver)
สร้าง 3 - 5 ทางเลือกที่เหมาะสมที่สุด พร้อมระบบ Relaxation เมื่อติดเงื่อนไขตึงเกินไป
"""
from __future__ import annotations

from typing import Any
from ortools.sat.python import cp_model
from ..config import get_settings
from ..models.schemas import (
    CandidatePlan,
    GeneratePlanResponse,
    SectionInput,
    StudentContextInput,
    StudentPreferences,
    ValidationSummary,
)
from .bitmask import (
    DAY_NAMES,
    check_clash,
    ensure_section_mask,
    get_schedule_profile,
)
from .conflict_detector import detect_conflicts
from .quality_evaluator import evaluate_quality


def build_and_solve_plan(
    available_sections: list[SectionInput],
    term: str = "1/2569",
    preferences: StudentPreferences | None = None,
    student: StudentContextInput | None = None,
    must_include: list[str] | None = None,
    exclude: list[str] | None = None,
    max_candidates: int = 5,
    allow_full_seats: bool = False,
    relax_min_credits: bool = False,
    relax_preferences: bool = False,
) -> tuple[list[CandidatePlan], bool]:
    """สร้างและรันโมเดล CP-SAT เพื่อค้นหาชุดตารางเรียน 3 - 5 แผน
    คืนค่า: (candidate_plans[], is_relaxed)
    """
    settings = get_settings()
    must_include_set = set(must_include or [])
    exclude_set = set(exclude or [])
    passed_courses = set(student.passed_courses) if student else set()
    is_summer = "3" in term or "summer" in term.lower()

    max_credits = settings.summer_max_credits if is_summer else settings.default_max_credits
    min_credits = 1 if is_summer else (0 if relax_min_credits else settings.default_min_credits)

    # กรอง Section เบื้องต้น
    valid_sections: list[SectionInput] = []
    for sec in available_sections:
        # หากอยู่ใน exclude
        if sec.id in exclude_set or sec.course_code in exclude_set:
            continue
        # หากเคยผ่านแล้ว
        if sec.course_code in passed_courses:
            continue
        # หาก Prereq ไม่ครบ
        missing_prereqs = [p for p in sec.prerequisites if p not in passed_courses]
        if student and missing_prereqs:
            continue
        # หากที่นั่งเต็ม (และยังไม่ได้ผ่อนปรน)
        if (
            not allow_full_seats
            and sec.seat_total is not None
            and sec.seat_taken is not None
            and sec.seat_taken >= sec.seat_total
        ):
            continue

        ensure_section_mask(sec)
        valid_sections.append(sec)

    if not valid_sections:
        return [], False

    # สร้าง Mapping รายวิชา -> Sections
    course_to_sections: dict[str, list[int]] = {}
    for idx, sec in enumerate(valid_sections):
        course_to_sections.setdefault(sec.course_code, []).append(idx)

    # เตรียมข้อมูลความขัดแย้งล่วงหน้า (Precompute Clashes)
    clash_pairs: list[tuple[int, int]] = []
    n = len(valid_sections)
    for i in range(n):
        for j in range(i + 1, n):
            sec_a, sec_b = valid_sections[i], valid_sections[j]
            # เวลาเรียนชน
            if sec_a.slots_mask and sec_b.slots_mask and check_clash(sec_a.slots_mask, sec_b.slots_mask):
                clash_pairs.append((i, j))
                continue
            # สอบชน
            exam_clash = False
            for ex_a in sec_a.exams:
                for ex_b in sec_b.exams:
                    if ex_a.exam_type == ex_b.exam_type and ex_a.exam_date == ex_b.exam_date:
                        if max(ex_a.start_min, ex_b.start_min) < min(ex_a.end_min, ex_b.end_min):
                            exam_clash = True
                            break
                if exam_clash:
                    break
            if exam_clash:
                clash_pairs.append((i, j))

    candidates: list[CandidatePlan] = []
    previous_solutions: list[list[int]] = []

    for plan_num in range(1, max_candidates + 1):
        model = cp_model.CpModel()

        # ตัวแปร Boolean x[i] = เลือกลง Section i หรือไม่
        x = [model.NewBoolVar(f"x_{sec.id}") for sec in valid_sections]

        # 1. ข้อจำกัด: แต่ละวิชาเลือกได้ไม่เกิน 1 Section
        for c_code, sec_indices in course_to_sections.items():
            model.AddAtMostOne([x[idx] for idx in sec_indices])
            # หากอยู่ใน must_include ต้องเลือกอย่างน้อย 1 Section
            if c_code in must_include_set:
                model.Add(sum(x[idx] for idx in sec_indices) == 1)

        # หากระบุ Section ID ชัดเจนใน must_include
        for idx, sec in enumerate(valid_sections):
            if sec.id in must_include_set:
                model.Add(x[idx] == 1)

        # 2. ข้อจำกัด: ห้ามเวลาเรียนหรือเวลาสอบชนกัน
        for i, j in clash_pairs:
            model.Add(x[i] + x[j] <= 1)

        # 3. ข้อจำกัด: หน่วยกิตรวม
        total_credits_expr = sum(valid_sections[i].credits * x[i] for i in range(n))
        model.Add(total_credits_expr <= max_credits)
        model.Add(total_credits_expr >= min_credits)

        # 4. ห้ามซ้ำกับชุดวิชาในแผนก่อนหน้า (Solution Diversity)
        for prev_indices in previous_solutions:
            model.Add(sum(x[idx] for idx in prev_indices) <= len(prev_indices) - 1)

        # 5. ฟังก์ชันเป้าหมาย (Objective Function)
        # ตัวแปรวันที่มีเรียน y[day] ∈ {0, 1}
        y_days = [model.NewBoolVar(f"day_{d}") for d in range(7)]
        for day in range(7):
            day_sec_indices = [
                i for i, sec in enumerate(valid_sections)
                if any(m.day == day for m in sec.meetings)
            ]
            for idx in day_sec_indices:
                model.Add(y_days[day] >= x[idx])

        objective_terms = []

        # น้ำหนักตามความสำคัญวิชา (Priority Score)
        for i, sec in enumerate(valid_sections):
            score = sec.priority_score if sec.priority_score > 0 else 50
            objective_terms.append(x[i] * score * 10)

        # น้ำหนักตามความชอบของนักศึกษา
        if preferences and not relax_preferences:
            free_days_indices = [
                DAY_NAMES.index(d) for d in preferences.free_days if d in DAY_NAMES
            ]
            for d_idx in free_days_indices:
                # ลดคะแนนอย่างหนักถ้ามีเรียนในวันที่ขอว่าง
                objective_terms.append(y_days[d_idx] * -150)

            if preferences.avoid_morning:
                for i, sec in enumerate(valid_sections):
                    has_early = any(
                        m.start_min < 540 for m in sec.meetings  # ก่อน 09:00
                    )
                    if has_early:
                        objective_terms.append(x[i] * -80)

            # อาจารย์ที่ชอบ
            for i, sec in enumerate(valid_sections):
                matching_teachers = set(sec.teachers).intersection(
                    set(preferences.preferred_teachers)
                )
                if matching_teachers:
                    objective_terms.append(x[i] * 60)

        # ลดจำนวนวันที่ต้องเดินทางมามหาวิทยาลัย (Compactness)
        for day in range(7):
            objective_terms.append(y_days[day] * -30)

        model.Maximize(sum(objective_terms))

        solver = cp_model.CpSolver()
        solver.parameters.max_time_in_seconds = settings.max_solver_seconds
        status = solver.Solve(model)

        if status in (cp_model.OPTIMAL, cp_model.FEASIBLE):
            selected_indices = [i for i in range(n) if solver.Value(x[i]) == 1]
            if not selected_indices:
                break

            chosen_sections = [valid_sections[i] for i in selected_indices]
            previous_solutions.append(selected_indices)

            tot_cr = sum(s.credits for s in chosen_sections)
            tot_mask = 0
            for s in chosen_sections:
                tot_mask |= s.slots_mask or 0
            prof = get_schedule_profile(tot_mask)
            warns, _ = evaluate_quality(chosen_sections, preferences)

            # Tradeoffs ที่เกิดขึ้น
            tradeoffs: list[str] = []
            if allow_full_seats:
                full_secs = [
                    s.id for s in chosen_sections
                    if s.seat_total and s.seat_taken and s.seat_taken >= s.seat_total
                ]
                if full_secs:
                    tradeoffs.append(f"มีกลุ่มที่ที่นั่งเต็ม ต้องขอโควตาเพิ่ม: {', '.join(full_secs)}")
            if relax_preferences:
                tradeoffs.append("ผ่อนปรนความชอบเรื่องวันว่างหรือคาบเช้าเพื่อให้จัดตารางได้")
            if relax_min_credits and tot_cr < settings.default_min_credits:
                tradeoffs.append(f"ผ่อนปรนหน่วยกิตต่ำสุด (ลงได้ {tot_cr} หน่วยกิต)")

            plan_name = f"ทางเลือกที่ {plan_num}"
            if plan_num == 1:
                plan_name += " (แนะนำ - คะแนนสูงสุด)"
            elif prof["days_on_campus"] <= 3:
                plan_name += f" (เน้นวันว่าง - เรียน {prof['days_on_campus']} วัน)"

            candidates.append(
                CandidatePlan(
                    plan_index=plan_num,
                    name=plan_name,
                    total_credits=tot_cr,
                    score=float(solver.ObjectiveValue()),
                    sections=[s.id for s in chosen_sections],
                    section_details=chosen_sections,
                    summary=ValidationSummary(
                        total_credits=tot_cr,
                        section_count=len(chosen_sections),
                        is_valid=True,
                        days_on_campus=prof["days_on_campus"],
                        free_days=prof["free_days"],
                    ),
                    warnings=warns,
                    tradeoffs_made=tradeoffs,
                )
            )
        else:
            break

    return candidates, (allow_full_seats or relax_min_credits or relax_preferences)


def generate_schedule_plans(
    available_sections: list[SectionInput],
    term: str = "1/2569",
    preferences: StudentPreferences | None = None,
    student: StudentContextInput | None = None,
    must_include: list[str] | None = None,
    exclude: list[str] | None = None,
    max_candidates: int = 5,
) -> GeneratePlanResponse:
    """ฟังก์ชันหลักสำหรับจัดตารางเรียนอัตโนมัติ พร้อมระบบ Relaxation อัตโนมัติ 3 ระดับ"""
    # ระดับปกติ (Strict Rules)
    plans, relaxed = build_and_solve_plan(
        available_sections,
        term=term,
        preferences=preferences,
        student=student,
        must_include=must_include,
        exclude=exclude,
        max_candidates=max_candidates,
    )

    if plans:
        return GeneratePlanResponse(
            status="success",
            term=term,
            plans_count=len(plans),
            plans=plans,
            relaxed=False,
        )

    # Relaxation ชั้นที่ 1: ผ่อนปรนความชอบ (Preferences)
    plans, _ = build_and_solve_plan(
        available_sections,
        term=term,
        preferences=preferences,
        student=student,
        must_include=must_include,
        exclude=exclude,
        max_candidates=max_candidates,
        relax_preferences=True,
    )

    if plans:
        return GeneratePlanResponse(
            status="success_relaxed_preferences",
            term=term,
            plans_count=len(plans),
            plans=plans,
            relaxed=True,
        )

    # Relaxation ชั้นที่ 2: ผ่อนปรนเรื่องที่นั่งเต็ม
    plans, _ = build_and_solve_plan(
        available_sections,
        term=term,
        preferences=preferences,
        student=student,
        must_include=must_include,
        exclude=exclude,
        max_candidates=max_candidates,
        allow_full_seats=True,
        relax_preferences=True,
    )

    if plans:
        return GeneratePlanResponse(
            status="success_relaxed_seats",
            term=term,
            plans_count=len(plans),
            plans=plans,
            relaxed=True,
        )

    # Relaxation ชั้นที่ 3: ผ่อนปรนหน่วยกิตต่ำสุด
    plans, _ = build_and_solve_plan(
        available_sections,
        term=term,
        preferences=preferences,
        student=student,
        must_include=must_include,
        exclude=exclude,
        max_candidates=max_candidates,
        allow_full_seats=True,
        relax_preferences=True,
        relax_min_credits=True,
    )

    return GeneratePlanResponse(
        status="success_relaxed_all" if plans else "infeasible",
        term=term,
        plans_count=len(plans),
        plans=plans,
        relaxed=True,
    )
