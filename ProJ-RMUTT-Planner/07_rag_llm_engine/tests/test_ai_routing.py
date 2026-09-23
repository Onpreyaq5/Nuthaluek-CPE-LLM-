"""กล่อง 4 ในแผนภาพ: 07 ต้องตอบตาม AI ที่ 03 เลือก และ Vector DB ล่มต้องไม่ทำให้ค้นไม่ได้"""
from __future__ import annotations

import asyncio

import pytest

from src.config import settings
from src.core.qdrant_index import QdrantVectorIndex
from src.core.retrieval import HybridRetriever
from src.llm.client import GENERAL_UNAVAILABLE
from src.models.schemas import GenerateRequest
from src.services.generator import answer
from src.services.knowledge import knowledge_base, load_documents
from src.services.tool_answer import answer_from_tools


@pytest.fixture(autouse=True)
def _loaded_knowledge_base():
    # service โหลดคลังตอน startup (lifespan) แต่เทสนี้เรียก answer() ตรง จึงต้องโหลดเอง
    if not knowledge_base.ready:
        knowledge_base.load()


def _run(req: GenerateRequest):
    return asyncio.run(answer(req))


def test_no_target_keeps_rag_behaviour():
    res = _run(GenerateRequest(question="ถอนรายวิชาได้ถึงเมื่อไหร่", context={}))
    assert res.grounded is True
    assert res.sources


def test_general_ai_without_any_model_says_so(monkeypatch):
    monkeypatch.setattr(settings, "llm_api_key", "")
    monkeypatch.setattr(settings, "local_model_url", "")
    res = _run(GenerateRequest(question="สวัสดีครับ", context={"ai_target": "general_ai"}))
    assert res.answer == GENERAL_UNAVAILABLE
    assert res.provider == "none"
    # ไม่ได้อ้างเอกสาร ห้ามติดป้าย grounded
    assert res.grounded is False and res.sources == []


def test_general_ai_falls_back_to_local_model(monkeypatch):
    monkeypatch.setattr(settings, "llm_api_key", "")
    monkeypatch.setattr(settings, "local_model_url", "http://local_ai:11434")

    async def fake_local(prompt: str) -> str:
        assert "ผู้ใช้: สวัสดีครับ" in prompt
        return "สวัสดีครับ ผมเป็นผู้ช่วย"

    monkeypatch.setattr("src.llm.client.call_local", fake_local)
    res = _run(GenerateRequest(question="สวัสดีครับ", context={"ai_target": "local_ai"}))
    assert res.answer.startswith("สวัสดีครับ")
    assert res.provider == f"local:{settings.local_model}"
    assert res.grounded is False


def test_regulation_question_never_goes_to_local_model(monkeypatch):
    """เรื่องระเบียบต้องยึดเอกสาร แม้จะมีโมเดลในเครื่องพร้อมใช้"""
    monkeypatch.setattr(settings, "local_model_url", "http://local_ai:11434")

    async def boom(prompt: str) -> str:  # pragma: no cover - ถ้าถูกเรียก = ผิด
        raise AssertionError("regulation answer must not use the local model")

    monkeypatch.setattr("src.llm.client.call_local", boom)
    res = _run(GenerateRequest(
        question="ถอนรายวิชาได้ถึงเมื่อไหร่", context={"ai_target": "university_rag"}
    ))
    assert res.grounded is True


def test_conflict_tool_result_is_summarised_not_searched():
    ctx = {"tool_results": {"check_conflicts": {
        "has_conflict": True,
        "conflicts": [{"code": "C1", "message": "เวลาเรียนชนกัน วันจันทร์ 09:00"}],
        "warnings": [],
    }}}
    res = _run(GenerateRequest(question="ลง CPE101 กับ CPE102 ชนไหม", context=ctx))
    assert res.provider == "tools"
    assert "C1" in res.answer and "พบปัญหา 1 ข้อ" in res.answer
    assert res.sources[0].doc_id == "system:06"


def test_unknown_tool_shape_falls_back_to_documents():
    assert answer_from_tools({"check_conflicts": {"weird": 1}}) is not None  # อ่านได้ = ไม่ชน
    assert answer_from_tools({"search_knowledge": {"chunks": []}}) is None
    assert answer_from_tools(None) is None


def test_qdrant_down_falls_back_to_memory_with_same_results():
    docs = load_documents(settings.knowledge_dir)
    memory = HybridRetriever(rrf_k=settings.rrf_k)
    memory.fit(docs)
    # พอร์ตที่ไม่มีใครฟัง = Qdrant ล่ม
    down = QdrantVectorIndex("http://127.0.0.1:9", "x", timeout=0.2)
    fallback = HybridRetriever(rrf_k=settings.rrf_k, vector=down)
    fallback.fit(docs)
    assert down.backend == "memory"
    q = "ถอนรายวิชาได้ถึงเมื่อไหร่"
    a = [(d.doc_id, round(s, 6)) for d, s in memory.search(q, top_k=6)]
    b = [(d.doc_id, round(s, 6)) for d, s in fallback.search(q, top_k=6)]
    assert a == b


def test_general_ai_busy_says_so_instead_of_weak_local_answer(monkeypatch):
    """มีคีย์ Gemini แต่ Gemini ล่ม: ตอบว่าไม่ว่าง ไม่ถอยไปโมเดลในเครื่องที่ช้าและตอบวน"""
    from src.llm import client

    monkeypatch.setattr(settings, "llm_provider", "gemini")
    monkeypatch.setattr(settings, "llm_api_key", "k")
    monkeypatch.setattr(settings, "local_model_url", "http://local_ai:11434")

    async def down(prompt: str) -> str:
        raise RuntimeError("503")

    async def boom(prompt: str) -> str:  # pragma: no cover
        raise AssertionError("must not fall back to the local model when a key is configured")

    monkeypatch.setitem(client._PROVIDERS, "gemini", down)
    monkeypatch.setattr("src.llm.client.call_local", boom)
    res = _run(GenerateRequest(question="สวัสดี", context={"ai_target": "general_ai"}))
    assert res.answer == client.GENERAL_BUSY
    assert res.provider == "gemini_unavailable"
