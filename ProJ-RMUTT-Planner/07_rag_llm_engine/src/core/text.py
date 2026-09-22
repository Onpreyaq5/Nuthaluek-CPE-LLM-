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
ASCII_WORD_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.+\-]*")
# เครื่องหมาย + ต้องอยู่ใน token ไม่งั้น "B+" กับ "B" กลายเป็นคำเดียวกัน
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
    """แบ่งเอกสารตามหัวข้อ markdown -> [(breadcrumb, text)]

    breadcrumb คือหัวข้อไล่ตามลำดับชั้น เช่น "ชั้นปีที่ 2 > ภาคการศึกษาที่ 1 (18 หน่วยกิต)"

    ทำไมต้องมี: แผนการศึกษามีหัวข้อ "ภาคการศึกษาที่ 1" ซ้ำกัน 4 ครั้ง (ปี 1-4)
    ถ้าเก็บแค่หัวข้อสุดท้าย chunk ทั้ง 4 จะหน้าตาเหมือนกันหมด แยกไม่ออกว่าเป็นของปีไหน
    ทำให้คำถาม "ปี 2 เทอม 1 เรียนอะไร" ค้นไม่เจอ (เคยเป็นบั๊กจริง)
    """
    matches = list(HEADING_RE.finditer(body))
    if not matches:
        return [("", body.strip())]

    parts: list[tuple[str, str]] = []
    lead = body[: matches[0].start()].strip()
    if lead:
        parts.append(("", lead))

    trail: list[tuple[int, str]] = []  # (ระดับหัวข้อ, ข้อความ)
    for i, m in enumerate(matches):
        level = len(m.group(1))
        title = m.group(2).strip()
        while trail and trail[-1][0] >= level:
            trail.pop()
        trail.append((level, title))

        start = m.end()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(body)
        breadcrumb = " > ".join(t for _, t in trail)
        parts.append((breadcrumb, body[start:end].strip()))
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


# ── การขยายคำถาม ────────────────────────────────────────────────
# คำถามนักศึกษามักสั้นและใช้คำพูดชาวบ้าน ต่างจากคำในเอกสารราชการ
# เช่น ถาม "ปี 2 เทอม 1" แต่เอกสารเขียน "ชั้นปีที่ 2 > ภาคการศึกษาที่ 1"
#
# จัดเป็น "กลุ่มหัวข้อ" ไม่ใช่ dict แบน ๆ เพราะถ้าคำในหัวข้อเดียวกันติดหลายคำ
# ข้อความขยายจะซ้ำซ้อนจนกลบคำถามเดิม เคยทำให้คำถาม "เรียนกี่หน่วยกิตถึงจะจบ"
# ไปได้เอกสาร "หน่วยกิตต่อเทอม" แทนที่จะเป็น "หน่วยกิตตลอดหลักสูตร"
# กติกา: หนึ่งหัวข้อใช้ข้อความขยายได้ครั้งเดียว และคำที่เจาะจงกว่าอยู่ก่อน

EXPANSION_TOPICS: list[tuple[str, tuple[str, ...], str]] = [
    # (ชื่อหัวข้อ, คำที่จับ, ข้อความที่เติมเข้าไป)
    ("graduate", ("ถึงจะจบ", "จะจบ", "เรียนจบ", "สำเร็จการศึกษา", "จบการศึกษา", "ตลอดหลักสูตร"),
     "เกณฑ์สำเร็จการศึกษา จำนวนหน่วยกิตรวมตลอดหลักสูตร โครงสร้างหลักสูตร"),
    ("term_credits", ("กี่หน่วยกิตต่อเทอม", "หน่วยกิตต่อเทอม", "หน่วยกิตต่อภาค", "ลงได้กี่หน่วยกิต"),
     "จำนวนหน่วยกิตต่อภาคการศึกษา ขั้นต่ำ สูงสุด"),
    ("credits", ("หน่วยกิต",),
     "หน่วยกิต"),
    ("withdraw", ("ถอนรายวิชา", "ถอนวิชา"),
     "ถอนรายวิชา สัญลักษณ์ W กำหนดเวลา"),
    ("add_course", ("เพิ่มรายวิชา", "เพิ่มวิชา"),
     "เพิ่มรายวิชา กำหนดเวลา"),
    ("clash", ("ตารางชน", "เรียนชน", "ชนกัน", "ซ้ำซ้อน"),
     "เวลาเรียนซ้ำซ้อน เวลาสอบตรงกัน"),
    ("retire", ("รีไทร์", "พ้นสภาพ"),
     "พ้นสภาพนักศึกษา ระยะเวลาศึกษา GPAX"),
    ("prereq", ("บังคับก่อน", "ต้องผ่านอะไรก่อน", "ต้องเรียนอะไรก่อน"),
     "รายวิชาบังคับก่อน prerequisite แผนการศึกษา"),
    ("seat_full", ("ที่นั่งเต็ม",),
     "ที่นั่งเต็ม ขอเพิ่มที่นั่ง หมู่เรียน"),
    ("exam", ("ตารางสอบ", "สอบกลางภาค", "สอบปลายภาค"),
     "ตารางสอบ ปฏิทินการศึกษา"),
    ("plan", ("เรียนวิชาอะไร", "ต้องเรียนอะไร", "วิชาอะไรบ้าง", "แผนการเรียน"),
     "แผนการศึกษาแนะนำ รายวิชา"),
    # ผู้ใช้พูด "เกรด" เอกสารเขียน "ระดับคะแนน" — ไม่แปลงแล้วค้นไม่เจอเลย
    ("grade", ("เกรด", "กี่แต้ม", "ค่าระดับ", "เกรดเฉลี่ย"),
     "ระดับคะแนน ค่าระดับคะแนน การวัดและประเมินผล"),
    # ผู้ใช้พูด "ลาพักการเรียน" เอกสารเขียน "ลาพักการศึกษา"
    ("leave", ("ลาพัก", "พักการเรียน", "ดรอป"),
     "ลาพักการศึกษา สถานภาพนักศึกษา"),
    ("retake", ("ได้ F", "ติด F", "สอบตก", "เรียนซ้ำ"),
     "การเรียนซ้ำ ลงทะเบียนเรียนซ้ำ ระดับคะแนน"),
    # เอกสารใช้หัวข้อ "กลุ่มวิชาชีพเลือก" ผู้ใช้มักพูดว่า "วิชาเลือก" เฉย ๆ
    ("elective", ("วิชาเลือก", "เลือกเสรี", "วิชาชีพเลือก"),
     "กลุ่มวิชาชีพเลือก รายวิชาที่ภาควิชาเปิดให้เลือก"),
    # ถามถึงเนื้อหาวิชา -> ไปที่คำอธิบายรายวิชา
    ("syllabus", ("เรียนอะไรบ้าง", "เนื้อหาวิชา", "คืออะไร", "สอนอะไร", "เรียนเกี่ยวกับ"),
     "คำอธิบายรายวิชา"),
]

# "ปี 2" -> "ชั้นปีที่ 2"   /   "เทอม 1" -> "ภาคการศึกษาที่ 1"
# ต้องแปลงเพราะ breadcrumb ของ chunk ใช้คำทางการ ถ้าไม่แปลงจะค้นไม่เจอเลย
_YEAR_RE = re.compile(r"(?:ชั้น)?ปี(?:ที่)?\s*([1-8])(?![0-9])")
_TERM_RE = re.compile(r"(?:เทอม|ภาคเรียน|ภาคการศึกษา)(?:ที่)?\s*([1-3])(?![0-9])")


def expand_query(question: str) -> str:
    """ขยายคำถามสั้น ๆ ให้ตรงกับคำที่ใช้ในเอกสาร

    - แปลงคำพูดชาวบ้านเป็นคำทางการ (ปี 2 -> ชั้นปีที่ 2)
    - เติมคำพ้องความหมายตามหัวข้อ หัวข้อละไม่เกิน 1 ครั้ง
    """
    q = question.strip()
    extra: list[str] = []

    m = _YEAR_RE.search(q)
    if m:
        extra.append(f"ชั้นปีที่ {m.group(1)}")
    m = _TERM_RE.search(q)
    if m:
        extra.append(f"ภาคการศึกษาที่ {m.group(1)}")

    matched_topics: set[str] = set()
    for topic, keys, expansion in EXPANSION_TOPICS:
        if topic in matched_topics:
            continue
        # หัวข้อ credits แบบกว้าง ใช้ต่อเมื่อไม่มีหัวข้อหน่วยกิตที่เจาะจงกว่าติดมาก่อน
        if topic == "credits" and {"graduate", "term_credits"} & matched_topics:
            continue
        if any(k in q for k in keys):
            matched_topics.add(topic)
            extra.append(expansion)

    return f"{q} {' '.join(dict.fromkeys(extra))}".strip() if extra else q


def section_hints(question: str) -> list[str]:
    """ดึงเงื่อนไขที่ต้องปรากฏใน breadcrumb ของ chunk

    "ปี 2 เทอม 1" -> ["ชั้นปีที่ 2", "ภาคการศึกษาที่ 1"]
    ใช้คู่กับ SECTION_HINT_BOOST ในตัวค้นคืน เพราะเลขชั้นปี/ภาคเรียน
    มีน้ำหนักน้อยเกินกว่าจะแยกแยะได้ด้วยการค้นตามปกติ
    """
    hints: list[str] = []
    m = _YEAR_RE.search(question or "")
    if m:
        hints.append(f"ชั้นปีที่ {m.group(1)}")
    m = _TERM_RE.search(question or "")
    if m:
        hints.append(f"ภาคการศึกษาที่ {m.group(1)}")
    return hints
