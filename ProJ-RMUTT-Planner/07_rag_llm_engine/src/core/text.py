"""ตัดคำภาษาไทย/อังกฤษ และแบ่งเอกสารเป็น chunk

ทำไมไม่ใช้ pythainlp: โมดูลนี้ต้องรันใน CI และ container ขนาดเล็ก
ภาษาไทยเขียนติดกันไม่มีช่องว่าง จึงใช้ **character n-gram** ซึ่งใช้ได้ดีกับ BM25
โดยไม่ต้องมี dictionary หรือโมเดล

ขนาด n = (3, 4) เลือกจากการวัดจริงกับคำถามตัวอย่าง 14 ข้อ:

    n-gram    คะแนนต่ำสุด(เกี่ยวข้อง)   คะแนนสูงสุด(นอกเรื่อง)   ช่องว่าง
    (2,3)          0.2451                  0.2423              +0.0028
    (3,)           0.2192                  0.2178              +0.0013
    (3,4)          0.2233                  0.1968              +0.0265  <-- เลือกอันนี้
    (4,)           0.1721                  0.1754              -0.0034

ช่องว่างกว้างสุดแปลว่าแยก "คำถามที่ตอบได้" ออกจาก "คำถามนอกเรื่อง" ได้ชัดที่สุด
จึงตั้ง MIN_SCORE = 0.21 (ดู tests/test_retrieval.py)

ถ้าภายหลังต้องการความแม่นขึ้น เปลี่ยน tokenize() ให้เรียก pythainlp ได้เลย
"""
from __future__ import annotations

import re
import unicodedata

THAI_RE = re.compile(r"[\u0e00-\u0e7f]+")
ASCII_WORD_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.\-]*")
# รหัสวิชา เช่น 04100201-66 ต้องเป็น token เดี่ยว ๆ ห้ามถูกหั่น
COURSE_CODE_RE = re.compile(r"\b\d{8}-\d{2}\b")

# คำที่ตัดทิ้งเพราะเจอทุกเอกสาร ไม่ช่วยแยกแยะ
THAI_STOPWORDS = {
    "และ", "หรือ", "ของ", "ที่", "ใน", "การ", "ความ", "เป็น", "ให้", "ได้",
    "กับ", "จาก", "โดย", "ต้อง", "จะ", "ไม่", "มี", "นี้", "นั้น", "แล้ว",
}


def normalize(text: str) -> str:
    text = unicodedata.normalize("NFC", text or "")
    return re.sub(r"[\s\u00a0]+", " ", text).strip()


def _thai_ngrams(word: str, sizes: tuple[int, ...] = (3, 4)) -> list[str]:
    out: list[str] = []
    for n in sizes:
        if len(word) < n:
            if len(word) >= 2:
                out.append(word)
            continue
        out.extend(word[i:i + n] for i in range(len(word) - n + 1))
    return out


def tokenize(text: str) -> list[str]:
    """คืน token สำหรับ BM25 / TF-IDF"""
    text = normalize(text).lower()
    tokens: list[str] = []

    # 1) รหัสวิชาเก็บทั้งก้อน + เก็บส่วนหน้า 8 หลักด้วย (ค้นแบบไม่ระบุปีหลักสูตรก็เจอ)
    for code in COURSE_CODE_RE.findall(text):
        tokens.append(code)
        tokens.append(code.split("-")[0])

    # 2) คำอังกฤษ/ตัวเลข
    tokens.extend(ASCII_WORD_RE.findall(text))

    # 3) ภาษาไทย -> n-gram
    for run in THAI_RE.findall(text):
        if run in THAI_STOPWORDS:
            continue
        tokens.extend(t for t in _thai_ngrams(run) if t not in THAI_STOPWORDS)

    return tokens


# ── การแบ่ง chunk ───────────────────────────────────────────────
FRONTMATTER_RE = re.compile(r"^---\s*\n(.*?)\n---\s*\n", re.DOTALL)
HEADING_RE = re.compile(r"^(#{1,6})\s+(.+)$", re.MULTILINE)


def parse_frontmatter(raw: str) -> tuple[dict[str, str], str]:
    """อ่าน YAML frontmatter แบบง่าย (key: value และ list แบบ ["a","b"])"""
    m = FRONTMATTER_RE.match(raw)
    if not m:
        return {}, raw
    meta: dict[str, str] = {}
    for line in m.group(1).splitlines():
        if ":" not in line:
            continue
        k, _, v = line.partition(":")
        meta[k.strip()] = v.strip().strip('"').strip("'")
    return meta, raw[m.end():]


def split_by_heading(body: str) -> list[tuple[str, str]]:
    """แบ่งเอกสารตามหัวข้อ markdown -> [(heading, text)]"""
    matches = list(HEADING_RE.finditer(body))
    if not matches:
        return [("", body.strip())]
    parts: list[tuple[str, str]] = []
    lead = body[: matches[0].start()].strip()
    if lead:
        parts.append(("", lead))
    for i, m in enumerate(matches):
        start = m.end()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(body)
        parts.append((m.group(2).strip(), body[start:end].strip()))
    return parts


def chunk_text(text: str, max_chars: int, overlap: int) -> list[str]:
    """หั่นข้อความยาวโดยพยายามตัดที่ท้ายบรรทัด ไม่ตัดกลางประโยค"""
    text = text.strip()
    if len(text) <= max_chars:
        return [text] if text else []
    chunks: list[str] = []
    start = 0
    while start < len(text):
        end = min(start + max_chars, len(text))
        if end < len(text):
            cut = text.rfind("\n", start + max_chars // 2, end)
            if cut == -1:
                cut = text.rfind(" ", start + max_chars // 2, end)
            if cut > start:
                end = cut
        piece = text[start:end].strip()
        if piece:
            chunks.append(piece)
        if end >= len(text):
            break
        start = max(end - overlap, start + 1)
    return chunks
