"""04_course_data_services — ข้อมูลรายวิชาและกลุ่มเรียน (ดู store.py)"""
from prometheus_fastapi_instrumentator import Instrumentator
from fastapi import FastAPI, Query
from typing import Optional
from pydantic import BaseModel

from .store import course_store

app = FastAPI(title="04_course_data_services")

# /metrics ให้ Prometheus (ช่อง Monitoring ในแผนภาพ)
Instrumentator().instrument(app).expose(app, endpoint="/metrics", include_in_schema=False)

@app.get("/health")
def health():
    return {
        "ok": True,
        "service": "04_course_data_services",
        # "mock" = ไม่ได้ต่อตารางสอนจริง ใช้ข้อมูลตัวอย่าง 2 วิชา
        "source": course_store.source,
        "terms": {t: len(course_store.sections(t)) for t in course_store.terms},
    }


@app.get("/terms")
def list_terms():
    return {"items": course_store.terms}


# ── สำหรับ 02 (schemas/courses.py) ───────────────────────────────
@app.get("/courses")
def list_courses(
    q: str | None = None,
    term: str | None = None,
    day: str | None = None,
    teacher: str | None = None,
    cursor: str | None = None,
    limit: int = Query(default=20, le=100),
):
    items, next_cursor = course_store.search_courses(q, term, day, teacher, cursor, limit)
    return {"items": items, "next_cursor": next_cursor}


@app.get("/courses/{code}/sections")
def list_sections(code: str, term: str | None = None):
    return {"items": course_store.get_sections(code, term), "next_cursor": None}


@app.post("/sections/bulk")
def sections_bulk(payload: dict):
    return {"items": course_store.get_sections_by_ids(payload.get("ids") or [], payload.get("term"))}


# ── สำหรับ 06 (adapters/course_data.py) ──────────────────────────
@app.post("/sections/batch")
def sections_batch(payload: dict):
    """06 ตรวจตารางชน: ขอ section เต็มรูปแบบ (เวลาเป็นนาที วันเป็นเลข) ตาม id
    id ที่ไม่มีจะไม่อยู่ในผล 06 เป็นคนแจ้ง SECTION_NOT_FOUND เอง"""
    ids = payload.get("section_ids") or payload.get("ids") or []
    return {"sections": course_store.get_engine_sections_by_ids(ids, payload.get("term"))}


# ── ใช้ร่วมกันระหว่าง 03 และ 06 ──────────────────────────────────
@app.post("/courses/search")
def search_courses(payload: dict):
    """03 (tools.search_courses) ส่ง {q, term} และอ่าน "items"
    06 (จัดตารางอัตโนมัติ) ส่ง {term, course_codes} และอ่าน "sections"
    ตอบทั้งสองแบบในก้อนเดียว ก่อนหน้านี้ตอบแค่ items ทำให้ 06 ได้ 0 วิชาและจัดแผนไม่ได้เลย"""
    q = payload.get("q") or ""
    term = payload.get("term")
    codes = payload.get("course_codes") or []
    items, _ = course_store.search_courses(q=q, term=term, day=None, teacher=None, cursor=None, limit=50)
    return {"items": items, "sections": course_store.open_engine_sections(term, codes, q)}
