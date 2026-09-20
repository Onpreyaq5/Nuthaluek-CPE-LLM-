from sqlalchemy import text

from src.core.database import engine


def test_export_ics(client):
    with engine.begin() as connection:
        connection.execute(text("CREATE TABLE IF NOT EXISTS plans (id INTEGER PRIMARY KEY, name TEXT, term TEXT)"))
        connection.execute(text("CREATE TABLE IF NOT EXISTS sections (id INTEGER PRIMARY KEY, course_code TEXT, section TEXT)"))
        connection.execute(text("CREATE TABLE IF NOT EXISTS plan_items (plan_id INTEGER, section_id INTEGER)"))
        connection.execute(text("CREATE TABLE IF NOT EXISTS section_meetings (section_id INTEGER, day_of_week INTEGER, start_min INTEGER, end_min INTEGER, room TEXT, building TEXT, meeting_type TEXT)"))
        connection.execute(text("DELETE FROM section_meetings"))
        connection.execute(text("DELETE FROM plan_items"))
        connection.execute(text("DELETE FROM sections"))
        connection.execute(text("DELETE FROM plans"))
        connection.execute(text("INSERT INTO plans VALUES (1, 'แผน A', '1/2569')"))
        connection.execute(text("INSERT INTO sections VALUES (10, 'CPE301', '01')"))
        connection.execute(text("INSERT INTO plan_items VALUES (1, 10)"))
        connection.execute(text("INSERT INTO section_meetings VALUES (10, 0, 540, 720, '301', 'CPE', 'lecture')"))
    response = client.get("/export/ics/1?start_date=2026-06-01&end_date=2026-10-01")
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/calendar")
    assert b"BEGIN:VCALENDAR" in response.content
    assert b"CPE301" in response.content
