"""Request/response shapes for events, including the shared EventFilter (§11)."""

from __future__ import annotations

from datetime import date, datetime
from enum import Enum

from pydantic import BaseModel, Field, field_validator

from app.models.event import EventType, Freq


def _aware(v: datetime) -> datetime:
    if v.tzinfo is None:
        raise ValueError("datetimes must include a time zone (send UTC, e.g. ...Z)")
    return v


class Repeat(BaseModel):
    freq: Freq
    until: date  # last date (New York), inclusive
    weekdays: list[int] = Field(default_factory=list)  # 0 = Monday; weekly/biweekly

    @field_validator("weekdays")
    @classmethod
    def _days(cls, v: list[int]) -> list[int]:
        if any(d < 0 or d > 6 for d in v):
            raise ValueError("weekdays are 0 (Mon) to 6 (Sun)")
        return sorted(set(v))


class EventCreate(BaseModel):
    title: str = Field(min_length=1, max_length=120)
    description: str = Field(default="", max_length=2000)
    type: EventType
    room_id: int
    starts_at: datetime
    ends_at: datetime
    repeat: Repeat | None = None
    # Dates (New York) the user chose to skip after seeing conflicts.
    skip_dates: list[date] = Field(default_factory=list)

    _tz = field_validator("starts_at", "ends_at")(_aware)


class EventUpdate(BaseModel):
    """Edit one occurrence."""

    title: str | None = Field(default=None, min_length=1, max_length=120)
    description: str | None = Field(default=None, max_length=2000)
    room_id: int | None = None
    starts_at: datetime | None = None
    ends_at: datetime | None = None

    @field_validator("starts_at", "ends_at")
    @classmethod
    def _tz(cls, v):
        return v if v is None else _aware(v)


class CancelScope(str, Enum):
    THIS = "this"  # only this date
    FUTURE = "future"  # this and all future dates
    SERIES = "series"  # every date in the series that hasn't happened yet


class EventCancel(BaseModel):
    scope: CancelScope = CancelScope.THIS
    reason: str = Field(default="", max_length=300)


class EventFilter(BaseModel):
    types: list[EventType] = Field(default_factory=lambda: list(EventType))
    start: datetime | None = None  # default: now
    end: datetime | None = None  # default: end of today (New York)
    happening_now: bool = False
    building_ids: list[int] = Field(default_factory=list)
    room_ids: list[int] = Field(default_factory=list)
    favorites_only: bool = False  # Milestone 4
    search: str = ""
