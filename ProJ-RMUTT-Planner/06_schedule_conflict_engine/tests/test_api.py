"""Tests for FastAPI HTTP Endpoints"""
from fastapi.testclient import TestClient
from src.main import app

client = TestClient(app)


def test_health_check():
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["ok"] is True
    assert data["service"] == "06_schedule_conflict_engine"


def test_conflicts_check_endpoint():
    payload = {
        "term": "1/2569",
        "sections": [
            {
                "id": "CPE101-01",
                "course_code": "CPE101",
                "section": "01",
                "meetings": [{"day": 0, "start_min": 540, "end_min": 720}],
            },
            {
                "id": "CPE102-01",
                "course_code": "CPE102",
                "section": "01",
                "meetings": [{"day": 0, "start_min": 660, "end_min": 840}],
            },
        ],
    }
    response = client.post("/conflicts/check", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["has_conflict"] is True
    assert len(data["conflicts"]) >= 1
    assert data["conflicts"][0]["code"] == "C1"


def test_validate_alias_endpoint():
    """ทดสอบ endpoint alias /validate จาก 02_api_backend"""
    payload = {
        "term": "1/2569",
        "sections": [
            {
                "id": "CPE101-01",
                "course_code": "CPE101",
                "section": "01",
                "meetings": [{"day": 0, "start_min": 540, "end_min": 720}],
            }
        ],
    }
    response = client.post("/validate", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert "conflicts" in data
    assert "summary" in data


def test_preview_endpoint():
    """ทดสอบ fast preview endpoint"""
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


def test_generate_plan_endpoint():
    """ทดสอบ generate plan endpoint"""
    payload = {
        "term": "1/2569",
        "preferences": {"avoid_morning": False},
    }
    response = client.post("/plan/generate", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["status"] in ("success", "success_relaxed_preferences")
    assert data["plans_count"] > 0


def test_repair_endpoint():
    """ทดสอบ repair endpoint"""
    payload = {
        "term": "1/2569",
        "sections": [
            {
                "id": "01000101-01",
                "course_code": "01000101",
                "section": "01",
                "meetings": [{"day": 0, "start_min": 540, "end_min": 720}],  # จันทร์ 09:00-12:00
            },
            {
                "id": "01000102-01",
                "course_code": "01000102",
                "section": "01",
                "meetings": [{"day": 0, "start_min": 600, "end_min": 780}],  # จันทร์ 10:00-13:00 (ชนกัน)
            },
        ],
        "all_available_sections": [
            {
                "id": "01000101-02",
                "course_code": "01000101",
                "section": "02",
                "meetings": [{"day": 1, "start_min": 780, "end_min": 960}],  # อังคารบ่าย (ไม่ชน)
                "seat_total": 40,
                "seat_taken": 10,
            }
        ],
    }
    response = client.post("/plan/repair", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["has_repair"] is True
    assert len(data["suggestions"]) >= 1
    assert data["suggestions"][0]["to_section"] == "01000101-02"


def test_compare_endpoint():
    """ทดสอบ compare plans endpoint"""
    payload = {
        "plan_a": [
            {
                "id": "CPE101-01",
                "course_code": "CPE101",
                "section": "01",
                "credits": 3,
                "meetings": [{"day": 0, "start_min": 540, "end_min": 720}],
            }
        ],
        "plan_b": [
            {
                "id": "CPE101-01",
                "course_code": "CPE101",
                "section": "01",
                "credits": 3,
                "meetings": [{"day": 0, "start_min": 540, "end_min": 720}],
            },
            {
                "id": "CPE102-01",
                "course_code": "CPE102",
                "section": "01",
                "credits": 3,
                "meetings": [{"day": 1, "start_min": 540, "end_min": 720}],
            },
        ],
    }
    response = client.post("/plan/compare", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["credits_a"] == 3
    assert data["credits_b"] == 6
