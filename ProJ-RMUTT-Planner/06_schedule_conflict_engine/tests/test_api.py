"""Tests for FastAPI HTTP Endpoints"""
import pytest
from fastapi.testclient import TestClient
from src.adapters.course_data import MemorySectionProvider
from src.adapters.student_data import MemoryStudentContextProvider
from src.api.routes import set_test_providers
from src.main import app
from src.models.schemas import Meeting, SectionInput, StudentContextInput

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
