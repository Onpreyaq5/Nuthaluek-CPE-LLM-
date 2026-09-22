"""ตัวเรียกโมเดลภาษา — มี 2 โหมด

1. rule_based (ค่าเริ่มต้น)  สรุปคำตอบจากเอกสารที่ค้นเจอโดยไม่ต้องมี API key
   ใช้ตอนพัฒนา/รัน CI/เดโม่ ได้คำตอบที่ "ไม่มีวันมั่ว" เพราะหยิบข้อความจากเอกสารตรง ๆ
2. provider จริง (gemini | openai | anthropic) เมื่อกำหนด LLM_API_KEY

กติกาที่ใช้กับทุกโหมด
- ห้ามคำนวณเวลา/หน่วยกิตเอง ตัวเลขทั้งหมดต้องมาจากโมดูล 05 และ 06
- ทุกคำตอบที่อ้างระเบียบต้องแนบแหล่งอ้างอิง
- ถ้าไม่มีเอกสารรองรับ ให้ตอบว่าไม่พบข้อมูล
"""
from __future__ import annotations

import logging

import httpx

from ..config import settings
from ..models.schemas import Chunk

log = logging.getLogger(__name__)

SYSTEM_PROMPT = """คุณคือผู้ช่วยอาจารย์ที่ปรึกษาของมหาวิทยาลัยเทคโนโลยีราชมงคลธัญบุรี
ตอบเป็นภาษาไทย กระชับ สุภาพ ตรงประเด็น

กติกาที่ห้ามละเมิด
1. ตอบได้เฉพาะสิ่งที่มีในเอกสารอ้างอิงที่ให้มาเท่านั้น ห้ามเดา ห้ามเติมจากความรู้ทั่วไป
2. ถ้าเอกสารไม่มีคำตอบ ให้บอกตรง ๆ ว่าไม่พบ และแนะนำให้ติดต่อ สวท.
3. ตัวเลขเรื่องตารางชน หน่วยกิต และเวลา ให้ใช้ตามที่ระบบส่งมาเท่านั้น ห้ามคำนวณเอง
4. เมื่ออ้างระเบียบ ให้ระบุหัวข้อหรือข้อที่อ้างด้วยเสมอ"""


def build_prompt(question: str, chunks: list[Chunk], context: dict) -> str:
    refs = "\n\n".join(
        f"[{i}] {c.title} — {c.section or 'เนื้อหาทั่วไป'}\n{c.text}"
        for i, c in enumerate(chunks, start=1)
    )
    ctx_lines = []
    if context.get("student"):
        ctx_lines.append(f"ข้อมูลนักศึกษา: {context['student']}")
    if context.get("plan"):
        ctx_lines.append(f"แผนการเรียนปัจจุบัน: {context['plan']}")
    if context.get("conflicts"):
        ctx_lines.append(f"ผลตรวจตารางชนจากระบบ (ห้ามแก้ตัวเลข): {context['conflicts']}")
    ctx = "\n".join(ctx_lines) or "ไม่มีข้อมูลเพิ่มเติม"

    return (
        f"{SYSTEM_PROMPT}\n\n"
        f"=== เอกสารอ้างอิง ===\n{refs}\n\n"
        f"=== ข้อมูลจากระบบ ===\n{ctx}\n\n"
        f"=== คำถาม ===\n{question}\n\n"
        f"ตอบโดยอ้างอิงหมายเลขเอกสาร เช่น [1]:"
    )


# ── โหมด rule-based ─────────────────────────────────────────────
# โหมดนี้ยกข้อความจากเอกสารมาแสดงตรง ๆ จึงใส่ได้ไม่กี่ชิ้นก่อนจะยาวเกินอ่าน
RULE_BASED_MAX_CHUNKS = 3


def _rule_based_answer(question: str, chunks: list[Chunk]) -> str:
    """เรียบเรียงคำตอบจากข้อความในเอกสารโดยตรง ไม่แต่งเพิ่ม"""
    if not chunks:
        return ""
    lines = ["จากเอกสารของมหาวิทยาลัยที่เกี่ยวข้องกับคำถามนี้:", ""]
    for i, c in enumerate(chunks, start=1):
        where = f"{c.title}" + (f" — {c.section}" if c.section else "")
        excerpt = c.text.strip()
        if len(excerpt) > 600:
            excerpt = excerpt[:600].rsplit("\n", 1)[0] + " ..."
        lines.append(f"[{i}] {where}")
        lines.append(excerpt)
        lines.append("")
    return "\n".join(lines).strip()


# ── โหมด provider จริง ──────────────────────────────────────────
async def _call_gemini(prompt: str) -> str:
    model = settings.llm_model or "gemini-2.0-flash"
    url = (
        f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
        f"?key={settings.llm_api_key}"
    )
    async with httpx.AsyncClient(timeout=settings.llm_timeout) as client:
        r = await client.post(url, json={"contents": [{"parts": [{"text": prompt}]}]})
        r.raise_for_status()
        data = r.json()
    return data["candidates"][0]["content"]["parts"][0]["text"]


async def _call_openai(prompt: str) -> str:
    model = settings.llm_model or "gpt-4.1-mini"
    async with httpx.AsyncClient(timeout=settings.llm_timeout) as client:
        r = await client.post(
            "https://api.openai.com/v1/chat/completions",
            headers={"Authorization": f"Bearer {settings.llm_api_key}"},
            json={"model": model, "messages": [{"role": "user", "content": prompt}]},
        )
        r.raise_for_status()
        data = r.json()
    return data["choices"][0]["message"]["content"]


async def _call_anthropic(prompt: str) -> str:
    model = settings.llm_model  # ต้องกำหนด LLM_MODEL เองสำหรับ provider นี้
    async with httpx.AsyncClient(timeout=settings.llm_timeout) as client:
        r = await client.post(
            "https://api.anthropic.com/v1/messages",
            headers={
                "x-api-key": settings.llm_api_key,
                "anthropic-version": "2023-06-01",
            },
            json={
                "model": model,
                "max_tokens": 1024,
                "messages": [{"role": "user", "content": prompt}],
            },
        )
        r.raise_for_status()
        data = r.json()
    return data["content"][0]["text"]


_PROVIDERS = {
    "gemini": _call_gemini,
    "openai": _call_openai,
    "anthropic": _call_anthropic,
}


async def generate(
    question: str, chunks: list[Chunk], context: dict | None = None
) -> tuple[str, str, list[Chunk]]:
    """คืน (คำตอบ, ชื่อ provider ที่ใช้จริง, เอกสารที่ถูกใช้สร้างคำตอบจริง)

    ตัวที่สามสำคัญ: ผู้เรียกต้องเอาไปทำ sources ให้ตรงกับคำตอบ
    โหมด rule_based ใช้แค่ 3 ชิ้นแรก ถ้าแนบ sources ครบ 6 ชิ้น ผู้ใช้จะเห็น
    แหล่งอ้างอิงที่ไม่เคยถูกอ้างถึงในคำตอบเลย (เคยเป็นบั๊กจริง)
    """
    context = context or {}
    used = chunks[:RULE_BASED_MAX_CHUNKS]

    if not settings.llm_enabled:
        return _rule_based_answer(question, used), "rule_based", used

    caller = _PROVIDERS.get(settings.llm_provider)
    if caller is None:
        log.warning("ไม่รู้จัก provider %r กลับไปใช้ rule_based", settings.llm_provider)
        return _rule_based_answer(question, used), "rule_based", used

    try:
        answer = await caller(build_prompt(question, chunks, context))
        # provider จริงได้เอกสารครบทุกชิ้นใน prompt จึงถือว่าใช้ทั้งหมด
        return answer.strip(), settings.llm_provider, chunks
    except Exception as exc:  # noqa: BLE001 - ล้มแล้วต้องยังตอบผู้ใช้ได้
        log.error("เรียก %s ไม่สำเร็จ: %s — กลับไปใช้ rule_based", settings.llm_provider, exc)
        return _rule_based_answer(question, used), "rule_based_fallback", used
