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
        # เอกสารต้นฉบับเป็น Markdown ถ้าไม่ลบ ** ผู้ใช้จะเห็นเครื่องหมายดิบในคำตอบ
        excerpt = c.text.strip().replace("**", "")
        if len(excerpt) > 600:
            excerpt = excerpt[:600].rsplit("\n", 1)[0] + " ..."
        lines.append(f"[{i}] {where}")
        lines.append(excerpt)
        lines.append("")
    return "\n".join(lines).strip()


# ── โหมด provider จริง ──────────────────────────────────────────
# Gemini ตอบ 429/503 ตอนคนใช้เยอะ และแต่ละครั้งกว่าจะตอบ 503 ก็ใช้ 8-10 วินาที (วัดจริง)
# ลองซ้ำรุ่นเดิมจึงเสียเวลาเปล่า ลองรุ่นสำรองรุ่นละครั้งแทน
# ถ้ายังไม่ได้ ผู้เรียกถอยไปโหมดยกข้อความจากเอกสาร ผู้ใช้ยังได้คำตอบเสมอ
GEMINI_FALLBACK_MODELS = ("gemini-flash-lite-latest", "gemini-flash-latest")


async def _call_gemini(prompt: str) -> str:
    primary = settings.llm_model or "gemini-flash-lite-latest"
    models = [primary] + [m for m in GEMINI_FALLBACK_MODELS if m != primary]
    # ส่งคีย์ใน header ไม่ใช่ ?key= ใน URL: เวลาเรียกล้ม httpx ใส่ URL ลงข้อความ error
    # แล้ว log.error ด้านล่างจะพิมพ์คีย์ลง log ของ container ทั้งดุ้น (เจอจริงตอนทดสอบ)
    headers = {"x-goog-api-key": settings.llm_api_key}
    body = {"contents": [{"parts": [{"text": prompt}]}]}
    last: Exception | None = None
    async with httpx.AsyncClient(timeout=settings.llm_timeout) as client:
        for model in models:
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
            try:
                r = await client.post(url, headers=headers, json=body)
                r.raise_for_status()
                data = r.json()
                return data["candidates"][0]["content"]["parts"][0]["text"]
            except (httpx.HTTPError, KeyError, IndexError) as exc:
                last = exc
                log.warning("Gemini รุ่น %s ใช้ไม่ได้ตอนนี้ (%s) ลองรุ่นถัดไป", model, type(exc).__name__)
    raise last or RuntimeError("gemini: no model answered")


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


# ── Local AI Model (Ollama) ─────────────────────────────────────
async def call_local(prompt: str) -> str:
    """เรียกโมเดลในเครื่องผ่าน Ollama — ไม่มีค่าใช้จ่าย ไม่ส่งข้อมูลออกนอกเครื่อง"""
    async with httpx.AsyncClient(timeout=settings.local_timeout) as client:
        r = await client.post(
            f"{settings.local_model_url.rstrip('/')}/api/generate",
            json={
                "model": settings.local_model,
                "prompt": prompt,
                "stream": False,
                "options": {"num_predict": settings.local_max_tokens, "temperature": 0.3},
            },
        )
        r.raise_for_status()
        return (r.json().get("response") or "").strip()


# ── General AI (ช่อง General AI ในแผนภาพ) ───────────────────────
GENERAL_SYSTEM_PROMPT = """คุณคือผู้ช่วย AI ของระบบวางแผนการเรียน มหาวิทยาลัยเทคโนโลยีราชมงคลธัญบุรี
ตอบเป็นภาษาไทย กระชับ สุภาพ ไม่เกิน 8 บรรทัด
ช่วยได้เรื่องความรู้ทั่วไป การเขียน การสรุป เทคนิคการเรียน และอธิบายแนวคิด

กติกาที่ห้ามละเมิด
1. ถ้าคำถามเป็นเรื่องระเบียบ หลักสูตร รายวิชา ค่าธรรมเนียม หรือกำหนดการของมหาวิทยาลัย ห้ามตอบจากความจำ
   ให้บอกว่าถามเรื่องนั้นโดยตรงแล้วระบบจะค้นจากเอกสารของมหาวิทยาลัยให้
2. ห้ามตั้งชื่อหรือแนะนำร้าน สถานที่ บริษัท บุคคล ราคา เวลาเปิดปิด เบอร์โทร หรือที่อยู่ที่เฉพาะเจาะจง
   เพราะคุณตรวจสอบไม่ได้ว่ามีอยู่จริงหรือยังเปิดอยู่ ให้แนะนำวิธีหาข้อมูลแทน เช่น Google Maps หรือถามรุ่นพี่
3. ถ้าไม่แน่ใจ ให้บอกตรง ๆ ว่าไม่แน่ใจ ดีกว่าตอบให้ดูเหมือนรู้"""

GENERAL_UNAVAILABLE = (
    "ตอนนี้ยังไม่ได้เปิดใช้โมเดลสำหรับคำถามทั่วไป "
    "ถ้าเป็นเรื่องระเบียบหรือหลักสูตร ลองถามให้ระบุเรื่องชัดขึ้น เช่น "
    "“ถอนรายวิชาได้ถึงเมื่อไหร่” ระบบจะค้นจากเอกสารของมหาวิทยาลัยให้"
)


def _general_prompt(question: str, history: list[dict] | None) -> str:
    turns = []
    for m in (history or [])[-6:]:
        role = "ผู้ใช้" if m.get("role") == "user" else "ผู้ช่วย"
        content = str(m.get("content", "")).strip()
        if content:
            turns.append(f"{role}: {content}")
    convo = "\n".join(turns)
    return (
        f"{GENERAL_SYSTEM_PROMPT}\n\n"
        + (f"=== บทสนทนาก่อนหน้า ===\n{convo}\n\n" if convo else "")
        + f"ผู้ใช้: {question}\nผู้ช่วย:"
    )


GENERAL_BUSY = (
    "ตอนนี้บริการ AI สำหรับคำถามทั่วไปมีผู้ใช้หนาแน่น ยังตอบไม่ได้ ลองถามใหม่อีกครั้งในอีกสักครู่ "
    "ส่วนคำถามเรื่องระเบียบ หลักสูตร และตารางเรียน ใช้งานได้ตามปกติ"
)


async def general_answer(question: str, history: list[dict] | None = None) -> tuple[str, str]:
    """คืน (คำตอบ, provider)

    มีคีย์ Gemini -> ใช้ Gemini; ถ้า Gemini ไม่ว่างตอบตรง ๆ ว่าไม่ว่าง
    ไม่มีคีย์ -> ใช้โมเดลในเครื่อง (ช่อง Local AI Model)

    ทำไมไม่ถอยจาก Gemini ไปโมเดลในเครื่อง: วัดจริงแล้วโมเดล 0.5B บน CPU ใช้ 30+ วินาที
    และตอบวนซ้ำไม่มีประโยชน์ ผู้ใช้ที่เคยได้คำตอบดีจาก Gemini จะเห็นคุณภาพตกฮวบ
    บอกว่าไม่ว่างแล้วให้ลองใหม่ ซื่อตรงและเร็วกว่า
    """
    prompt = _general_prompt(question, history)
    if settings.llm_enabled:
        caller = _PROVIDERS.get(settings.llm_provider)
        if caller is not None:
            try:
                return (await caller(prompt)).strip(), settings.llm_provider
            except Exception as exc:  # noqa: BLE001
                log.error("General AI (%s) ไม่ว่าง: %s", settings.llm_provider, exc)
                return GENERAL_BUSY, f"{settings.llm_provider}_unavailable"
    if settings.local_enabled:
        try:
            text = await call_local(prompt)
            if text:
                return text, f"local:{settings.local_model}"
        except Exception as exc:  # noqa: BLE001
            log.error("Local AI เรียกไม่ติด: %s", exc)
    return GENERAL_UNAVAILABLE, "none"


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
