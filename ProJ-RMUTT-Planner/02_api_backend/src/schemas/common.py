from __future__ import annotations

from enum import Enum
from typing import Annotated, Generic, TypeVar

from pydantic import BaseModel, Field

T = TypeVar("T")

_DAY_ORDER = ["MON", "TUE", "WED", "THU", "FRI", "SAT", "SUN"]


class Day(str, Enum):
    MON = "MON"
    TUE = "TUE"
    WED = "WED"
    THU = "THU"
    FRI = "FRI"
    SAT = "SAT"
    SUN = "SUN"


TimeStr = Annotated[
    str,
    Field(pattern=r"^([01]\d|2[0-3]):[0-5]\d$", examples=["09:00"], description='เวลารูปแบบ "HH:MM"'),
]

TermStr = Annotated[
    str,
    Field(pattern=r"^[1-3]/\d{4}$", examples=["1/2569"], description='ภาคการศึกษารูปแบบ "ภาค/ปีพ.ศ."'),
]


class Page(BaseModel, Generic[T]):
    items: list[T]
    next_cursor: str | None = None


def minutes_to_hhmm(minutes: int) -> str:
    hours, mins = divmod(minutes, 60)
    return f"{hours:02d}:{mins:02d}"


def hhmm_to_minutes(hhmm: str) -> int:
    hours, mins = hhmm.split(":")
    return int(hours) * 60 + int(mins)


def day_index_to_enum(index: int) -> Day:
    return Day(_DAY_ORDER[index % 7])


def day_enum_to_index(day: Day) -> int:
    return _DAY_ORDER.index(day.value)
