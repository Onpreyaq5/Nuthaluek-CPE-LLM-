"""สร้างคำตอบจากคำถาม + เอกสารที่ค้นเจอ (RAG)

ด่านกันมั่ว (anti-hallucination) 3 ชั้น
1. ถ้าคะแนนค้นคืนสูงสุดต่ำกว่าเกณฑ์ -> ตอบว่าไม่พบข้อมูล ไม่เรียก LLM เลย
2. prompt สั่งให้ตอบเฉพาะจากเอกสาร และให้อ้างหมายเลขเอกสาร
3. คำตอบทุกครั้งแนบ sources กลับไป เพื่อให้ผู้ใช้กดดูต้นทางได้
"""
from __future__ import annotations

from ..config import DISCLAIMER, NOT_FOUND_MESSAGE, settings
from ..llm.client import generate as llm_generate
from ..models.schemas import GenerateRequest, GenerateResponse, Source
from .knowledge import knowledge_base


def _to_sources(chunks) -> list[Source]:
    return [
        Source(
            doc_id=c.doc_id, title=c.title, section=c.section,
            doc_type=c.doc_type, effective_year=c.effective_year, score=c.score,
        )
        for c in chunks
    ]


# คำที่ใช้ขยายคำถาม — ต้องเป็นวลีที่ "ยาวพอจะไม่ไปพ้องกับคำอื่น"
# เช่น ห้ามใช้คำว่า "ชน" เฉย ๆ เพราะไปตรงกับ "ชนะ" ใน "ทีมไหนชนะ"
# ทำให้คำถามนอกเรื่องถูกดันคะแนนขึ้นจนผ่านเกณฑ์ (เคยเป็นบั๊กจริง)
QUERY_EXPANSIONS: dict[str, str] = {
    "ถอนรายวิชา": "ถอนรายวิชา สัญลักษณ์ W กำหนดเวลา",
    "ถอนวิชา": "ถอนรายวิชา สัญลักษณ์ W กำหนดเวลา",
    "เพิ่มรายวิชา": "เพิ่มรายวิชา กำหนดเวลา",
    "เพิ่มวิชา": "เพิ่มรายวิชา กำหนดเวลา",
    "กี่หน่วยกิต": "จำนวนหน่วยกิตต่อภาคการศึกษา ขั้นต่ำ สูงสุด",
    "หน่วยกิต": "จำนวนหน่วยกิตต่อภาคการศึกษา",
    "ตารางชน": "เวลาเรียนซ้ำซ้อน เวลาสอบตรงกัน",
    "เรียนชน": "เวลาเรียนซ้ำซ้อน เวลาสอบตรงกัน",
    "ชนกัน": "เวลาเรียนซ้ำซ้อน เวลาสอบตรงกัน",
    "ซ้ำซ้อน": "เวลาเรียนซ้ำซ้อน เวลาสอบตรงกัน",
    "จะจบ": "เกณฑ์สำเร็จการศึกษา หน่วยกิตสะสม GPAX",
    "เรียนจบ": "เกณฑ์สำเร็จการศึกษา หน่วยกิตสะสม GPAX",
    "สำเร็จการศึกษา": "เกณฑ์สำเร็จการศึกษา หน่วยกิตสะสม GPAX",
    "รีไทร์": "พ้นสภาพนักศึกษา ระยะเวลาศึกษา GPAX",
    "พ้นสภาพ": "พ้นสภาพนักศึกษา ระยะเวลาศึกษา GPAX",
    "บังคับก่อน": "รายวิชาบังคับก่อน prerequisite",
    "ที่นั่งเต็ม": "ที่นั่งเต็ม ขอเพิ่มที่นั่ง หมู่เรียน",
    "ตารางสอบ": "ตารางสอบ กลางภาค ปลายภาค",
    "สอบกลางภาค": "ตารางสอบ กลางภาค",
    "สอบปลายภาค": "ตารางสอบ ปลายภาค",
}


def _expand_query(question: str) -> str:
    """ขยายคำถามสั้น ๆ ให้ค้นเจอง่ายขึ้น (คำถามนักศึกษามักสั้นมาก)"""
    q = question.strip()
    extra = [v for k, v in QUERY_EXPANSIONS.items() if k in q]
    return f"{q} {' '.join(dict.fromkeys(extra))}".strip() if extra else q


async def answer(req: GenerateRequest) -> GenerateResponse:
    student = req.context.get("student") or {}
    effective_year = student.get("curriculum_year") or student.get("effective_year")
    program_id = student.get("program_id")

    chunks = knowledge_base.search(
        _expand_query(req.question),
        top_k=req.top_k,
        effective_year=effective_year if isinstance(effective_year, int) else None,
        program_id=program_id if isinstance(program_id, str) else None,
    )

    top_score = chunks[0].score if chunks else 0.0
    # ── ด่านที่ 1: ไม่มีหลักฐานพอ -> ไม่ตอบ ────────────────────
    if not chunks or top_score < settings.min_score:
        return GenerateResponse(
            answer=NOT_FOUND_MESSAGE,
            sources=[],
            grounded=False,
            provider="none",
            disclaimer=DISCLAIMER,
        )

    text, provider = await llm_generate(req.question, chunks, req.context)
    if not text:
        return GenerateResponse(
            answer=NOT_FOUND_MESSAGE, sources=[], grounded=False,
            provider=provider, disclaimer=DISCLAIMER,
        )

    return GenerateResponse(
        answer=text,
        sources=_to_sources(chunks),
        grounded=True,
        provider=provider,
        disclaimer=DISCLAIMER,
    )
