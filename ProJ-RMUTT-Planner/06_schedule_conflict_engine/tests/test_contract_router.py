"""Contract Tests with Module 03 (03_ai_router_agent)
Verifies exact compatibility with 03's check_conflicts and generate_plan tool calls
"""
import pytest
from fastapi.testclient import TestClient
from src.adapters.course_data import MemorySectionProvider
from src.adapters.student_data import MemoryStudentContextProvider
from src.api.routes import set_test_providers
from src.api.schemas_router import RouterConflictResponse, RouterGenerateResponse
from src.main import app
from src.models.schemas import Meeting, SectionInput, StudentContextInput

client = TestClient(app)


@pytest.fixture(autouse=True)
def setup_test_environment():
    cpe101 = SectionInput(
        id="CPE101-01",
        course_code="CPE101",
        section="01",
        credits=3,
        meetings=[Meeting(day=0, start_min=540, end_min=720)],  # จันทร์ 09:00-12:00
        seat_total=40,
        seat_taken=10,
    )
    cpe102_clash = SectionInput(
        id="CPE102-01",
        course_code="CPE102",
        section="01",
        credits=3,
        meetings=[Meeting(day=0, start_min=660, end_min=840)],  # จันทร์ 11:00-14:00 (ชนกัน)
        seat_total=40,
        seat_taken=10,
    )
    cpe103_ok = SectionInput(
        id="CPE103-01",
        course_code="CPE103",
        section="01",
        credits=3,
        meetings=[Meeting(day=1, start_min=540, end_min=720)],  # อังคาร 09:00-12:00
        seat_total=40,
        seat_taken=10,
    )

    section_provider = MemorySectionProvider([cpe101, cpe102_clash, cpe103_ok])
    student_provider = MemoryStudentContextProvider({
        "synthetic_hash_123": StudentContextInput(
            student_id="synthetic_hash_123",
            passed_courses=["GEN101"],
        )
    })

    set_test_providers(section_provider, student_provider)
    yield
    set_test_providers(None, None)


def test_03_check_conflicts_payload_and_resolution():
    """1. /conflicts/check รับ payload ปัจจุบันของ 03 และ resolve ข้อมูลจริง"""
    payload = {
        "sections": ["CPE101-01", "CPE102-01"],
    }
    response = client.post("/conflicts/check", json=payload)
    assert response.status_code == 200

    data = response.json()
    validated = RouterConflictResponse.model_validate(data)
    assert validated.has_conflict is True
    assert any(c.code == "C1" for c in validated.conflicts)


def test_03_check_conflicts_unknown_section_fails():
    """2. Section ID ที่ไม่พบ ต้องคืน error 422 อย่างชัดเจน ไม่เดาข้อมูล"""
    payload = {
        "sections": ["UNKNOWN999-01"],
    }
    response = client.post("/conflicts/check", json=payload)
    assert response.status_code == 422
    assert response.json()["detail"]["code"] == "SECTION_NOT_FOUND"


def test_03_auto_plan_payload_with_hash():
    """3. /plans/auto รับ student hash และ resolve ผ่าน StudentContextProvider"""
    payload = {
        "student_id": "synthetic_hash_123",
        "term": "1/2569",
        "preferences": {
            "free_days": ["FRI"],
            "no_early_class": True,
            "max_credits": 18,
        },
    }
    response = client.post("/plans/auto", json=payload)
    assert response.status_code == 200

    data = response.json()
    validated = RouterGenerateResponse.model_validate(data)
    assert validated.term == "1/2569"


def test_03_auto_plan_unknown_hash_fails():
    """4. Student hash ที่ไม่พบ ต้องคืน error ชัดเจน ไม่สร้าง context ว่าง"""
    payload = {
        "student_id": "non_existent_hash_999",
        "term": "1/2569",
    }
    response = client.post("/plans/auto", json=payload)
    assert response.status_code == 422
    assert response.json()["detail"]["code"] == "STUDENT_NOT_FOUND"
