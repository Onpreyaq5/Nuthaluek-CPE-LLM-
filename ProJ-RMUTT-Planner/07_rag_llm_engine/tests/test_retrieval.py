"""ทดสอบการค้นคืนเอกสาร — รวมการวัดว่า MIN_SCORE แยกคำถามนอกเรื่องได้จริง"""
import pytest

from src.config import settings
from src.core.text import chunk_text, parse_frontmatter, split_by_heading, tokenize
from src.services.knowledge import knowledge_base

# คำถามที่ระบบ "ต้องตอบได้" — มีคำตอบอยู่ในเอกสารจริง
ON_TOPIC = [
    "ลงทะเบียนได้กี่หน่วยกิตต่อเทอม",
    "ถอนรายวิชาได้ถึงเมื่อไหร่",
    "ตารางเรียนชนกันลงได้ไหม",
    "วิชา 04100203-66 ต้องผ่านอะไรก่อน",
    "เรียนเกินกี่ปีจะถูกรีไทร์",
    "สอบปลายภาค 1/2569 วันไหน",
    "หลักสูตรวิศวะคอมต้องเรียนกี่หน่วยกิตถึงจะจบ",
    "ที่นั่งเต็มทำยังไง",
    "ได้ F ต้องทำยังไง",
]

# คำถามนอกเรื่อง — ระบบ "ต้องไม่ตอบ" เพราะไม่มีหลักฐานในเอกสาร
OFF_TOPIC = [
    "ราคาข้าวมันไก่เท่าไหร่",
    "วิธีเปลี่ยนยางรถยนต์",
    "ทีมฟุตบอลไหนชนะเมื่อคืน",
    "อยากรู้ดวงวันนี้",
    "แนะนำร้านกาแฟหน่อย",
]


@pytest.fixture(scope="module", autouse=True)
def loaded_kb():
    knowledge_base.load()
    assert knowledge_base.ready, "โหลดเอกสารไม่สำเร็จ"
    return knowledge_base


# ── tokenizer ───────────────────────────────────────────────────
def test_course_code_stays_one_token():
    tokens = tokenize("วิชา 04100201-66 เปิดสอนเทอมนี้")
    assert "04100201-66" in tokens
    assert "04100201" in tokens  # ค้นแบบไม่ระบุปีหลักสูตรก็ต้องเจอ


def test_thai_ngram_size_is_3_and_4():
    tokens = tokenize("ลงทะเบียน")
    assert all(len(t) in (3, 4) for t in tokens), tokens


def test_english_and_digits_tokenized():
    tokens = tokenize("GPAX 2.00 credit")
    assert "gpax" in tokens and "credit" in tokens


# ── chunking ────────────────────────────────────────────────────
def test_frontmatter_parsed():
    meta, body = parse_frontmatter('---\ndoc_type: regulation\ntitle: "ทดสอบ"\n---\n# หัวข้อ\nเนื้อหา')
    assert meta["doc_type"] == "regulation"
    assert meta["title"] == "ทดสอบ"
    assert body.startswith("# หัวข้อ")


def test_split_by_heading_keeps_parent_path():
    """หัวข้อย่อยต้องพ่วงหัวข้อแม่มาด้วย (breadcrumb) ไม่งั้นแยกไม่ออกว่าอยู่ใต้อะไร"""
    parts = split_by_heading("# ก\nเนื้อ ก\n## ข\nเนื้อ ข")
    headings = [h for h, _ in parts]
    assert headings == ["ก", "ก > ข"]


def test_breadcrumb_distinguishes_repeated_headings():
    """แผนการศึกษามี 'ภาคการศึกษาที่ 1' ซ้ำทุกชั้นปี ต้องแยกออกจากกันได้"""
    body = (
        "## ชั้นปีที่ 1\n### ภาคการศึกษาที่ 1\nวิชาปี1เทอม1\n"
        "## ชั้นปีที่ 2\n### ภาคการศึกษาที่ 1\nวิชาปี2เทอม1\n"
    )
    headings = [h for h, _ in split_by_heading(body)]
    assert "ชั้นปีที่ 1 > ภาคการศึกษาที่ 1" in headings
    assert "ชั้นปีที่ 2 > ภาคการศึกษาที่ 1" in headings
    assert len(set(headings)) == len(headings), "breadcrumb ต้องไม่ซ้ำกัน"


def test_chunk_respects_max_chars():
    text = "\n".join(f"บรรทัดที่ {i} ทดสอบการหั่นข้อความยาว" * 3 for i in range(60))
    chunks = chunk_text(text, max_chars=500, overlap=50)
    assert len(chunks) > 1
    assert all(len(c) <= 600 for c in chunks)  # เผื่อขอบเขตการตัดที่ขึ้นบรรทัด


def test_short_text_not_chunked():
    assert chunk_text("สั้นมาก", 500, 50) == ["สั้นมาก"]


# ── คุณภาพการค้นคืน ─────────────────────────────────────────────
@pytest.mark.parametrize("question", ON_TOPIC)
def test_on_topic_scores_above_threshold(question):
    hits = knowledge_base.search(question, top_k=1)
    assert hits, f"ไม่เจอเอกสารสำหรับ: {question}"
    assert hits[0].score >= settings.min_score, (
        f"{question} ได้ {hits[0].score:.4f} ต่ำกว่าเกณฑ์ {settings.min_score}"
    )


@pytest.mark.parametrize("question", OFF_TOPIC)
def test_off_topic_scores_below_threshold(question):
    """คำถามนอกเรื่องต้องได้คะแนนต่ำกว่าเกณฑ์ ระบบจะได้ตอบว่า 'ไม่พบข้อมูล' แทนการเดา"""
    hits = knowledge_base.search(question, top_k=1)
    score = hits[0].score if hits else 0.0
    assert score < settings.min_score, f"{question} ได้ {score:.4f} หลุดเกณฑ์"


def test_credit_rule_question_finds_the_right_rule():
    """คำถามเรื่องหน่วยกิตต้องเจอเอกสารที่มีเลข 9 และ 21 จริง"""
    hits = knowledge_base.search("ลงทะเบียนได้กี่หน่วยกิตต่อเทอม", top_k=3)
    joined = " ".join(h.text for h in hits)
    assert "9" in joined and "21" in joined


def test_filter_by_doc_type():
    hits = knowledge_base.search("ปฏิทินการศึกษา เปิดภาคเรียน", top_k=3, doc_type="calendar")
    assert hits and all(h.doc_type == "calendar" for h in hits)


def test_scores_are_not_all_identical():
    """กันการถดถอยกลับไปใช้คะแนน RRF ซึ่งอันดับ 1 จะได้คะแนนเท่ากันเสมอ"""
    scores = [knowledge_base.search(q, top_k=1)[0].score for q in ON_TOPIC]
    assert len(set(round(s, 4) for s in scores)) > 1
