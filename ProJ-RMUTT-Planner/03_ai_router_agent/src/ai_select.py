"""เลือกว่าคำถามนี้ให้ AI ตัวไหนตอบ — กล่อง 4 ในแผนภาพสถาปัตยกรรม

    University RAG   คำถามเรื่องระเบียบ หลักสูตร ตาราง รายวิชา
                     ต้องตอบจากเอกสาร/ผลของระบบเท่านั้น (ด่านกันมั่ว 4 ชั้นของ 07)
    General AI       คุยทั่วไป เขียน สรุป อธิบายแนวคิด — Gemini ถ้ามีคีย์
    Local AI Model   โมเดลในเครื่องผ่าน Ollama
                     - จัดประเภทคำถามตอน keyword ไม่มั่นใจ (classifier.py)
                     - ตอบแทน General AI เมื่อไม่มีคีย์ Gemini

ทำไมเรื่องระเบียบไม่ให้ General AI หรือ Local AI ตอบ:
โมเดลทั่วไปไม่รู้ระเบียบของ มทร.ธัญบุรี แต่ตอบเต็มปากเหมือนรู้ ซึ่งอันตรายกว่าไม่ตอบ
"""
from __future__ import annotations

from .config import settings

UNIVERSITY_RAG = "university_rag"
GENERAL_AI = "general_ai"
LOCAL_AI = "local_ai"

_GENERAL_INTENTS = {"GENERAL_CHAT"}


def select_ai(intent: str) -> str:
    """intent -> AI ที่ควรตอบ"""
    if intent in _GENERAL_INTENTS:
        # ไม่มีคีย์ภายนอก แต่มีโมเดลในเครื่อง = งานทั่วไปตกไปที่ Local AI
        if not settings.llm_api_key and settings.local_model_url:
            return LOCAL_AI
        return GENERAL_AI
    return UNIVERSITY_RAG


def backing_model(target: str) -> str:
    """บอกว่าช่องนั้นใช้โมเดลอะไรจริง แสดงให้ผู้ใช้/ผู้ดูแลเห็นใน router_result"""
    if target == GENERAL_AI:
        return f"{settings.llm_provider}:{settings.llm_model}"
    if target == LOCAL_AI:
        return f"ollama:{settings.local_model}"
    return "rag:bm25+qdrant"
