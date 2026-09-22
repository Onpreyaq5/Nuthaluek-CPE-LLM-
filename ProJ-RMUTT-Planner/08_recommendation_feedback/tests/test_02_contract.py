import json
from pathlib import Path

from src.core.database import SessionLocal
from src.models import EventLog, FeedbackEvent, ReviewItem

HEADERS = {"X-Internal-Token": "test-token"}
FIXTURE = Path(__file__).parent / "fixtures" / "02_event_batch.json"


def test_02_real_event_shapes_are_accepted_and_analyzed(client):
    payload = json.loads(FIXTURE.read_text(encoding="utf-8"))
    response = client.post("/events/batch", json=payload, headers={"X-Request-ID": "req-from-02"})
    assert response.status_code == 202
    assert response.json()["data"] == {"accepted": 4, "duplicates": 0, "received": 4}
    with SessionLocal() as db:
        events = db.query(EventLog).order_by(EventLog.id).all()
        assert [item.action for item in events] == [
            "plan_validate", "plan_auto", "chat_message", "feedback"
        ]
        assert all(item.student_hash == "8df1309c43a1e207" for item in events)
        assert all(item.request_id == "req-from-02" for item in events)
        assert events[0].payload == {"term": "1/2569", "section_count": 2, "is_valid": False}
        assert db.query(FeedbackEvent).count() == 1
        assert db.query(ReviewItem).count() == 1
    analytics = client.get("/analytics/summary", headers=HEADERS).json()["data"]
    assert analytics["events"]["by_action"]["plan_validate"] == 1
    assert analytics["quality"]["invalid_plan_validations"] == 1
    assert analytics["quality"]["unanswered_questions"] is None
    assert analytics["feedback"]["plan_acceptance_rate"] is None


def test_retry_without_event_id_is_not_claimed_as_idempotent(client):
    payload = {"events": [{"event": "plan_auto", "id_hash": "hashed", "plan_count": 2}]}
    assert client.post("/events/batch", json=payload).json()["data"]["accepted"] == 1
    assert client.post("/events/batch", json=payload).json()["data"]["accepted"] == 1


def test_sensitive_values_are_scrubbed_recursively(client):
    response = client.post("/events/batch", json={"events": [{
        "event": "chat_message", "id_hash": "hashed",
        "payload": {
            "nested": {"authorization": "Bearer abc", "jwt": "secret", "note": "contact a@example.com"},
            "cookies": [{"access_token": "secret"}],
        },
    }]})
    assert response.status_code == 202
    with SessionLocal() as db:
        saved = db.query(EventLog).one().payload
        assert "authorization" not in saved["nested"]
        assert "jwt" not in saved["nested"]
        assert "access_token" not in saved["cookies"][0]
        assert "[EMAIL]" in saved["nested"]["note"]
