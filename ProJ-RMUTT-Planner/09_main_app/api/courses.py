"""GET /api/courses — รายวิชาและหมู่เรียนที่เปิดสอน

พารามิเตอร์
  term   ภาคการศึกษา เช่น 1/2569 (ค่าเริ่มต้น 1/2569)
  q      คำค้น รหัสวิชาหรือชื่อวิชา
  year   กรองตามชั้นปีที่แนะนำ
  day    กรองวันที่เรียน (0=จันทร์ .. 6=อาทิตย์)
"""
from _core.http import JsonHandler
from _core.store import available_terms, courses_index, load_timetable


class handler(JsonHandler):
    def get(self, query: dict) -> dict:
        term = query.get("term", "1/2569")
        rows = courses_index(term)

        q = (query.get("q") or "").strip().lower()
        if q:
            rows = [r for r in rows
                    if q in r["course_code"].lower() or q in r["course_name"].lower()]

        year = query.get("year")
        if year and year.isdigit():
            rows = [r for r in rows if r.get("suggested_year") == int(year)]

        day = query.get("day")
        if day and day.isdigit():
            d = int(day)
            rows = [r for r in rows
                    if any(m["day"] == d for s in r["sections"] for m in s["meetings"])]

        meta = load_timetable(term)
        return {
            "ok": True,
            "term": term,
            "term_start": meta.get("term_start"),
            "weeks": meta.get("weeks", 16),
            "available_terms": available_terms(),
            "credit_rule": meta["credit_rule"],
            "disclaimer": meta["disclaimer"],
            "total": len(rows),
            "courses": rows,
        }
