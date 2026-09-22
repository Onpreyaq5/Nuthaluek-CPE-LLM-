"""POST /api/autoplan — ให้ระบบจัดตารางให้

body: {term, student_year, passed_courses[], retake_courses[], locked_section_ids[],
       preferences:{avoid_morning, free_days[], max_credits, min_credits}}
"""
from _core.http import JsonHandler
from _core.planner import generate_plan
from _core.store import load_timetable


class handler(JsonHandler):
    def post(self, body: dict) -> dict:
        term = body.get("term", "1/2569")
        data = load_timetable(term)
        year = body.get("student_year")
        result = generate_plan(
            data["sections"],
            term=term,
            passed_courses=body.get("passed_courses") or [],
            retake_courses=body.get("retake_courses") or [],
            student_year=int(year) if str(year).isdigit() else None,
            preferences=body.get("preferences") or {},
            locked_section_ids=body.get("locked_section_ids") or [],
        )
        result["ok"] = True
        result["term"] = term
        return result
