"""เทสกันบั๊กย้อนกลับจากรอบ user test — ทุกเคสในไฟล์นี้เคยพังจริง

ปัญหาที่เจอตอนทดสอบแบบผู้ใช้ (12/12 คำถามมีปัญหา):
 1. sources ที่แนบกลับ ไม่ตรงกับเอกสารที่คำตอบใช้จริง
 2. ลำดับผลลัพธ์ไม่เรียงตามคะแนนที่แสดง (เรียงด้วย RRF แต่โชว์ cosine)
 3. /knowledge/search กับ /generate ให้ผลต่างกันสำหรับคำถามเดียวกัน
 4. ค้นด้วยรหัสวิชา / ชั้นปี-ภาคการศึกษา แล้วได้ผิดอัน
"""
import pytest
from fastapi.testclient import TestClient

from src.core.text import expand_query, section_hints
from src.llm.client import RULE_BASED_MAX_CHUNKS
from src.main import app
from src.services.knowledge import knowledge_base


@pytest.fixture(scope="module")
def client():
    knowledge_base.load()
    with TestClient(app) as c:
        yield c


# ── 1. sources ต้องตรงกับคำตอบ ──────────────────────────────────
@pytest.mark.parametrize("question", [
    "ลงทะเบียนได้กี่หน่วยกิตต่อเทอม",
    "ถอนรายวิชาได้ถึงเมื่อไหร่",
    "ได้ F ต้องทำยังไง",
])
def test_sources_match_what_answer_actually_used(client, question):
    body = client.post("/generate", json={"question": question, "top_k": 6}).json()
    assert body["grounded"] is True

    # โหมด rule_based ยกข้อความมา 3 ชิ้น -> sources ต้องมี 3 ชิ้น ไม่ใช่ 6
    assert len(body["sources"]) == RULE_BASED_MAX_CHUNKS

    # ทุกแหล่งอ้างอิงต้องปรากฏในคำตอบจริง
    for s in body["sources"]:
        assert s["section"] in body["answer"], f"{s['section']} ไม่อยู่ในคำตอบ"

    # จำนวนที่อ้าง [n] ในคำตอบ ต้องเท่ากับจำนวน sources
    import re
    assert len(re.findall(r"\[\d+\]", body["answer"])) == len(body["sources"])


# ── 2. ลำดับต้องเรียงตามคะแนนที่แสดง ────────────────────────────
@pytest.mark.parametrize("question", [
    "ลงทะเบียนได้กี่หน่วยกิตต่อเทอม",
    "ถอนรายวิชาได้ถึงเมื่อไหร่",
    "สอบปลายภาค เทอม 1/2569 วันไหน",
    "ที่นั่งเต็มทำยังไง",
])
def test_results_sorted_by_displayed_score(client, question):
    chunks = client.post("/knowledge/search", json={"query": question, "top_k": 6}).json()["chunks"]
    scores = [c["score"] for c in chunks]
    assert scores == sorted(scores, reverse=True), (
        f"ลำดับไม่ตรงกับคะแนนที่แสดง: {scores}"
    )


# ── 3. สองปลายทางต้องให้ผลตรงกัน ────────────────────────────────
@pytest.mark.parametrize("question", [
    "ลงทะเบียนได้กี่หน่วยกิตต่อเทอม",
    "สอบกลางภาค เทอม 1/2569 วันไหน",
    "GPAX ต้องได้เท่าไหร่ถึงจะจบ",
])
def test_search_and_generate_agree(client, question):
    """โมดูล 03 เรียกทั้งสอง endpoint ถ้าให้ผลต่างกันผู้ใช้จะเห็นข้อมูลขัดกันเอง"""
    search = client.post("/knowledge/search", json={"query": question, "top_k": 6}).json()
    gen = client.post("/generate", json={"question": question, "top_k": 6}).json()
    assert search["chunks"][0]["doc_id"] == gen["sources"][0]["doc_id"]


# ── 4. ค้นด้วยรหัสวิชา / ชั้นปี ต้องได้ตรงอัน ───────────────────
def test_course_code_finds_the_table_that_contains_it(client):
    """chunk ตารางหลักสูตรยาวมาก TF-IDF หารคะแนนตก ต้องมีโบนัสรหัสวิชาช่วย"""
    chunks = client.post(
        "/knowledge/search", json={"query": "วิชา 04100203-66 ต้องผ่านอะไรก่อน", "top_k": 6}
    ).json()["chunks"]
    assert any("04100203-66" in c["text"] for c in chunks[:3]), \
        "เอกสารที่มีรหัสวิชาที่ถาม ต้องติด 3 อันดับแรก"


@pytest.mark.parametrize("year,term", [(1, 1), (2, 1), (2, 2), (3, 1), (4, 2)])
def test_year_and_term_question_returns_that_exact_section(client, year, term):
    """เลขชั้นปี/ภาคเรียนมี IDF ต่ำมาก ถ้าไม่ boost จาก breadcrumb จะได้ผิดปี"""
    q = f"ปี {year} เทอม {term} ต้องเรียนวิชาอะไรบ้าง"
    chunks = client.post("/knowledge/search", json={"query": q, "top_k": 3}).json()["chunks"]
    top = chunks[0]["section"]
    assert f"ชั้นปีที่ {year}" in top and f"ภาคการศึกษาที่ {term}" in top, \
        f"ถาม ปี{year} เทอม{term} แต่ได้ '{top}'"


def test_section_hints_extracted():
    assert section_hints("ปี 2 เทอม 1 เรียนอะไร") == ["ชั้นปีที่ 2", "ภาคการศึกษาที่ 1"]
    assert section_hints("ถอนวิชาได้ถึงเมื่อไหร่") == []


# ── 5. การขยายคำถามต้องไม่ทับซ้อนจนกลบคำถามเดิม ─────────────────
def test_expansion_picks_specific_topic_not_both():
    """'เรียนกี่หน่วยกิตถึงจะจบ' ต้องไปทางหน่วยกิตตลอดหลักสูตร ไม่ใช่หน่วยกิตต่อเทอม"""
    expanded = expand_query("หลักสูตรวิศวะคอมต้องเรียนกี่หน่วยกิตถึงจะจบ")
    assert "ตลอดหลักสูตร" in expanded
    assert "ต่อภาคการศึกษา" not in expanded


def test_total_credits_question_returns_curriculum_not_term_rule(client):
    body = client.post(
        "/generate", json={"question": "หลักสูตรวิศวะคอมต้องเรียนกี่หน่วยกิตถึงจะจบ"}
    ).json()
    assert "143" in body["answer"], "ต้องตอบหน่วยกิตรวมตลอดหลักสูตร"


# ── 6. ยังต้องปฏิเสธคำถามนอกเรื่องเหมือนเดิม ────────────────────
@pytest.mark.parametrize("question", [
    "ราคาข้าวมันไก่เท่าไหร่",
    "วิธีเปลี่ยนยางรถยนต์",
    "ทีมฟุตบอลไหนชนะเมื่อคืน",
    "ปี 2 นี้หุ้นตัวไหนน่าซื้อ",
])
def test_boosts_do_not_let_off_topic_through(client, question):
    """โบนัสรหัสวิชา/ชั้นปี ต้องไม่ดันคำถามนอกเรื่องให้ผ่านเกณฑ์"""
    body = client.post("/generate", json={"question": question}).json()
    assert body["grounded"] is False, f"{question} ไม่ควรตอบได้"
