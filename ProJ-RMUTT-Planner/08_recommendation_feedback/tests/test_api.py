from datetime import date, timedelta

from src.core.database import SessionLocal
from src.models import EventLog, FeedbackEvent, ReviewItem

HEADERS = {"X-Internal-Token": "test-token"}


def test_health_and_ready(client):
    assert client.get("/health").status_code == 200
    assert client.get("/ready").json()["database"] == "ready"


def test_event_batch_is_idempotent_and_scrubs_pii(client):
    payload = {
        "events": [
            {
                "event_id": "evt-1",
                "request_id": "req-1",
                "student_hash": "ab12cd34ef56",
                "service": "02",
                "action": "plan.validate",
                "latency_ms": 120,
                "payload": {"note": "ติดต่อ 0812345678 หรือ test@example.com", "student_id": "6500000000"},
            }
        ]
    }
    first = client.post("/events/batch", json=payload)
    second = client.post("/events/batch", json=payload)
    assert first.status_code == 202
    assert first.json()["data"]["accepted"] == 1
    assert second.json()["data"]["duplicates"] == 1
    with SessionLocal() as db:
        event = db.query(EventLog).one()
        assert "student_id" not in event.payload
        assert "[PHONE]" in event.payload["note"]
        assert "[EMAIL]" in event.payload["note"]


def test_raw_student_id_is_rejected(client):
    response = client.post(
        "/events",
        json={"student_hash": "6500000000", "service": "02", "action": "test"},
    )
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "VALIDATION_422"


def test_feedback_creates_review_and_analytics(client):
    response = client.post(
        "/feedback",
        json={
            "source_feedback_id": "fb-1",
            "student_hash": "hash-abc",
            "target_type": "chat_message",
            "target_id": "99",
            "rating": 2,
            "reason": "หาเอกสารไม่เจอ",
        },
    )
    assert response.status_code == 201
    assert response.json()["data"]["review_queued"] is True
    duplicate = client.post("/feedback", json={
        "source_feedback_id": "fb-1", "target_type": "chat_message", "target_id": "99", "rating": 2
    })
    assert duplicate.json()["data"]["duplicate"] is True
    with SessionLocal() as db:
        assert db.query(FeedbackEvent).count() == 1
        assert db.query(ReviewItem).count() == 1
    analytics = client.get("/analytics/summary", headers=HEADERS)
    assert analytics.status_code == 200
    assert analytics.json()["data"]["feedback"]["negative_count"] == 1


def test_gateway_feedback_event_is_promoted_to_feedback(client):
    response = client.post(
        "/events/batch",
        json={"events": [{
            "event": "feedback",
            "id_hash": "hash-gateway",
            "service": "02",
            "target_type": "plan",
            "target_id": "12",
            "rating": 5,
        }]},
    )
    assert response.status_code == 202
    with SessionLocal() as db:
        assert db.query(FeedbackEvent).count() == 1


def test_recommendation_composer_keeps_structured_results(client):
    response = client.post(
        "/recommendations/compose",
        json={"candidates": [{
            "plan_id": "1",
            "name": "แผน A",
            "term": "1/2569",
            "sections": [{"section_id": "CPE301-01", "course_code": "CPE301", "credits": 3}],
            "summary": {"total_credits": 18, "advantages": ["ว่างวันศุกร์"]},
            "rule_reasons": [{"rule": "P1", "message": "วิชาบังคับ"}],
            "risks": ["ที่นั่งเหลือน้อย"],
            "explanation": "จัดตามความชอบของผู้ใช้",
        }]},
    )
    body = response.json()["data"]
    assert body["recommendations"][0]["summary"]["total_credits"] == 18
    assert "ไม่ใช่การยืนยันจากมหาวิทยาลัย" in body["disclaimer"]


def test_alerts_cover_a1_to_a5_and_are_deduplicated(client):
    today = date.today()
    payload = {
        "student_hash": "hash-alert",
        "as_of": today.isoformat(),
        "academic_events": [
            {"event_type": "registration", "event_date": (today + timedelta(days=3)).isoformat()},
            {"event_type": "withdraw", "event_date": (today + timedelta(days=5)).isoformat()},
        ],
        "planned_sections": [
            {"section_id": "A-01", "course_code": "A", "seats_remaining": 2},
            {"section_id": "B-01", "course_code": "B", "schedule_changed": True},
        ],
        "planned_credits": 6,
        "min_credits": 9,
    }
    first = client.post("/alerts/evaluate", json=payload, headers=HEADERS)
    second = client.post("/alerts/evaluate", json=payload, headers=HEADERS)
    assert {item["code"] for item in first.json()["data"]["notifications"]} == {"A1", "A2", "A3", "A4", "A5"}
    assert second.json()["data"]["created"] == 0


def test_internal_endpoints_require_token(client):
    assert client.get("/analytics/summary").status_code == 401
    assert client.get("/analytics/summary", headers=HEADERS).status_code == 200


def test_privacy_deletion(client):
    client.post("/events", json={"student_hash": "hash-delete", "service": "02", "action": "test"})
    response = client.delete("/privacy/students/hash-delete", headers=HEADERS)
    assert response.json()["data"]["deleted"]["events"] == 1
