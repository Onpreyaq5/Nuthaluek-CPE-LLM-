"""POST /api/validate — ตรวจตารางชนของหมู่เรียนที่เลือก

body: {term, section_ids[], passed_courses[]}
คืนรหัสปัญหา C1-C6 และคำเตือน W1-W5 แบบเดียวกับโมดูล 06
"""
from _core.conflicts import detect_conflicts
from _core.http import JsonHandler
from _core.store import load_timetable, resolve_sections


class handler(JsonHandler):
    def post(self, body: dict) -> dict:
        term = body.get("term", "1/2569")
        ids = body.get("section_ids") or []
        if not isinstance(ids, list):
            raise ValueError("section_ids ต้องเป็น list")

        sections, missing = resolve_sections([str(i) for i in ids], term)
        result = detect_conflicts(
            sections,
            passed_courses=body.get("passed_courses") or [],
            term=term,
            all_sections=load_timetable(term)["sections"],
        )
        result["ok"] = True
        result["term"] = term
        result["unknown_section_ids"] = missing
        return result
