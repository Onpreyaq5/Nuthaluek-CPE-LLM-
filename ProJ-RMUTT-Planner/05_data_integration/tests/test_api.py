from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from src.main import app

client = TestClient(app)
FIX = Path(__file__).parent / "fixtures"


def test_api_health():
    res = client.get("/health")
    assert res.status_code == 200
    assert res.json() == {"ok": True, "service": "05_data_integration"}


def test_api_get_prereq():
    # 040603002 (โครงสร้างข้อมูล) ต้องผ่าน 040603001 (เขียนโปรแกรม)
    res = client.get("/prereq/040603002")
    assert res.status_code == 200
    data = res.json()
    assert "040603001" in data["direct_prerequisites"]
    assert "040603003" in data["direct_unlocks"]  # ปลดล็อกระบบฐานข้อมูล


def test_api_get_context():
    res = client.get("/context/sample")
    assert res.status_code == 200
    data = res.json()
    assert "student_id" in data
    assert "academic_summary" in data
    assert "preferences" in data


def test_api_get_eligible():
    res = client.get("/eligible/sample")
    assert res.status_code == 200
    data = res.json()
    assert "eligible_courses" in data
    assert data["eligible_count"] >= 0


def test_api_transcript_parse_csv():
    csv_payload = {
        "content": "course_code,grade,credits\n04000201-62,A,3\n04000202-62,F,3",
        "format": "csv",
    }
    res = client.post("/transcript/parse", json=csv_payload)
    assert res.status_code == 200
    data = res.json()
    assert "04000201-62" in data["passed_courses"]
    assert "04000202-62" in data["failed_courses"]


def test_api_normalize_courses():
    payload = {
        "courses": [
            {
                "code": " 04000201 - 62 ",
                "name_th": "ฟิสิกส์ 1",
                "credit_detail": "3(2-2-5)",
                "sections": [
                    {
                        "section": "01",
                        "meetings": [
                            {"day": "จ.", "start_min": "09:00", "end_min": "12:00"}
                        ],
                    }
                ],
                "prerequisites": [],
            }
        ]
    }
    res = client.post("/normalize/courses", json=payload)
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "success"
    course = data["courses"][0]
    assert course["code"] == "04000201-62"
    assert course["credits"] == 3
    assert course["sections"][0]["slots_mask"] > 0


def test_api_clash_check():
    # จันทร์ 09:00-12:00 ชนกับ จันทร์ 10:00-11:00
    payload = {
        "meetings_a": [{"day": "จ.", "start_min": "09:00", "end_min": "12:00"}],
        "meetings_b": [{"day": "MON", "start_min": "10:00", "end_min": "11:00"}],
    }
    res = client.post("/slots/clash-check", json=payload)
    assert res.status_code == 200
    data = res.json()
    assert data["has_clash"] is True
    assert data["overlap_count"] == 1


def test_api_search_courses():
    res = client.get("/search/courses?q=ฟิสิกส์")
    assert res.status_code == 200
    data = res.json()
    assert data["count"] > 0
    assert "04000201-62" in [r["code"] for r in data["results"]]


def test_api_get_context_shape_for_02_and_03():
    res = client.get("/students/sample/context")
    assert res.status_code == 200
    data = res.json()
    # Contract requirements for 02/03/06/07
    assert "student_id" in data
    assert "id_hash" in data
    assert "program_id" in data
    assert "program_name" in data
    assert "curriculum_year" in data
    assert "year_level" in data
    assert "credits_earned" in data
    assert "credits_remaining" in data
    assert "gpax" in data
    assert "completed_course_codes" in data
    assert "preferences" in data
    # Check free_days in MON..SUN format
    if "free_days" in data["preferences"]:
        assert all(isinstance(d, str) for d in data["preferences"]["free_days"])


def test_api_get_transcript_for_02():
    res = client.get("/students/sample/transcript")
    assert res.status_code == 200
    data = res.json()
    assert "courses" in data
    assert "credits_by_category" in data
    assert isinstance(data["courses"], list)
    assert isinstance(data["credits_by_category"], dict)

    # 404 for unknown student
    res_404 = client.get("/students/unknown_student_9999/transcript")
    assert res_404.status_code == 404


def test_api_import_graduate_check():
    sample_file = FIX / "graduate_check_sample.html"
    if not sample_file.exists():
        pytest.skip("Fixture not found")

    raw_html = sample_file.read_bytes()
    res = client.post(
        "/import/graduate-check",
        content=raw_html,
        headers={"Content-Type": "text/html"},
    )
    assert res.status_code == 200
    data = res.json()
    assert data["imported_courses"] > 0
    # Must not report fake 0 remaining credits
    assert data["credits_remaining"] != 0
    assert data["credits_remaining"] == 123
    assert isinstance(data["retake_required"], list)
    assert isinstance(data["warnings"], list)

