"""สร้างคำตอบจากเอกสารที่ค้นเจอ — รองรับ Google Gemini และโหมดไม่ต้องมี API key

ตั้ง GEMINI_API_KEY ใน Vercel (Settings > Environment Variables) เพื่อเปิดโหมด Gemini
ถ้าไม่ตั้ง ระบบยังใช้งานได้ปกติด้วยโหมด rule_based ที่ยกข้อความจากเอกสารมาตรง ๆ
ซึ่ง "ไม่มีวันมั่ว" เพราะไม่ได้แต่งข้อความเอง

กติกาที่ใช้กับทุกโหมด
- ตอบได้เฉพาะจากเอกสารที่ให้ไป ห้ามเดา
- ตัวเลขเรื่องตารางชน/หน่วยกิต ใช้ตามที่ระบบคำนวณมาเท่านั้น
- ทุกคำตอบแนบแหล่งอ้างอิง
"""
from __future__ import annotations

import json
import os
import urllib.error
import urllib.request

RULE_BASED_MAX_CHUNKS = 3
TIMEOUT = 25

SYSTEM_PROMPT = """คุณคือผู้ช่วยอาจารย์ที่ปรึกษาของมหาวิทยาลัยเทคโนโลยีราชมงคลธัญบุรี
ตอบเป็นภาษาไทย กระชับ สุภาพ ตรงประเด็น ไม่เกิน 6 บรรทัด

กติกาที่ห้ามละเมิด
1. ตอบได้เฉพาะสิ่งที่มีในเอกสารอ้างอิงที่ให้มา ห้ามเดา ห้ามเติมจากความรู้ทั่วไป
2. ถ้าเอกสารไม่มีคำตอบ ให้บอกตรง ๆ ว่าไม่พบ และแนะนำให้ติดต่อ สวท.
3. ตัวเลขเรื่องตารางชน หน่วยกิต และเวลา ใช้ตามที่ระบบส่งมาเท่านั้น ห้ามคำนวณเอง
4. เมื่ออ้างระเบียบ ให้ระบุหัวข้อที่อ้างด้วย เช่น [1]"""


def api_key() -> str:
    return (os.getenv("GEMINI_API_KEY") or os.getenv("LLM_API_KEY") or "").strip()


def model_name() -> str:
    return os.getenv("GEMINI_MODEL", "gemini-2.0-flash").strip()


def _rule_based(chunks: list[dict]) -> str:
    if not chunks:
        return ""
    lines = ["จากเอกสารของมหาวิทยาลัยที่เกี่ยวข้องกับคำถามนี้:", ""]
    for i, c in enumerate(chunks, start=1):
        where = c["title"] + (f" — {c['section']}" if c.get("section") else "")
        text = c["text"].strip()
        if len(text) > 600:
            text = text[:600].rsplit("\n", 1)[0] + " ..."
        lines += [f"[{i}] {where}", text, ""]
    return "\n".join(lines).strip()


def _build_prompt(question: str, chunks: list[dict], context: dict) -> str:
    refs = "\n\n".join(
        f"[{i}] {c['title']} — {c.get('section') or 'เนื้อหาทั่วไป'}\n{c['text']}"
        for i, c in enumerate(chunks, start=1)
    )
    extra = []
    if context.get("plan"):
        extra.append(f"แผนการเรียนที่ผู้ใช้เลือกอยู่: {context['plan']}")
    if context.get("conflicts"):
        extra.append(f"ผลตรวจตารางชนจากระบบ (ห้ามแก้ตัวเลข): {context['conflicts']}")
    ctx = "\n".join(extra) or "ไม่มีข้อมูลเพิ่มเติม"
    return (f"{SYSTEM_PROMPT}\n\n=== เอกสารอ้างอิง ===\n{refs}\n\n"
            f"=== ข้อมูลจากระบบ ===\n{ctx}\n\n=== คำถาม ===\n{question}\n\nคำตอบ:")


def _call_gemini(prompt: str) -> str:
    url = (f"https://generativelanguage.googleapis.com/v1beta/models/"
           f"{model_name()}:generateContent?key={api_key()}")
    body = json.dumps({
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {"temperature": 0.2, "maxOutputTokens": 800},
    }).encode()
    req = urllib.request.Request(url, data=body,
                                 headers={"Content-Type": "application/json"}, method="POST")
    with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
        data = json.load(r)
    return data["candidates"][0]["content"]["parts"][0]["text"].strip()


def generate(question: str, chunks: list[dict], context: dict | None = None) -> tuple[str, str, list[dict]]:
    """คืน (คำตอบ, provider ที่ใช้จริง, เอกสารที่ใช้สร้างคำตอบ)

    ตัวที่สามสำคัญ: sources ที่ส่งกลับต้องเป็นเอกสารที่ถูกใช้จริงเท่านั้น
    ไม่ใช่ผลค้นทั้งหมด ไม่งั้นผู้ใช้จะเห็นแหล่งอ้างอิงที่ไม่เคยถูกอ้างถึง
    """
    context = context or {}
    used = chunks[:RULE_BASED_MAX_CHUNKS]
    if not api_key():
        return _rule_based(used), "rule_based", used
    try:
        return _call_gemini(_build_prompt(question, chunks, context)), "gemini", chunks
    except (urllib.error.URLError, KeyError, IndexError, TimeoutError):
        # เรียกโมเดลไม่ได้ก็ยังต้องตอบผู้ใช้ได้ ไม่ปล่อยให้ค้าง
        return _rule_based(used), "rule_based_fallback", used
