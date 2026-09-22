"""04_course_data_services — service skeleton"""
from fastapi import FastAPI, Query
from typing import Optional
from pydantic import BaseModel

from .store import course_store

app = FastAPI(title="04_course_data_services")

@app.get("/health")
def health():
    return {"ok": True, "service": "04_course_data_services"}

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
    items = course_store.get_sections(code, term)
    return {"items": items, "next_cursor": None}

@app.post("/sections/bulk")
def sections_bulk(payload: dict):
    ids = payload.get("ids", [])
    return {"items": course_store.get_sections_by_ids(ids)}

@app.post("/courses/search")
def search_courses_for_03(payload: dict):
    """path ที่ 03's tools.py เรียกจริง"""
    q = payload.get("q", "")
    term = payload.get("term")
    items, _ = course_store.search_courses(q=q, term=term, day=None, teacher=None, cursor=None, limit=20)
    return {"items": items}
