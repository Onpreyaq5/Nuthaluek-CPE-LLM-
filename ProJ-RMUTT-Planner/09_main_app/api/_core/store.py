"""โหลดข้อมูลที่ bundle ไปกับฟังก์ชัน — ตารางสอน + คลังความรู้

ข้อมูลชุดเดียวกับโมดูล 07 (data/seed, data/knowledge) คัดลอกมาไว้ใน 09
เพราะ Vercel ต้อง bundle ไฟล์ไปกับฟังก์ชัน อ้างข้ามโฟลเดอร์ไม่ได้
ถ้าแก้ข้อมูลที่ 07 ให้รัน `npm run sync-data` เพื่อคัดลอกมาใหม่
"""
from __future__ import annotations

import json
import re
from functools import lru_cache
from pathlib import Path

# .../09_main_app/api/_core/store.py -> .../09_main_app
BASE_DIR = Path(__file__).resolve().parents[2]
DATA_DIR = BASE_DIR / "data"

# เทอมที่รับได้มีรูปแบบเดียวคือ <ภาค>/<ปีพ.ศ.> เช่น 1/2569
TERM_RE = re.compile(r"^[1-3]/25\d{2}$")


def safe_term(term: str) -> str:
    """ตรวจ term ก่อนเอาไปประกอบชื่อไฟล์

    term มาจากผู้ใช้ตรง ๆ ถ้าปล่อยผ่านจะเอา .. หรือ \\ มาไต่ออกนอกโฟลเดอร์ data ได้
    (เช่น "..\\..\\x" บน Windows) จึงบังคับรูปแบบ แล้วเทียบกับรายการเทอมที่มีจริงอีกชั้น
    """
    term = (term or "").strip()
    if not TERM_RE.match(term) or term not in available_terms():
        raise FileNotFoundError(f"ไม่มีข้อมูลภาคการศึกษา {term or '(ว่าง)'}")
    return term


@lru_cache(maxsize=8)
def load_timetable(term: str = "1/2569") -> dict:
    """อ่านตารางสอนของภาคการศึกษาที่ระบุ"""
    name = f"cpe_timetable_{safe_term(term).replace('/', '_')}.json"
    path = DATA_DIR / "seed" / name
    if not path.exists():
        raise FileNotFoundError(name)
    return json.loads(path.read_text(encoding="utf-8"))


@lru_cache(maxsize=1)
def available_terms() -> list[str]:
    seed = DATA_DIR / "seed"
    if not seed.exists():
        return []
    return sorted(
        p.stem.replace("cpe_timetable_", "").replace("_", "/")
        for p in seed.glob("cpe_timetable_*.json")
    )


@lru_cache(maxsize=8)
def sections_by_id(term: str = "1/2569") -> dict[str, dict]:
    return {s["id"]: s for s in load_timetable(term)["sections"]}


def resolve_sections(section_ids: list[str], term: str = "1/2569") -> tuple[list[dict], list[str]]:
    """แปลงรายการรหัสหมู่เรียนเป็นข้อมูลเต็ม คืน (ที่เจอ, ที่ไม่เจอ)"""
    table = sections_by_id(term)
    found, missing = [], []
    for sid in section_ids:
        if sid in table:
            found.append(table[sid])
        else:
            missing.append(sid)
    return found, missing


def courses_index(term: str = "1/2569") -> list[dict]:
    """สรุปรายวิชา (หนึ่งแถวต่อหนึ่งวิชา) พร้อมหมู่เรียนทั้งหมด — ใช้แสดงหน้าค้นหา"""
    data = load_timetable(term)
    grouped: dict[str, dict] = {}
    for s in data["sections"]:
        row = grouped.setdefault(s["course_code"], {
            "course_code": s["course_code"],
            "course_name": s["course_name"],
            "credits": s["credits"],
            "category": s.get("category", ""),
            "suggested_year": s.get("suggested_year"),
            "prerequisites": s.get("prerequisites", []),
            "sections": [],
        })
        row["sections"].append({
            "id": s["id"],
            "section": s["section"],
            "meetings": s["meetings"],
            "exams": s.get("exams", []),
            "seat_total": s.get("seat_total"),
            "seat_taken": s.get("seat_taken"),
            "seat_left": (s["seat_total"] - s["seat_taken"])
            if s.get("seat_total") is not None and s.get("seat_taken") is not None else None,
            "teachers": s.get("teachers", []),
            "slots_mask": s.get("slots_mask"),
        })
    for row in grouped.values():
        row["sections"].sort(key=lambda x: x["section"])
    return sorted(grouped.values(), key=lambda r: r["course_code"])
