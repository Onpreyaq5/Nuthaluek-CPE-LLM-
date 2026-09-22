"""สร้างคำตอบจากคำถาม + เอกสารที่ค้นเจอ (RAG)

ด่านกันมั่ว (anti-hallucination) 4 ชั้น
0. ถ้าถามเรื่องที่คลังไม่มีข้อมูลตั้งแต่แรก (เช่น ตารางสอน อาจารย์ที่ปรึกษา)
   -> บอกตรง ๆ ว่าไม่มี พร้อมชี้ว่าไปหาที่ไหนได้ ดู services/coverage.py
1. ถ้าคะแนนค้นคืนสูงสุดต่ำกว่าเกณฑ์ -> ตอบว่าไม่พบข้อมูล ไม่เรียก LLM เลย
2. prompt สั่งให้ตอบเฉพาะจากเอกสาร และให้อ้างหมายเลขเอกสาร
3. คำตอบทุกครั้งแนบ sources กลับไป เพื่อให้ผู้ใช้กดดูต้นทางได้
   และ sources ต้องเป็น "เอกสารที่ถูกใช้สร้างคำตอบจริง" เท่านั้น ไม่ใช่ผลค้นทั้งหมด
"""
from __future__ import annotations

from ..config import DISCLAIMER, NOT_FOUND_MESSAGE, settings
from ..core.metrics import RETRIEVAL_TOP_SCORE
from ..llm.client import general_answer
from ..llm.client import generate as llm_generate
from ..models.schemas import GenerateRequest, GenerateResponse, Source
from .coverage import find_gap
from .knowledge import knowledge_base
from .tool_answer import answer_from_tools

# ช่อง AI ในกล่อง 4 ของแผนภาพ — โมดูล 03 เป็นคนเลือกแล้วส่งมาใน context["ai_target"]
AI_UNIVERSITY_RAG = "university_rag"
AI_GENERAL = "general_ai"
AI_LOCAL = "local_ai"

GENERAL_NOTE = "คำตอบนี้มาจากความรู้ทั่วไปของโมเดล ไม่ได้อ้างอิงเอกสารของมหาวิทยาลัย"


def _to_sources(chunks) -> list[Source]:
    return [
        Source(
            doc_id=c.doc_id, title=c.title, section=c.section,
            doc_type=c.doc_type, effective_year=c.effective_year, score=c.score,
        )
        for c in chunks
    ]


async def answer(req: GenerateRequest) -> GenerateResponse:
    """เลือกทางตาม AI ที่ 03 เลือกไว้ ไม่ระบุ = University RAG (พฤติกรรมเดิมทุกประการ)"""
    target = str(req.context.get("ai_target") or AI_UNIVERSITY_RAG)

    if target in (AI_GENERAL, AI_LOCAL):
        history = req.context.get("history")
        text, provider = await general_answer(
            req.question, history if isinstance(history, list) else None
        )
        return GenerateResponse(
            answer=text,
            sources=[],
            # ไม่ได้อ้างเอกสาร จึงไม่นับว่า grounded ผู้ใช้ต้องเห็นความต่างนี้
            grounded=False,
            provider=provider,
            disclaimer=GENERAL_NOTE,
        )

    # คำถามตารางชน/จัดแผน/ค้นวิชา: 03 เรียกเครื่องมือมาแล้ว สรุปจากผลจริงของเครื่องมือ
    # ห้ามให้โมเดลคำนวณเวลาหรือหน่วยกิตเอง
    from_tools = answer_from_tools(req.context.get("tool_results"))
    if from_tools is not None:
        text, sources = from_tools
        return GenerateResponse(
            answer=text, sources=sources, grounded=True,
            provider="tools", disclaimer=DISCLAIMER,
        )

    return await _answer_from_documents(req)


async def _answer_from_documents(req: GenerateRequest) -> GenerateResponse:
    # ── ด่านที่ 0: รู้ตัวว่าไม่มีข้อมูลเรื่องนี้ ────────────────
    # การค้นคืนวัดได้แค่ "เอกสารเกี่ยวข้องไหม" ไม่ได้วัดว่า "มีคำตอบไหม"
    # เรื่องที่คลังไม่มีข้อมูลตั้งแต่แรก ต้องบอกตรง ๆ ไม่ใช่ยกเอกสารใกล้เคียงมาให้
    gap = find_gap(req.question)
    if gap is not None:
        return GenerateResponse(
            answer=gap.message,
            sources=[],
            grounded=False,
            provider="coverage_gap",
            disclaimer=DISCLAIMER,
        )

    # 03 ส่งข้อมูลนักศึกษามาในชื่อ "profile" (context_manager.py) ส่วนผู้เรียกตรงใช้ "student"
    student = req.context.get("student") or req.context.get("profile") or {}
    if not isinstance(student, dict):
        student = {}
    effective_year = student.get("curriculum_year") or student.get("effective_year")
    program_id = student.get("program_id")

    chunks = knowledge_base.search(
        req.question,
        top_k=req.top_k,
        effective_year=effective_year if isinstance(effective_year, int) else None,
        program_id=program_id if isinstance(program_id, str) else None,
    )

    top_score = chunks[0].score if chunks else 0.0
    RETRIEVAL_TOP_SCORE.observe(top_score)
    # ── ด่านที่ 1: ไม่มีหลักฐานพอ -> ไม่ตอบ ────────────────────
    if not chunks or top_score < settings.min_score:
        return GenerateResponse(
            answer=NOT_FOUND_MESSAGE,
            sources=[],
            grounded=False,
            provider="none",
            disclaimer=DISCLAIMER,
        )

    text, provider, used = await llm_generate(req.question, chunks, req.context)
    if not text:
        return GenerateResponse(
            answer=NOT_FOUND_MESSAGE, sources=[], grounded=False,
            provider=provider, disclaimer=DISCLAIMER,
        )

    return GenerateResponse(
        answer=text,
        sources=_to_sources(used),
        grounded=True,
        provider=provider,
        disclaimer=DISCLAIMER,
    )
