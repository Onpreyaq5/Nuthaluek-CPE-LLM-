"""สรุปผลจากเครื่องมือที่โมดูล 03 เรียกมาแล้ว เป็นคำตอบภาษาคน

ใช้กับคำถามตรวจตารางชน / จัดแผน / ค้นรายวิชา ซึ่งคำตอบที่ถูกต้องมาจากระบบ
ไม่ได้มาจากเอกสาร ถ้าส่งไปค้นเอกสารแทน จะได้ "ไม่พบข้อมูล" ทั้งที่ระบบมีคำตอบอยู่แล้ว

ทุกตัวเลขยกมาจากผลของโมดูล 04/06 ตรง ๆ ไม่คำนวณใหม่
รูปแบบผลของแต่ละโมดูลยังขยับได้ จึงอ่านแบบยืดหยุ่น (ลองหลายชื่อ key)
และถ้าอ่านไม่ออกเลยให้คืน None เพื่อให้ผู้เรียกไปใช้ทางค้นเอกสารตามปกติ
"""
from __future__ import annotations

from typing import Any

from ..models.schemas import Source

MAX_ITEMS = 8


def _first(d: dict, *keys: str, default: Any = None) -> Any:
    for k in keys:
        v = d.get(k)
        if v not in (None, "", []):
            return v
    return default


def _source(module: str, title: str, section: str = "") -> Source:
    return Source(doc_id=f"system:{module}", title=title, section=section, doc_type="system", score=1.0)


def _conflicts(result: dict) -> tuple[str, list[Source]] | None:
    data = result.get("data") if isinstance(result.get("data"), dict) else result
    conflicts = _first(data, "conflicts", "errors", default=[])
    warnings = _first(data, "warnings", default=[])
    has = data.get("has_conflict")
    if has is None:
        has = bool(conflicts)
    if not isinstance(conflicts, list) or not isinstance(warnings, list):
        return None

    lines: list[str] = []
    if has:
        lines.append(f"ตรวจแล้วพบปัญหา {len(conflicts)} ข้อ:")
        for c in conflicts[:MAX_ITEMS]:
            if isinstance(c, dict):
                code = _first(c, "code", default="")
                msg = _first(c, "message", "message_th", "description", "detail", default="")
                lines.append(f"• {code} {msg}".rstrip())
    else:
        lines.append("ตรวจแล้วไม่พบเวลาเรียนหรือเวลาสอบชนกัน")
    if warnings:
        lines.append("")
        lines.append(f"ข้อควรระวัง {len(warnings)} ข้อ:")
        for w in warnings[:MAX_ITEMS]:
            if isinstance(w, dict):
                code = _first(w, "code", default="")
                msg = _first(w, "message", "message_th", "description", "detail", default="")
                lines.append(f"• {code} {msg}".rstrip())
    return "\n".join(lines), [_source("06", "ระบบตรวจตารางชน (โมดูล 06)", "C1–C6 / W1–W5")]


def _plans(result: dict) -> tuple[str, list[Source]] | None:
    data = result.get("data") if isinstance(result.get("data"), dict) else result
    plans = _first(data, "plans", "candidates", "items", default=[])
    if not isinstance(plans, list):
        return None
    if not plans:
        return "จัดตารางอัตโนมัติแล้วยังไม่พบแผนที่ลงตัวตามเงื่อนไข ลองลดเงื่อนไขหรือเลือกวิชาน้อยลง", [
            _source("06", "ระบบจัดตารางอัตโนมัติ (โมดูล 06)")
        ]
    lines = [f"จัดตารางให้ได้ {len(plans)} แบบ:"]
    for i, p in enumerate(plans[:5], start=1):
        if not isinstance(p, dict):
            continue
        credits = _first(p, "total_credits", "credits", default="?")
        sections = _first(p, "sections", "section_ids", "items", default=[])
        n = len(sections) if isinstance(sections, list) else "?"
        score = p.get("score")
        tail = f" · คะแนน {score}" if score is not None else ""
        lines.append(f"{i}. {n} กลุ่มเรียน · {credits} หน่วยกิต{tail}")
    return "\n".join(lines), [_source("06", "ระบบจัดตารางอัตโนมัติ (โมดูล 06)", "CP-SAT")]


def _courses(result: dict) -> tuple[str, list[Source]] | None:
    items = _first(result, "items", "courses", "results", default=[])
    if not isinstance(items, list):
        return None
    if not items:
        return "ไม่พบรายวิชาที่ตรงกับคำค้นในภาคการศึกษานี้", [_source("04", "ข้อมูลรายวิชา (โมดูล 04)")]
    lines = [f"พบ {len(items)} รายวิชา:"]
    for c in items[:MAX_ITEMS]:
        if not isinstance(c, dict):
            continue
        code = _first(c, "course_code", "code", "id", default="")
        name = _first(c, "name_th", "course_name", "name", "title", default="")
        credits = _first(c, "credits", "credit", default=None)
        tail = f" ({credits} หน่วยกิต)" if credits is not None else ""
        lines.append(f"• {code} {name}{tail}".rstrip())
    if len(items) > MAX_ITEMS:
        lines.append(f"…และอีก {len(items) - MAX_ITEMS} วิชา")
    return "\n".join(lines), [_source("04", "ข้อมูลรายวิชา (โมดูล 04)")]


# ลำดับสำคัญ: ถ้ามีผลตรวจชน นั่นคือสิ่งที่ถาม ส่วนค้นวิชาเป็นขั้นประกอบของการจัดแผน
_FORMATTERS = (
    ("check_conflicts", _conflicts),
    ("generate_plan", _plans),
    ("search_courses", _courses),
)


def answer_from_tools(tool_results: Any) -> tuple[str, list[Source]] | None:
    if not isinstance(tool_results, dict):
        return None
    for name, fmt in _FORMATTERS:
        result = tool_results.get(name)
        if isinstance(result, dict):
            out = fmt(result)
            if out is not None:
                return out
    return None
