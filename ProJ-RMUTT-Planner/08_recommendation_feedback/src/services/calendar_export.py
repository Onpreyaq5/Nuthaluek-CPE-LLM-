from __future__ import annotations

from datetime import date, datetime, time, timedelta
from zoneinfo import ZoneInfo

from icalendar import Calendar, Event
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

BANGKOK = ZoneInfo("Asia/Bangkok")
DAY_CODES = ["MO", "TU", "WE", "TH", "FR", "SA", "SU"]


class PlanNotFound(Exception):
    pass


class PlanSchemaUnavailable(Exception):
    pass


def _first_weekday(start: date, weekday: int) -> date:
    return start + timedelta(days=(weekday - start.weekday()) % 7)


def export_plan(db: Session, plan_id: int, start_date: date, end_date: date) -> bytes:
    try:
        plan = db.execute(
            text("SELECT id, name, term FROM plans WHERE id = :plan_id"), {"plan_id": plan_id}
        ).mappings().first()
        if not plan:
            raise PlanNotFound
        meetings = db.execute(
            text(
                """
                SELECT s.course_code, s.section, sm.day_of_week, sm.start_min, sm.end_min,
                       sm.room, sm.building, sm.meeting_type
                FROM plan_items pi
                JOIN sections s ON s.id = pi.section_id
                JOIN section_meetings sm ON sm.section_id = s.id
                WHERE pi.plan_id = :plan_id
                ORDER BY sm.day_of_week, sm.start_min
                """
            ),
            {"plan_id": plan_id},
        ).mappings().all()
    except SQLAlchemyError as exc:
        raise PlanSchemaUnavailable from exc

    calendar = Calendar()
    calendar.add("prodid", "-//RMUTT Study Planner//Module 08//TH")
    calendar.add("version", "2.0")
    calendar.add("x-wr-calname", str(plan["name"] or f"RMUTT Plan {plan_id}"))
    for row in meetings:
        event = Event()
        event.add("uid", f"plan-{plan_id}-{row['course_code']}-{row['section']}-{row['day_of_week']}-{row['start_min']}@rmutt-planner")
        event.add("summary", f"{row['course_code']} หมู่ {row['section']}")
        location = " ".join(filter(None, [row["building"], row["room"]]))
        if location:
            event.add("location", location)
        first = _first_weekday(start_date, int(row["day_of_week"]))
        start_dt = datetime.combine(first, time.min, BANGKOK) + timedelta(minutes=int(row["start_min"]))
        end_dt = datetime.combine(first, time.min, BANGKOK) + timedelta(minutes=int(row["end_min"]))
        event.add("dtstart", start_dt)
        event.add("dtend", end_dt)
        until = datetime.combine(end_date, time(23, 59, 59), BANGKOK)
        event.add("rrule", {"freq": "weekly", "byday": DAY_CODES[int(row["day_of_week"])], "until": until})
        calendar.add_component(event)
    return calendar.to_ical()
