"""เทสจาก user test รอบ 2 — ระบบต้องรู้ว่าตัวเองไม่รู้อะไร

ปัญหาที่เจอรอบ 2 (13 คำถาม พบปัญหา 5 ข้อ):
 - ถาม "เทอม 2/2569 วิชา X เรียนวันไหน" ได้ chunk แผนการศึกษา คะแนน 0.5452
   ทั้งที่ chunk นั้นไม่มีวัน-เวลาเรียนเลย เพราะคลังไม่มีตารางสอนตั้งแต่แรก
   -> เกณฑ์คะแนนวัดได้แค่ "เกี่ยวข้องไหม" ไม่ได้วัด "มีคำตอบไหม"
 - ถาม "เกรด B+ ได้กี่แต้ม" ค้นไม่เจอ เพราะเอกสารเขียน "ระดับคะแนน" ไม่ใช่ "เกรด"
   และเครื่องหมาย + หายไปตอนตัดคำ ทำให้ B+ กับ B เป็นคำเดียวกัน
"""
import pytest
from fastapi.testclient import TestClient

from src.core.text import expand_query, tokenize
from src.main import app
from src.services.coverage import COVERAGE_GAPS, coverage_summary, find_gap
from src.services.knowledge import knowledge_base


@pytest.fixture(scope="module")
def client():
    knowledge_base.load()
    with TestClient(app) as c:
        yield c


# ── ระบบต้องบอกว่าไม่มีข้อมูล ───────────────────────────────────
@pytest.mark.parametrize("question,topic", [
    ("เทอม 2/2569 วิชา 04100205-66 เรียนวันไหน", "timetable"),
    ("วิชานี้เรียนกี่โมง", "timetable"),
    ("อาจารย์ที่ปรึกษาของผมคือใคร", "advisor"),
    ("ค่าเทอมเท่าไหร่", "fees"),
    ("หอพักในมหาลัยสมัครยังไง", "facility"),
    ("ขอทุนการศึกษายังไง", "scholarship"),
])
def test_known_gaps_answered_honestly(client, question, topic):
    gap = find_gap(question)
    assert gap is not None and gap.topic == topic

    body = client.post("/generate", json={"question": question}).json()
    assert body["grounded"] is False, "ต้องไม่อ้างว่าตอบได้"
    assert body["provider"] == "coverage_gap"
    assert body["sources"] == [], "ไม่มีข้อมูลก็ต้องไม่แนบแหล่งอ้างอิง"
    assert len(body["answer"]) > 20, "ต้องบอกด้วยว่าไปหาข้อมูลได้ที่ไหน"


def test_gap_check_runs_before_retrieval(client):
    """เคสนี้เคยได้คะแนน 0.5452 (สูงมาก) แต่ chunk ไม่มีคำตอบ
    ถ้าปล่อยให้ค้นก่อนจะหลุดเกณฑ์ไปตอบ"""
    q = "เทอม 2/2569 วิชา 04100205-66 เรียนวันไหน"
    search = client.post("/knowledge/search", json={"query": q, "top_k": 3}).json()
    assert search["found"] is True and search["top_score"] > 0.4, "การค้นยังเจอเอกสารใกล้เคียง"

    gen = client.post("/generate", json={"question": q}).json()
    assert gen["grounded"] is False, "แต่ /generate ต้องไม่ตอบ เพราะไม่มีตารางสอนในคลัง"


def test_questions_with_data_are_not_blocked_by_gaps(client):
    """คำถามที่ตอบได้ ต้องไม่ถูกดักด้วย coverage gap โดยผิดพลาด"""
    for q in ["ลงทะเบียนได้กี่หน่วยกิตต่อเทอม", "ถอนรายวิชาได้ถึงเมื่อไหร่",
              "ปี 2 เทอม 1 ต้องเรียนวิชาอะไรบ้าง", "หมวดวิชาศึกษาทั่วไปต้องเก็บกี่หน่วยกิต",
              "วิชาเลือกเสรีมีอะไรให้เลือกบ้าง"]:
        assert find_gap(q) is None, f"{q} ไม่ควรถูกจัดเป็นช่องว่างข้อมูล"
        assert client.post("/generate", json={"question": q}).json()["grounded"] is True


def test_health_declares_coverage(client):
    body = client.get("/health").json()
    assert "coverage" in body
    assert body["coverage"]["has"] and body["coverage"]["missing"]
    assert "จำลอง" in body["coverage"]["note"], "ต้องบอกว่าเป็นข้อมูลจำลอง"


def test_every_gap_has_a_useful_message():
    for gap in COVERAGE_GAPS:
        assert gap.keywords, f"{gap.topic} ไม่มีคำที่จับ"
        assert len(gap.message) > 20, f"{gap.topic} ข้อความสั้นเกินไป"
    assert len(coverage_summary()["missing"]) == len(COVERAGE_GAPS)


# ── คำศัพท์ที่ผู้ใช้กับเอกสารเรียกไม่เหมือนกัน ──────────────────
def test_plus_sign_kept_in_grade_token():
    """ถ้า + หลุด 'B+' กับ 'B' จะกลายเป็น token เดียวกัน แยกเกรดไม่ออก"""
    tokens = tokenize("เกรด B+ ได้กี่แต้ม")
    assert "b+" in tokens
    assert "b" not in tokens


@pytest.mark.parametrize("question,expected_word", [
    ("เกรด B+ ได้กี่แต้ม", "ระดับคะแนน"),
    ("ลาพักการเรียนติดต่อกันได้กี่เทอม", "ลาพักการศึกษา"),
    ("ได้ F ต้องทำยังไง", "การเรียนซ้ำ"),
])
def test_vocabulary_gap_bridged_by_expansion(question, expected_word):
    """ผู้ใช้พูดคำหนึ่ง เอกสารเขียนอีกคำ ต้องแปลงให้ตรงกันก่อนค้น"""
    assert expected_word in expand_query(question)


@pytest.mark.parametrize("question,must_contain", [
    ("เกรด B+ ได้กี่แต้ม", "3.50"),
    ("ลาพักการเรียนติดต่อกันได้กี่เทอม", "ลาพัก"),
    ("หมวดวิชาศึกษาทั่วไปต้องเก็บกี่หน่วยกิต", "30"),
    ("สหกิจศึกษาต้องผ่านอะไรก่อน", "48"),
    ("วิชา 04100301-66 ปัญญาประดิษฐ์ อยู่ปีไหน", "ชั้นปีที่ 3"),
])
def test_answers_contain_the_actual_fact(client, question, must_contain):
    body = client.post("/generate", json={"question": question}).json()
    assert body["grounded"] is True, f"{question} ควรตอบได้"
    assert must_contain in body["answer"], f"คำตอบควรมี '{must_contain}'"


# ── เอกสารคำอธิบายรายวิชาที่เพิ่มเข้ามา ─────────────────────────
@pytest.mark.parametrize("question,must_contain", [
    ("วิชาชีพเลือกมีอะไรบ้าง", "04100501-66"),
    ("คอมพิวเตอร์วิทัศน์เรียนเกี่ยวกับอะไร", "ภาพ"),
    ("04100302-66 การเรียนรู้ของเครื่อง เนื้อหาวิชาเป็นยังไง", "การเรียนรู้"),
])
def test_course_description_answerable(client, question, must_contain):
    """เพิ่ม 05_cpe_course_descriptions.md แล้ว ต้องตอบเรื่องเนื้อหาวิชาได้"""
    body = client.post("/generate", json={"question": question}).json()
    assert body["grounded"] is True, f"{question} ควรตอบได้แล้ว"
    assert must_contain in body["answer"]
