"""POST /api/validate — ตรวจตารางชนของหมู่เรียนที่เลือก

body: {term, section_ids[], passed_courses[]}
คืนรหัสปัญหา C1-C6 และคำเตือน W1-W5 แบบเดียวกับโมดูล 06
"""
from _core.conflicts import detect_conflicts
from _core.http import JsonHandler
from _core.store import load_timetable, resolve_sections

# ตรวจตารางชนเทียบทุกคู่ (O(n²)) ถ้าปล่อยให้ส่งมาเท่าไหร่ก็ได้ จะกลายเป็นช่องให้ยิงจนฟังก์ชันหมดเวลา
# นักศึกษาลงจริงเต็มที่ไม่ถึง 15 หมู่ เผื่อไว้ 60 ก็เกินพอแล้ว
MAX_SECTIONS = 60
MAX_PASSED = 400


def _str_list(value, field: str, limit: int) -> list[str]:
    if value is None:
        return []
    if not isinstance(value, list):
        raise ValueError(f"{field} ต้องเป็น list")
    if len(value) > limit:
        raise ValueError(f"{field} ส่งมาได้ไม่เกิน {limit} รายการ")
    return [str(v) for v in value]


class handler(JsonHandler):
    def post(self, body: dict) -> dict:
        term = body.get("term", "1/2569")
        ids = _str_list(body.get("section_ids"), "section_ids", MAX_SECTIONS)
        passed = _str_list(body.get("passed_courses"), "passed_courses", MAX_PASSED)

        sections, missing = resolve_sections(ids, term)
        result = detect_conflicts(
            sections,
            passed_courses=passed,
            term=term,
            all_sections=load_timetable(term)["sections"],
        )
        result["ok"] = True
        result["term"] = term
        result["unknown_section_ids"] = missing
        return result
