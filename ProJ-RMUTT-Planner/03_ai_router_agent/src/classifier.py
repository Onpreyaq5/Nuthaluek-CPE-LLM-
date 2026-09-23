"""classifier.py — Two-layer intent classifier

Layer 1 (keyword rules): fast, free, always runs first.
  - If confidence >= settings.confidence_threshold (0.7) -> use the result.

Layer 2 (LLM, JSON structured output): slower, costs tokens.
  - Only called when keyword confidence < threshold.

FROM DL-06: same two-layer design, but DL-06 does LLM first then keyword fallback.
  Main project inverts this: keyword first (cheaper), LLM only when uncertain.

NOT IN DL-06:
  - Slot filling (term, course_code, day, time)
  - Thai numeral normalization
  - "Ask back if slot missing" logic
  - Domain-specific intents (SCHEDULE_CONFLICT, PLAN_GENERATE, etc.)
"""
from __future__ import annotations
import json
import re
import logging

import httpx

from .models import ClassificationResult, Slots
from .config import settings

logger = logging.getLogger(__name__)

# ──────────────────────────────────────────────────────────────
#  Keyword tables per intent
# ──────────────────────────────────────────────────────────────

_KEYWORD_RULES: dict[str, list[str]] = {
    "SCHEDULE_CONFLICT": [
        "ชน", "ทับ", "ซ้อน", "conflict", "ลงตัวนี้ได้ไหม",
        "ชนไหม", "ซ้ำ", "ทับกัน", "ตารางชน",
    ],
    "PLAN_GENERATE": [
        "จัดตาราง", "วางแผน", "แนะนำวิชา", "จัดให้", "ช่วยเลือก",
        "เทอมหน้า", "ควรลงวิชา", "ลงวิชาอะไร", "auto plan",
    ],
    "COURSE_INFO": [
        "วิชานี้เปิด", "sec ไหน", "section ว่าง", "กี่คนลง",
        "เวลาเรียน", "วันไหน", "ที่นั่ง", "อาจารย์ผู้สอน", "เปิดสอน",
    ],
    "CURRICULUM_RULE": [
        "หน่วยกิต", "จบได้ไหม", "บังคับก่อน", "prereq", "prerequisite",
        "เหลืออีกกี่หน่วย", "โครงสร้างหลักสูตร", "วิชาบังคับ", "วิชาเลือก",
        "ต้องผ่าน", "มาก่อน", "เรียนก่อน", "คือวิชาอะไร", "เรียนอะไร", "คำอธิบายรายวิชา",
        "ต้องเรียน", "เรียนวิชาอะไร", "แผนการเรียน",
    ],
    "REGULATION_QA": [
        "ระเบียบ", "ประกาศ", "ถอน", "drop", "withdraw",
        "ลาพัก", "สอบซ่อม", "สอบปลายภาค", "กฎ", "ข้อบังคับ",
        "สำเร็จการศึกษา", "ผลการเรียน", "เกรด", "ติด F",
    ],
    "GENERAL_CHAT": [
        "สวัสดี", "ขอบคุณ", "ช่วยอธิบาย", "สรุป", "แปล",
        "เขียน", "hello", "hi", "thanks",
    ],
}

# ──────────────────────────────────────────────────────────────
#  Thai / mixed text utilities  (NOT IN DL-06)
# ──────────────────────────────────────────────────────────────

_TH_DIGIT = str.maketrans("๐๑๒๓๔๕๖๗๘๙", "0123456789")

def _normalize_text(text: str) -> str:
    """Convert Thai digits, lowercase, collapse whitespace."""
    return text.translate(_TH_DIGIT).lower().strip()


_TERM_RE = re.compile(r"(\d)[/\\](\d{4})")        # "1/2569"
_YEAR_RE = re.compile(r"ปี(?:การศึกษา)?\s*(\d{4})")
# รหัสวิชา/กลุ่มเรียนที่ต้องจับได้ (เรียงจากยาวไปสั้น ให้รหัสกลุ่มเรียนชนะรหัสวิชา)
#   04100203-66-01   รหัสกลุ่มเรียนจริงของ มทร.ธัญบุรี (วิชา 8 หลัก - ปีหลักสูตร - หมู่)
#   04100203-66      รหัสวิชาจริง
#   C0407131         รหัสแบบเก่าในหน้าตรวจสอบจบ
#   CPE101 / CPE101-01  รูปแบบสมมติที่ใช้ในเอกสารตัวอย่าง
# เดิมจับได้แค่ CPE101 ถามด้วยรหัสจริงจึงไม่มีรหัสวิชาใน slot เลย
# ตรวจตารางชนในแชตไม่ได้ และคำถามรายวิชาหลุดไปให้ General AI ตอบ
_COURSE_RE = re.compile(
    r"(?<![\w-])(\d{8}-\d{2}(?:-\d{2})?|C\d{7}|[A-Za-z]{2,4}\d{3}(?:-\d{2})?)(?![\w-])"
)
_DAY_MAP = {
    "จันทร์": "MON", "อังคาร": "TUE", "พุธ": "WED",
    "พฤหัส": "THU", "ศุกร์": "FRI", "เสาร์": "SAT", "อาทิตย์": "SUN",
}
_TIME_RE = re.compile(r"\b(\d{1,2})[:.h](\d{2})\b")


def _extract_slots(text: str) -> Slots:
    """Pull term, year, course codes, day, time from raw message text."""
    norm = _normalize_text(text)

    # Term: "1/2569"
    term = None
    m = _TERM_RE.search(norm)
    if m:
        term = f"{m.group(1)}/{m.group(2)}"

    # Academic year standalone
    academic_year: int | None = None
    m = _YEAR_RE.search(norm)
    if m:
        academic_year = int(m.group(1))
    elif term:
        academic_year = int(term.split("/")[1])

    # Course codes e.g. "CPE101"
    course_codes = list({c.upper() for c in _COURSE_RE.findall(text)})

    # Day of week
    day = next((th for th in _DAY_MAP if th in text), None)

    # Time string
    time_str: str | None = None
    m = _TIME_RE.search(norm)
    if m:
        time_str = f"{int(m.group(1)):02d}:{m.group(2)}"

    return Slots(
        term=term,
        academic_year=academic_year,
        course_codes=course_codes,
        day=day,
        time_str=time_str,
    )


# ──────────────────────────────────────────────────────────────
#  Layer 1 — Keyword classifier
# ──────────────────────────────────────────────────────────────

def _keyword_classify(message: str) -> ClassificationResult:
    """Score every intent by keyword hits; pick the best one."""
    norm = _normalize_text(message)
    scores: dict[str, int] = {}
    for intent, kws in _KEYWORD_RULES.items():
        scores[intent] = sum(1 for kw in kws if kw in norm)

    best_intent = max(scores, key=scores.get)  # type: ignore[arg-type]
    best_score = scores[best_intent]
    total = sum(scores.values()) or 1

    if best_score == 0:
        return ClassificationResult(
            intent="GENERAL_CHAT",
            confidence=0.3,
            reasoning="No keywords matched; defaulting to GENERAL_CHAT",
            slots=_extract_slots(message),
            source="keyword",
        )

    confidence = min(0.95, best_score / total + 0.3)  # heuristic boost
    return ClassificationResult(
        intent=best_intent,
        confidence=round(confidence, 2),
        reasoning=f"Keyword match: {best_score}/{total} for {best_intent}",
        slots=_extract_slots(message),
        source="keyword",
    )


# ──────────────────────────────────────────────────────────────
#  Layer 2 — LLM classifier  (FROM DL-06: structured JSON output)
# ──────────────────────────────────────────────────────────────

_LLM_SYSTEM_PROMPT = """\
You are an intent classifier for an RMUTT university schedule-planner AI assistant.
Classify the student's message into EXACTLY ONE intent and extract slot values.

INTENTS:
- SCHEDULE_CONFLICT  : student asks if enrolling a course will clash with existing schedule
- PLAN_GENERATE      : student wants the system to auto-generate a schedule plan
- COURSE_INFO        : student asks about a course's open sections, times, seats, teacher
- CURRICULUM_RULE    : student asks about credits required, prerequisites, degree structure
- REGULATION_QA      : student asks about university regulations (withdraw, leave, grades)
- GENERAL_CHAT       : greeting, thanks, general question not in above categories

Respond ONLY with valid JSON (no markdown, no extra text):
{
  "intent": "<INTENT>",
  "confidence": <0.0-1.0>,
  "reasoning": "<one English sentence>",
  "slots": {
    "term": "<e.g. 1/2569 or null>",
    "academic_year": <int or null>,
    "course_codes": ["<e.g. CPE101>"],
    "day": "<Thai day name or null>",
    "time_str": "<HH:MM or null>",
    "topic": "<short topic phrase or null>"
  }
}
"""


def _llm_classify(message: str, history: list) -> ClassificationResult:
    """Call LLM API to classify intent with structured JSON output."""
    history_text = "\n".join(
        f"{m.get('role','user')}: {m.get('content','')}" for m in history[-3:]
    ) or "None"

    user_prompt = (
        f"Conversation history (last 3 turns):\n{history_text}\n\n"
        f"Student message: {message}"
    )

    try:
        raw, source = _call_llm(user_prompt)
        # Strip markdown fences if model wraps in ```json
        raw = re.sub(r"^```(?:json)?\s*|\s*```$", "", raw.strip(), flags=re.MULTILINE)
        data = json.loads(raw)

        intent = str(data.get("intent", "")).strip().upper()
        # โมเดลเล็กในเครื่องตอบ intent นอกรายการได้ ถ้าไม่รู้จักให้ถือว่าจัดไม่ได้ ใช้ keyword แทน
        if intent not in ClassificationResult.VALID_INTENTS:
            raise ValueError(f"unknown intent from {source}: {intent!r}")

        if source == "local":
            # โมเดลเล็กเก่งพอจะแยกประเภท แต่ดึงรหัสวิชา/ภาคเรียนพลาดบ่อย
            # ใช้ slot จาก regex ซึ่งแม่นกว่าสำหรับรูปแบบที่ตายตัวอย่างรหัสวิชา
            slots = _extract_slots(message)
        else:
            slots_data = data.get("slots") or {}
            slots = Slots(
                term=slots_data.get("term"),
                academic_year=slots_data.get("academic_year"),
                course_codes=slots_data.get("course_codes", []),
                day=slots_data.get("day"),
                time_str=slots_data.get("time_str"),
                topic=slots_data.get("topic"),
            )
        return ClassificationResult(
            intent=intent,
            confidence=min(max(float(data.get("confidence", 0.5)), 0.0), 1.0),
            reasoning=str(data.get("reasoning", "")),
            slots=slots,
            source=source,
        )
    except Exception as exc:
        logger.warning("LLM classify failed: %s; falling back to keyword result", exc)
        return _keyword_classify(message)


def _call_local(user_prompt: str) -> str:
    """ถามโมเดลในเครื่อง (Ollama) ให้ตอบเป็น JSON — ใช้เมื่อไม่มีคีย์ของ provider ภายนอก"""
    with httpx.Client(timeout=settings.local_classify_timeout_s) as client:
        r = client.post(
            f"{settings.local_model_url.rstrip('/')}/api/generate",
            json={
                "model": settings.local_model,
                "system": _LLM_SYSTEM_PROMPT,
                "prompt": user_prompt,
                "format": "json",
                "stream": False,
                "options": {"temperature": 0, "num_predict": 160},
            },
        )
        r.raise_for_status()
        return r.json().get("response", "")


def _call_llm(user_prompt: str) -> tuple[str, str]:
    """คืน (ข้อความดิบจากโมเดล, ที่มา "llm" | "local")

    มีคีย์ของ provider ภายนอก -> ใช้ provider นั้น (General AI)
    ไม่มีคีย์แต่มี Ollama -> ใช้โมเดลในเครื่อง (Local AI Model)
    """
    if not settings.llm_api_key:
        if settings.local_model_url:
            return _call_local(user_prompt), "local"
        raise RuntimeError("no LLM key and no local model configured")
    return _call_remote(user_prompt), "llm"


def _call_remote(user_prompt: str) -> str:
    """Dispatch to the configured LLM provider and return raw response text."""
    provider = settings.llm_provider.lower()

    if provider == "gemini":
        # เรียก REST ตรงแทน SDK google.generativeai (เลิกพัฒนาแล้ว และไม่มี timeout)
        # SDK เดิมค้างนานตอน Gemini ตอบ 503 จน 02 ตัดว่า 03 ไม่ตอบ (502) — เจอจริงตอนทดสอบ
        # timeout สั้นกว่า chat_start ของ 02 เสมอ ล้ม = classify() ถอยไปใช้ผลจาก keyword
        with httpx.Client(timeout=settings.local_classify_timeout_s) as client:
            r = client.post(
                "https://generativelanguage.googleapis.com/v1beta/models/"
                f"{settings.llm_model}:generateContent",
                headers={"x-goog-api-key": settings.llm_api_key},
                json={
                    "systemInstruction": {"parts": [{"text": _LLM_SYSTEM_PROMPT}]},
                    "contents": [{"role": "user", "parts": [{"text": user_prompt}]}],
                    "generationConfig": {"temperature": 0, "responseMimeType": "application/json"},
                },
            )
            r.raise_for_status()
            return r.json()["candidates"][0]["content"]["parts"][0]["text"]

    elif provider == "openai":
        from openai import OpenAI
        client = OpenAI(api_key=settings.llm_api_key)
        resp = client.chat.completions.create(
            model=settings.llm_model,
            messages=[
                {"role": "system", "content": _LLM_SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt},
            ],
            response_format={"type": "json_object"},
            temperature=0,
        )
        return resp.choices[0].message.content or ""

    elif provider == "groq":
        from openai import OpenAI
        # Groq is OpenAI-compatible, just change the base_url!
        client = OpenAI(
            api_key=settings.llm_api_key,
            base_url="https://api.groq.com/openai/v1"
        )
        resp = client.chat.completions.create(
            model=settings.llm_model,
            messages=[
                {"role": "system", "content": _LLM_SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt},
            ],
            response_format={"type": "json_object"},
            temperature=0,
        )
        return resp.choices[0].message.content or ""

    else:
        raise ValueError(f"Unsupported LLM_PROVIDER: {provider}")


# ──────────────────────────────────────────────────────────────
#  Public API
# ──────────────────────────────────────────────────────────────

def classify(message: str, history: list | None = None) -> ClassificationResult:
    """
    Two-layer classification:
      1. Keyword rules (fast, free)
      2. LLM (only if keyword confidence < threshold)
    """
    history = history or []
    result = _keyword_classify(message)
    logger.info(
        "[classifier] keyword: intent=%s conf=%.2f",
        result.intent, result.confidence,
    )

    if result.confidence < settings.confidence_threshold:
        logger.info(
            "[classifier] conf %.2f < %.2f -> calling LLM",
            result.confidence, settings.confidence_threshold,
        )
        result = _llm_classify(message, history)
        logger.info(
            "[classifier] llm: intent=%s conf=%.2f",
            result.intent, result.confidence,
        )

    # กันพลาด: คำถามที่มีรหัสวิชาเป็นเรื่องของมหาวิทยาลัยเสมอ ห้ามปล่อยให้ General AI ตอบจากความจำ
    # (เจอจริง: "วิชา 04100203-66 ต้องผ่านวิชาอะไรมาก่อน" ไปตกที่ GENERAL_CHAT)
    if result.intent == "GENERAL_CHAT" and result.slots.course_codes:
        result = result.model_copy(update={
            "intent": "CURRICULUM_RULE",
            "reasoning": f"{result.reasoning} | มีรหัสวิชา -> ตอบจากเอกสารหลักสูตร",
        })

    return result


def missing_slots(intent: str, slots: Slots) -> list[str]:
    """
    Return a list of slot names still needed for this intent.
    NOT IN DL-06 — required for slot-filling / ask-back logic.
    """
    needed: dict[str, list[str]] = {
        "SCHEDULE_CONFLICT": ["course_codes"],
        "PLAN_GENERATE":     ["term"],
        "COURSE_INFO":       ["course_codes"],
        "CURRICULUM_RULE":   [],
        "REGULATION_QA":     [],
        "GENERAL_CHAT":      [],
    }
    required = needed.get(intent, [])
    missing = []
    for field in required:
        val = getattr(slots, field, None)
        if not val:
            missing.append(field)
    return missing


# Friendly Thai question to ask when a slot is missing  (NOT IN DL-06)
SLOT_QUESTIONS: dict[str, str] = {
    "course_codes": "ขอรหัสวิชาที่ต้องการตรวจสอบหน่อยได้ไหมครับ? (เช่น CPE101)",
    "term":         "ต้องการจัดตารางเทอมไหนครับ? (เช่น 1/2569)",
}

def resolve_term(extracted_term: str | None, req_term: str | None) -> tuple[str | None, int | None]:
    """
    Resolve term fallback:
    1. If message specifies term, use it.
    2. Else use req.term.
    Returns (resolved_term, academic_year)
    """
    term = extracted_term or req_term
    if not term:
        return None, None
    
    # Try to extract year from term (e.g. "1/2569" -> 2569)
    try:
        if "/" in term:
            parts = term.split("/")
            return term, int(parts[-1])
        return term, int(re.search(r'\d{4}', term).group())
    except Exception:
        return term, None
