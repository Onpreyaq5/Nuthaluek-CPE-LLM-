from __future__ import annotations

from datetime import date, datetime, time, timedelta
from zoneinfo import ZoneInfo

from icalendar import Calendar, Event
from pydantic import BaseModel, Field, model_validator

BANGKOK = ZoneInfo("Asia/Bangkok")
DAY_CODES = ["MO", "TU", "WE", "TH", "FR", "SA", "SU"]


class CalendarMeeting(BaseModel):
    course_code: str = Field(min_length=1)
    section: str = Field(min_length=1)
    day_of_week: int = Field(ge=0, le=6)
    start_min: int = Field(ge=0, lt=1440)
    end_min: int = Field(gt=0, le=1440)
    room: str | None = None
    building: str | None = None

    @model_validator(mode="after")
    def check_interval(self):
        if self.start_min >= self.end_min:
            raise ValueError("meeting start_min must precede end_min")
        return self


class CalendarSnapshot(BaseModel):
    """An ownership-checked plan snapshot supplied by trusted module 02."""

    plan_id: int = Field(gt=0)
    name: str | None = None
    term: str
    start_date: date
    end_date: date
    meetings: list[CalendarMeeting]

    @model_validator(mode="after")
    def check_dates(self):
        if self.start_date > self.end_date:
            raise ValueError("start_date must be on or before end_date")
        return self


def _first_weekday(start: date, weekday: int) -> date:
    return start + timedelta(days=(weekday - start.weekday()) % 7)


def export_snapshot(snapshot: CalendarSnapshot) -> bytes:
    calendar = Calendar()
    calendar.add("prodid", "-//RMUTT Study Planner//Module 08//TH")
    calendar.add("version", "2.0")
    calendar.add("x-wr-calname", snapshot.name or f"RMUTT Plan {snapshot.plan_id}")
    for index, row in enumerate(snapshot.meetings):
        first = _first_weekday(snapshot.start_date, row.day_of_week)
        if first > snapshot.end_date:
            continue
        event = Event()
        event.add("uid", f"plan-{snapshot.plan_id}-{index}@rmutt-planner")
        event.add("summary", f"{row.course_code} หมู่ {row.section}")
        location = " ".join(filter(None, [row.building, row.room]))
        if location:
            event.add("location", location)
        start_dt = datetime.combine(first, time.min, BANGKOK) + timedelta(minutes=row.start_min)
        end_dt = datetime.combine(first, time.min, BANGKOK) + timedelta(minutes=row.end_min)
        event.add("dtstart", start_dt)
        event.add("dtend", end_dt)
        until = datetime.combine(snapshot.end_date, time(23, 59, 59), BANGKOK)
        event.add("rrule", {"freq": "weekly", "byday": DAY_CODES[row.day_of_week], "until": until})
        calendar.add_component(event)
    return calendar.to_ical()
