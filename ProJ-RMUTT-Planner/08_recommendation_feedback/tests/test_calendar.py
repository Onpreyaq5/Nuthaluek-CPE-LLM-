def test_export_ics(client):
    response = client.post(
        "/export/ics",
        headers={"X-Internal-Token": "test-token"},
        json={
            "plan_id": 1,
            "name": "แผน A",
            "term": "1/2569",
            "start_date": "2026-06-01",
            "end_date": "2026-10-01",
            "meetings": [{
                "course_code": "CPE301", "section": "01", "day_of_week": 0,
                "start_min": 540, "end_min": 720, "room": "301", "building": "CPE"
            }],
        },
    )
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/calendar")
    assert b"BEGIN:VCALENDAR" in response.content
    assert b"CPE301" in response.content


def test_export_cannot_read_another_module_plan_without_ownership_check(client):
    response = client.get("/export/ics/1?start_date=2026-06-01&end_date=2026-10-01")
    assert response.status_code == 503
    assert response.json()["error"]["code"] == "PLAN_EXPORT_NOT_CONNECTED"


def test_calendar_snapshot_requires_internal_token(client):
    response = client.post("/export/ics", json={})
    assert response.status_code == 401
