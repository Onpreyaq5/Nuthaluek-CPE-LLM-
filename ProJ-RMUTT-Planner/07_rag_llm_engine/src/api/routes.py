"""Endpoint ของโมดูล 07

path ต้องตรงกับที่โมดูล 03 (ai_router_agent) เรียกใช้:
  POST /knowledge/search   <- tools.search_knowledge()
  POST /generate           <- tools.answer_with_llm()
"""
from __future__ import annotations

import json
import logging
from pathlib import Path

from fastapi import APIRouter, HTTPException

from ..config import settings
from ..models.schemas import (
    ExplainPlanRequest,
    ExplainPlanResponse,
    GenerateRequest,
    GenerateResponse,
    IngestResponse,
    KnowledgeSearchRequest,
    KnowledgeSearchResponse,
)
from ..services.explainer import explain_plan
from ..services.generator import answer
from ..services.knowledge import knowledge_base

log = logging.getLogger(__name__)
router = APIRouter()


@router.get("/health")
def health() -> dict:
    return {
        "ok": True,
        "service": "07_rag_llm_engine",
        "documents": len(knowledge_base.documents),
        "files": knowledge_base.files,
        "llm_provider": settings.llm_provider if settings.llm_enabled else "rule_based",
    }


@router.post("/knowledge/search", response_model=KnowledgeSearchResponse)
def knowledge_search(req: KnowledgeSearchRequest) -> KnowledgeSearchResponse:
    """ค้นเอกสารระเบียบ/หลักสูตรแบบผสม BM25 + vector"""
    chunks = knowledge_base.search(
        req.query,
        top_k=req.top_k,
        doc_type=req.doc_type,
        effective_year=req.effective_year,
        program_id=req.program_id,
    )
    top = chunks[0].score if chunks else 0.0
    return KnowledgeSearchResponse(
        query=req.query,
        found=bool(chunks) and top >= settings.min_score,
        chunks=chunks,
        top_score=top,
    )


@router.post("/generate", response_model=GenerateResponse)
async def generate(req: GenerateRequest) -> GenerateResponse:
    """ตอบคำถามโดยอิงเอกสาร พร้อมแนบแหล่งอ้างอิง"""
    return await answer(req)


@router.post("/explain/plan", response_model=ExplainPlanResponse)
def explain(req: ExplainPlanRequest) -> ExplainPlanResponse:
    """แปลงผลตรวจตารางชนจากโมดูล 06 เป็นคำอธิบายภาษาคน"""
    return explain_plan(req)


@router.post("/ingest", response_model=IngestResponse)
def ingest() -> IngestResponse:
    """โหลดเอกสารใหม่ (ใช้หลังเพิ่ม/แก้ไฟล์ใน data/knowledge)"""
    count = knowledge_base.load()
    return IngestResponse(
        documents=len(knowledge_base.files),
        chunks=count,
        files=knowledge_base.files,
    )


@router.get("/seed/timetable")
def seed_timetable(term: str = "1/2569") -> dict:
    """ตารางสอนจำลองของสาขาวิศวกรรมคอมพิวเตอร์ สำหรับเดโม่/ทดสอบ

    ส่งต่อให้โมดูล 06 (`POST /conflicts/check`, `POST /plans/auto`) ได้ทันที
    เพราะโครงสร้างตรงกับ SectionInput
    """
    filename = f"cpe_timetable_{term.replace('/', '_')}.json"
    path = Path(settings.seed_dir) / filename
    if not path.exists():
        raise HTTPException(status_code=404, detail=f"ไม่พบไฟล์ข้อมูลจำลอง {filename}")
    return json.loads(path.read_text(encoding="utf-8"))
