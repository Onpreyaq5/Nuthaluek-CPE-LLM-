"""guardrails.py — Domain-specific guardrails for the AI Router

NOT IN DL-06 (DL-06 mentioned guardrails in principle but did not specify them).
Main project has two hard rules from 02_step.txt:

  1. SCHEDULE_CONFLICT must call check_conflicts (no LLM guessing)
  2. REGULATION_QA / CURRICULUM_RULE: if RAG returns no evidence -> refuse to answer
"""
from __future__ import annotations
import logging

from .models import ClassificationResult, ToolCall

logger = logging.getLogger(__name__)


def validate_tools_for_intent(
    classification: ClassificationResult,
    tools_called: list[ToolCall],
) -> tuple[bool, str]:
    """
    Returns (ok, reason).
    Raises a soft refusal message when a guardrail is violated.
    """
    intent = classification.intent
    tool_names = {tc.tool for tc in tools_called}

    # Guardrail 1: Schedule conflict MUST use the engine (no LLM guessing times)
    if intent == "SCHEDULE_CONFLICT":
        conflict_call = next((tc for tc in tools_called if tc.tool == "check_conflicts"), None)
        
        if conflict_call is None:
            reason = "ไม่สามารถตรวจสอบตารางชนได้โดยไม่ผ่านระบบตรวจ กรุณาระบุรหัสวิชาที่ต้องการตรวจสอบ"
            logger.warning("[guardrail] SCHEDULE_CONFLICT without check_conflicts call")
            return False, reason
        elif not conflict_call.success:
            reason = "ระบบตรวจตารางชน (โมดูล 06) ไม่ตอบสนองในขณะนี้ ยังไม่สามารถยืนยันได้ว่าตารางชนหรือไม่ กรุณาลองใหม่อีกครั้ง"
            logger.warning(f"[guardrail] SCHEDULE_CONFLICT check_conflicts failed: {conflict_call.error}")
            return False, reason

    # Guardrail 2: Regulation / curriculum answers MUST have RAG evidence
    if intent in ("REGULATION_QA", "CURRICULUM_RULE"):
        rag_call = next(
            (tc for tc in tools_called if tc.tool == "search_knowledge"), None
        )
        if rag_call is None or not rag_call.success:
            reason = (
                "ไม่พบข้อมูลในระเบียบหรือหลักสูตร "
                "กรุณาติดต่อสำนักส่งเสริมวิชาการและงานทะเบียน (สวท.)"
            )
            logger.warning("[guardrail] RAG not called or failed for %s", intent)
            return False, reason

        chunks = (rag_call.result or {}).get("chunks", [])
        if not chunks:
            reason = (
                "ไม่พบข้อมูลที่เกี่ยวข้องในระเบียบมหาวิทยาลัย "
                "กรุณาติดต่อ สวท. เพื่อยืนยัน"
            )
            logger.warning("[guardrail] RAG returned empty chunks for %s", intent)
            return False, reason

    return True, ""
