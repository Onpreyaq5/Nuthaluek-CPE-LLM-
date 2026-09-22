from __future__ import annotations

from collections.abc import AsyncIterator

from src.core.config import TimeoutPolicy, get_settings

from ..http_base import HttpAdapterClient

# ยืนยันจากโค้ดจริงของ 07_rag_llm_engine/src/api/routes.py (@router.post("/generate"))
# request  : {"question": str, "context": dict}  — context คือก้อนที่ 03 ส่งมากับ context_ready
#            (มี ai_target ที่ 03 เลือกไว้ว่า University RAG / General AI / Local AI ตอบ)
# response : {"answer": str, "sources": [{doc_id,title,section,...}], "grounded": bool,
#             "provider": str, "disclaimer": str}
PATH_GENERATE = "/generate"


def _to_source_item(src: dict) -> dict:
    """แปลง Source ของ 07 เป็น SourceItem ของ public schema (title/section/document_id)"""
    return {
        "title": str(src.get("title") or src.get("doc_id") or "เอกสารอ้างอิง"),
        "section": src.get("section") or None,
        "document_id": src.get("doc_id"),
    }


class HttpAnswerGenerator:
    """โมดูล 07 — สร้างคำตอบจริงหลัง 03 จบด้วย context_ready

    ไม่ retry: การสร้างคำตอบอาจใช้โมเดลในเครื่องซึ่งช้า ถ้า retry จะรอนานเป็นสองเท่า
    timeout ใช้ค่าเดียวกับ chat_idle เพราะระหว่างรอ 07 ไม่มี event อื่นไหลออกไปเลย
    """

    async def generate(
        self, *, question: str, context: dict, history: list[dict]
    ) -> AsyncIterator[dict]:
        settings = get_settings()
        ctx = dict(context or {})
        # 03 ตัดประวัติตามงบ token แล้ว แต่ถ้าไม่มีมา ใช้ประวัติจาก DB ของ 02 แทน
        ctx.setdefault("history", history)
        client = HttpAdapterClient(
            base_url=settings.EXPLAINER_URL,
            module="07",
            timeout_policy=TimeoutPolicy(
                seconds=settings.timeouts.chat_idle.seconds, retries=0
            ),
        )
        try:
            response = await client.request(
                "POST", PATH_GENERATE, json={"question": question, "context": ctx}
            )
        finally:
            await client.aclose()

        if response.status_code >= 400:
            from src.core.errors import Upstream502Error

            raise Upstream502Error(
                "โมดูล 07 ปฏิเสธคำขอสร้างคำตอบ", details={"module": "07", "status": response.status_code}
            )

        data = response.json()
        answer = str(data.get("answer") or "").strip()
        # ส่งทีละย่อหน้าให้หน้าเว็บเห็นข้อความไหลออกมา แทนที่จะโผล่ทีเดียวทั้งก้อน
        paragraphs = answer.split("\n")
        for i, line in enumerate(paragraphs):
            text = line + ("\n" if i < len(paragraphs) - 1 else "")
            if text:
                yield {"type": "token", "text": text}

        note = str(data.get("disclaimer") or "").strip()
        if note:
            yield {"type": "token", "text": f"\n\n— {note}"}

        sources = [_to_source_item(s) for s in data.get("sources") or [] if isinstance(s, dict)]
        if sources:
            yield {"type": "sources", "items": sources}
