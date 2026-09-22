"""Tests for FastAPI HTTP Endpoints"""
import pytest
from fastapi.testclient import TestClient
from src.adapters.course_data import MemorySectionProvider
from src.adapters.student_data import MemoryStudentContextProvider
from src.api.routes import set_test_providers
from src.main import app
from src.models.schemas import (
    ConflictDetail,
    Meeting,
    SectionInput,
    StudentContextInput,
    WarningDetail,
)

client = TestClient(app)


@pytest.fixture(autouse=True)
def setup_api_providers():
    sec1 = SectionInput(
        id="CPE101-01",
        course_code="CPE101",
        section="01",
        credits=3,
        meetings=[Meeting(day=0, start_min=540, end_min=720)],
    )
    sec2 = SectionInput(
        id="CPE102-01",
        course_code="CPE102",
        section="01",
        credits=3,
        meetings=[Meeting(day=0, start_min=660, end_min=840)],
    )
    sec3 = SectionInput(
        id="CPE103-01",
        course_code="CPE103",
        section="01",
        credits=3,
        meetings=[Meeting(day=1, start_min=540, end_min=720)],
    )

    set_test_providers(
        MemorySectionProvider([sec1, sec2, sec3]),
        MemoryStudentContextProvider({
            "student_123": StudentContextInput(student_id="student_123", passed_courses=[])
        }),
    )
    yield
    set_test_providers(None, None)


def test_health_and_ready_probes():
    res_health = client.get("/health")
    assert res_health.status_code == 200
    assert res_health.json()["ok"] is True

    res_ready = client.get("/ready")
    assert res_ready.status_code == 200
    assert res_ready.json()["ready"] is True


def test_conflicts_check_endpoint():
    payload = {
        "term": "1/2569",
        "sections": ["CPE101-01", "CPE102-01"],
    }
    response = client.post("/conflicts/check", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["has_conflict"] is True
    assert len(data["conflicts"]) >= 1
    assert data["conflicts"][0]["code"] == "C1"


def test_validate_endpoint():
    payload = {
        "term": "1/2569",
        "section_ids": ["CPE101-01"],
    }
    response = client.post("/validate", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert "conflicts" in data
    assert "summary" in data
    assert data["summary"]["is_valid"] is True


def test_validate_endpoint_with_conflicts_has_contract_fields():
    """ยิง POST /validate ที่มี conflict แล้ว assert ว่า response JSON มี key type, message, section_ids, details"""
    payload = {
        "term": "1/2569",
        "section_ids": ["CPE101-01", "CPE102-01"],
    }
    response = client.post("/validate", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert "conflicts" in data
    assert len(data["conflicts"]) >= 1

    for conflict in data["conflicts"]:
        assert "type" in conflict
        assert "message" in conflict
        assert "section_ids" in conflict
        assert "details" in conflict
        assert isinstance(conflict["type"], str)
        assert isinstance(conflict["message"], str)
        assert isinstance(conflict["section_ids"], list)
        assert isinstance(conflict["details"], dict)


def test_preview_endpoint():
    payload = {
        "sections": [
            {
                "id": "CPE101-01",
                "course_code": "CPE101",
                "section": "01",
                "meetings": [{"day": 1, "start_min": 540, "end_min": 720}],
            },
            {
                "id": "CPE102-01",
                "course_code": "CPE102",
                "section": "01",
                "meetings": [{"day": 1, "start_min": 600, "end_min": 780}],
            },
        ]
    }
    response = client.post("/conflicts/preview", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["has_clash"] is True
    assert data["clash_count"] == 1


def test_generate_endpoint():
    payload = {
        "term": "1/2569",
        "preferences": {"no_early_class": False},
    }
    response = client.post("/generate", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert "plans" in data
    assert isinstance(data["plans"], list)
    assert len(data["plans"]) >= 1

    first_plan = data["plans"][0]
    assert "sections" in first_plan
    assert isinstance(first_plan["sections"], list)
    assert len(first_plan["sections"]) >= 1
    assert isinstance(first_plan["sections"][0], str)
    assert all(isinstance(s, str) for s in first_plan["sections"])


def test_computed_fields_serialization():
    """ตรวจสอบว่า Pydantic v2 serialize @computed_field ออกมาใน .model_dump() ครบถ้วน"""
    conflict = ConflictDetail(
        code="C1",
        message_key="time_clash",
        message_th="เวลาชนกัน",
        message_en="Time clash",
        subjects=["CPE101-01", "CPE102-01"],
        detail={"day": "MON", "overlap_start": "11:00", "overlap_end": "12:00"},
    )
    c_dump = conflict.model_dump()
    assert c_dump["type"] == "time_clash"
    assert c_dump["message"] == "เวลาชนกัน"
    assert c_dump["section_ids"] == ["CPE101-01", "CPE102-01"]
    assert c_dump["details"]["day"] == "MON"

    warning = WarningDetail(
        code="W1",
        message_key="early_class",
        message_th="เรียนเช้า",
        message_en="Early class",
        detail={"day": "MON"},
    )
    w_dump = warning.model_dump()
    assert w_dump["type"] == "early_class"
    assert w_dump["message"] == "เรียนเช้า"
    assert w_dump["details"]["day"] == "MON"

