"""Contract Tests with Module 02 (02_api_backend)
Verifies exact compatibility with 02's PlanValidateRequest, PlanValidateResponse, and GeneratedPlan
"""
import pytest
from fastapi.testclient import TestClient
from src.adapters.course_data import MemorySectionProvider
from src.adapters.student_data import MemoryStudentContextProvider
from src.api.routes import set_test_providers
from src.api.schemas_backend import (
    BackendGeneratedPlan,
    BackendGenerateResponse,
    BackendValidateResponse,
)
from src.main import app
from src.models.schemas import Exam, Meeting, SectionInput, StudentContextInput

client = TestClient(app)


@pytest.fixture(autouse=True)
def setup_test_environment():
    # Setup test sections
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
        meetings=[Meeting(day=0, start_min=660, end_min=840)],  # จันทร์ 11:00-14:00 (ชน 11:00-12:00)
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
    cpe201_prereq = SectionInput(
        id="CPE201-01",
        course_code="CPE201",
        section="01",
        credits=3,
        prerequisites=["CPE101"],
        meetings=[Meeting(day=2, start_min=540, end_min=720)],  # พุธ 09:00-12:00
        seat_total=40,
        seat_taken=10,
    )

    section_provider = MemorySectionProvider([cpe101, cpe102_clash, cpe103_ok, cpe201_prereq])
    student_provider = MemoryStudentContextProvider()

    set_test_providers(section_provider, student_provider)
    yield
    set_test_providers(None, None)


def test_02_validate_endpoint_contract():
    """1. Payload /validate ตาม contract ของ 02 ต้องประมวลผลได้ และ validate ด้วย BackendValidateResponse"""
    payload = {
        "term": "1/2569",
        "section_ids": ["CPE101-01", "CPE102-01"],
        "student": {
            "student_id": "116610462000-0",
            "id_hash": "hash123",
            "program_id": "CPE-2566",
            "completed_course_codes": ["GEN101"],
            "preferences": {
                "free_days": ["FRI"],
                "no_early_class": True,
                "max_credits": 18,
            },
        },
    }
    response = client.post("/validate", json=payload)
    assert response.status_code == 200

    data = response.json()
    # ตรวจสอบว่า serialize ได้ field ตามที่ 02 คาดหวัง
    validated = BackendValidateResponse.model_validate(data)
    assert len(validated.conflicts) >= 1

    conflict = validated.conflicts[0]
    assert conflict.type == "time_clash"
    assert "CPE101-01" in conflict.section_ids
    assert "CPE102-01" in conflict.section_ids
    assert conflict.details["day"] == "MON"
    assert conflict.details["overlap_start"] == "11:00"
    assert conflict.details["overlap_end"] == "12:00"
    assert validated.summary.is_valid is False


def test_02_validate_prereq_and_completed_courses():
    """2. completed_course_codes จาก 02 ต้องถูกนำมาตรวจ Prereq จริง"""
    payload_without_prereq = {
        "term": "1/2569",
        "section_ids": ["CPE201-01"],
        "student": {
            "completed_course_codes": ["GEN101"],  # ยังไม่ผ่าน CPE101
        },
    }
    res = client.post("/validate", json=payload_without_prereq)
    assert res.status_code == 200
    data = res.json()
    val = BackendValidateResponse.model_validate(data)
    assert any(c.type == "prereq_fail" for c in val.conflicts)

    # กรณีผ่าน CPE101 แล้ว
    payload_with_prereq = {
        "term": "1/2569",
        "section_ids": ["CPE201-01"],
        "student": {
            "completed_course_codes": ["CPE101"],  # ผ่านแล้ว
        },
    }
    res_ok = client.post("/validate", json=payload_with_prereq)
    assert res_ok.status_code == 200
    val_ok = BackendValidateResponse.model_validate(res_ok.json())
    assert not any(c.type == "prereq_fail" for c in val_ok.conflicts)


def test_02_generate_endpoint_contract():
    """3. Response /generate ต้องตรงกับ BackendGenerateResponse และ sections เป็น list[str]"""
    payload = {
        "term": "1/2569",
        "preferences": {
            "free_days": ["FRI"],
            "no_early_class": True,
            "max_credits": 18,
        },
        "student": {
            "completed_course_codes": ["GEN101"],
        },
        "must_include": ["CPE101"],
        "exclude": ["CPE102"],
    }
    response = client.post("/generate", json=payload)
    assert response.status_code == 200

    data = response.json()
    validated = BackendGenerateResponse.model_validate(data)
    assert "plans" in data

    if validated.plans:
        plan = validated.plans[0]
        # sections ต้องเป็น list[str] ไม่ใช่ object!
        assert isinstance(plan.sections, list)
        assert all(isinstance(s, str) for s in plan.sections)
        assert "CPE101-01" in plan.sections
        assert "CPE102-01" not in plan.sections  # ถูก exclude
        assert plan.explanation is None
        assert isinstance(plan.warnings, list)
        assert all(isinstance(w, str) for w in plan.warnings)
