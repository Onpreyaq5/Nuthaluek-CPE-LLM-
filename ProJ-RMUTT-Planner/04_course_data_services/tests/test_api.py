import pytest
from fastapi.testclient import TestClient
from src.main import app

client = TestClient(app)

def test_health():
    response = client.get("/health")
    assert response.status_code == 200
    body = response.json()
    assert body["ok"] is True and body["service"] == "04_course_data_services"
    # รันเทสโดยไม่ตั้ง SEED_DIR = ใช้ข้อมูลตัวอย่าง
    assert body["source"] == "mock"

def test_list_courses():
    response = client.get("/courses?q=CPE")
    assert response.status_code == 200
    data = response.json()
    assert "items" in data
    assert "next_cursor" in data
    assert len(data["items"]) > 0
    
    # Assert schema shape
    course = data["items"][0]
    assert "code" in course
    assert "name_th" in course
    assert "credits" in course

def test_list_sections():
    response = client.get("/courses/CPE301/sections")
    assert response.status_code == 200
    data = response.json()
    assert "items" in data
    assert len(data["items"]) > 0
    
    # Assert schema shape
    section = data["items"][0]
    assert "section_id" in section
    assert "course_code" in section
    assert "meetings" in section
    assert isinstance(section["meetings"], list)

def test_sections_bulk():
    response = client.post("/sections/bulk", json={"ids": ["CPE301-01"]})
    assert response.status_code == 200
    data = response.json()
    assert "items" in data
    assert len(data["items"]) == 1
    assert data["items"][0]["section_id"] == "CPE301-01"

def test_search_courses_for_03():
    response = client.post("/courses/search", json={"q": "ข้อมูล", "term": "1/2569"})
    assert response.status_code == 200
    data = response.json()
    assert "items" in data
    assert len(data["items"]) > 0
    assert data["items"][0]["code"] == "CPE301"


# ── ตารางสอนจริง: สัญญาที่ 02 และ 06 ใช้ ─────────────────────────────
SEED = __import__("pathlib").Path(__file__).resolve().parents[2] / "09_main_app" / "data" / "seed"


@pytest.fixture
def real_store():
    from src.store import CourseStore

    if not SEED.exists():
        pytest.skip("ไม่มีตารางสอนจริงในเครื่องนี้")
    return CourseStore(SEED)


def test_real_seed_loads_both_terms(real_store):
    assert set(real_store.terms) >= {"1/2569", "2/2569"}
    assert real_store.source != "mock"


def test_backend_and_engine_shapes_describe_same_section(real_store):
    raw = real_store.sections("1/2569")[0]
    backend = real_store.get_sections_by_ids([raw["id"]], "1/2569")[0]
    engine = real_store.get_engine_sections_by_ids([raw["id"]], "1/2569")[0]
    assert backend["section_id"] == engine["id"] == raw["id"]
    m = engine["meetings"][0]
    hh, mm = backend["meetings"][0]["start"].split(":")
    assert int(hh) * 60 + int(mm) == m["start_min"]
    assert backend["meetings"][0]["day"] == ["MON", "TUE", "WED", "THU", "FRI", "SAT", "SUN"][m["day"]]


def test_engine_search_returns_sections_for_autoplan(real_store):
    # 06 ขอ course_codes ว่าง = ทุกกลุ่มเรียนที่เปิดในภาคนั้น
    assert len(real_store.open_engine_sections("1/2569", [])) == len(real_store.sections("1/2569"))
    one = real_store.sections("1/2569")[0]["course_code"]
    assert {s["course_code"] for s in real_store.open_engine_sections("1/2569", [one])} == {one}


def test_unknown_term_is_empty_not_default(real_store):
    assert real_store.sections("3/2599") == []
