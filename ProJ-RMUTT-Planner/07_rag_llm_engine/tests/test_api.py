"""ทดสอบ endpoint — path ต้องตรงกับที่โมดูล 03 เรียกใช้"""
import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from src.main import app
from src.services.knowledge import knowledge_base

SEED = Path(__file__).resolve().parent.parent / "data" / "seed" / "cpe_timetable_1_2569.json"


@pytest.fixture(scope="module")
def client():
    knowledge_base.load()
    with TestClient(app) as c:
        yield c


def test_health(client):
    r = client.get("/health")
    assert r.status_code == 200
    body = r.json()
    assert body["ok"] is True
    assert body["documents"] > 0


def test_knowledge_search_contract(client):
    """path และ payload ต้องตรงกับ 03/src/tools.py::search_knowledge"""
    r = client.post("/knowledge/search", json={"query": "ถอนรายวิชาได้ถึงเมื่อไหร่", "top_k": 6})
    assert r.status_code == 200
    body = r.json()
    assert body["found"] is True
    assert body["chunks"]
    assert body["chunks"][0]["title"]
    assert body["top_score"] > 0


def test_knowledge_search_off_topic_not_found(client):
    r = client.post("/knowledge/search", json={"query": "ราคาข้าวมันไก่เท่าไหร่", "top_k": 6})
    assert r.status_code == 200
    assert r.json()["found"] is False


def test_generate_grounded_answer_has_sources(client):
    """path และ payload ต้องตรงกับ 03/src/tools.py::answer_with_llm"""
    r = client.post("/generate", json={
        "question": "ลงทะเบียนได้กี่หน่วยกิตต่อเทอม",
        "context": {"student": {"program_id": "CPE-2566", "curriculum_year": 2566}},
    })
    assert r.status_code == 200
    body = r.json()
    assert body["grounded"] is True
    assert body["sources"], "คำตอบที่อ้างระเบียบต้องมีแหล่งอ้างอิง"
    assert "21" in body["answer"] or "9" in body["answer"]
    assert body["disclaimer"]


def test_generate_refuses_when_no_evidence(client):
    r = client.post("/generate", json={"question": "ทีมฟุตบอลไหนชนะเมื่อคืน", "context": {}})
    assert r.status_code == 200
    body = r.json()
    assert body["grounded"] is False
    assert body["sources"] == []
    assert "ไม่พบข้อมูล" in body["answer"]


def test_explain_plan_endpoint(client):
    r = client.post("/explain/plan", json={
        "term": "1/2569",
        "plan": [{"course_code": "04100201-66", "section": "01", "credits": 3}],
        "conflicts": [{
            "code": "C4", "severity": "ERROR", "message_key": "credit_limit",
            "detail": {"total_credits": 3},
        }],
    })
    assert r.status_code == 200
    body = r.json()
    assert body["verdict"] == "blocked"
    assert body["credit_check"]["status"] == "under"


def test_ingest_reloads(client):
    r = client.post("/ingest")
    assert r.status_code == 200
    body = r.json()
    assert body["chunks"] > 0
    assert body["documents"] == len(body["files"])


# ── ข้อมูลจำลองตารางเรียนวิศวะคอม ───────────────────────────────
def test_seed_timetable_endpoint(client):
    r = client.get("/seed/timetable", params={"term": "1/2569"})
    assert r.status_code == 200
    data = r.json()
    assert data["program_id"] == "CPE-2566"
    assert data["credit_rule"] == {"min_credits": 9, "max_credits": 21, "summer_max_credits": 9}
    assert len(data["sections"]) >= 15


def test_seed_timetable_unknown_term_404(client):
    assert client.get("/seed/timetable", params={"term": "9/9999"}).status_code == 404


def test_seed_sections_match_module_06_schema():
    """ฟิลด์ต้องครบตาม SectionInput ของโมดูล 06 ไม่งั้นส่งต่อไปไม่ได้"""
    data = json.loads(SEED.read_text(encoding="utf-8"))
    required = {"id", "course_code", "section", "credits", "slots_mask",
                "meetings", "exams", "seat_total", "seat_taken", "prerequisites"}
    for s in data["sections"]:
        assert required <= set(s), f"{s['id']} ขาดฟิลด์ {required - set(s)}"
        for m in s["meetings"]:
            assert 0 <= m["day"] <= 6
            assert m["start_min"] < m["end_min"]


def test_seed_contains_a_real_time_clash():
    """ต้องมีคู่ที่ชนกันจริง ไม่งั้นเดโม่ตัวตรวจตารางชนไม่ได้"""
    data = json.loads(SEED.read_text(encoding="utf-8"))
    by_id = {s["id"]: s for s in data["sections"]}
    a, b = by_id["04100201-66-01"], by_id["04100202-66-01"]
    assert a["slots_mask"] & b["slots_mask"], "คู่นี้ควรชนกัน"
    c = by_id["04100201-66-02"]
    assert not (c["slots_mask"] & b["slots_mask"]), "คู่นี้ไม่ควรชนกัน"


def test_seed_contains_a_real_exam_clash():
    data = json.loads(SEED.read_text(encoding="utf-8"))
    by_id = {s["id"]: s for s in data["sections"]}

    def midterm(sec):
        return next(e for e in by_id[sec]["exams"] if e["exam_type"] == "midterm")

    a, b = midterm("04100203-66-01"), midterm("04000207-63-01")
    assert a["exam_date"] == b["exam_date"]
    assert a["start_min"] < b["end_min"] and b["start_min"] < a["end_min"]


def test_query_expansion_does_not_leak_into_unrelated_questions(client):
    """กันบั๊กเดิม: คำว่า 'ชน' ไปตรงกับ 'ชนะ' ทำให้คำถามฟุตบอลถูกดันคะแนนจนผ่านเกณฑ์"""
    for q in ["ทีมฟุตบอลไหนชนะเมื่อคืน", "ใครชนะการเลือกตั้ง", "แข่งชนะไหม"]:
        body = client.post("/generate", json={"question": q, "context": {}}).json()
        assert body["grounded"] is False, f"{q} ไม่ควรตอบได้"


def test_real_questions_still_expand(client):
    """คำถามจริงที่สั้นมากยังต้องค้นเจอ"""
    for q in ["ถอนรายวิชาได้ถึงเมื่อไหร่", "ตารางชนกันทำไง", "กี่หน่วยกิตถึงจะจบ"]:
        body = client.post("/generate", json={"question": q, "context": {}}).json()
        assert body["grounded"] is True, f"{q} ควรตอบได้"
