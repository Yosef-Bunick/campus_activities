"""Request/response shapes for events, including the shared EventFilter (§11)."""

from __future__ import annotations

from datetime import date, datetime
from enum import Enum

from urllib.parse import urlsplit

from pydantic import BaseModel, Field, field_validator, model_validator

from app.core.majors import MAX_EVENT_MAJORS, is_major
from app.models.event import EventType, Freq, LocationKind


def _majors(v: list[str] | None) -> list[str] | None:
    if v is None:
        return v
    v = sorted(set(v))
    if len(v) > MAX_EVENT_MAJORS or not all(is_major(m) for m in v):
        raise ValueError(f"pick up to {MAX_EVENT_MAJORS} majors from the list")
    return v


def check_place(kind: LocationKind, room_id: int | None, location: str, online_url: str) -> None:
    """Exactly what each kind of place needs (ADR-032)."""
    if kind == LocationKind.CAMPUS and not room_id:
        raise ValueError("Pick a room for an on-campus event")
    if kind == LocationKind.OFF_CAMPUS and not location.strip():
        raise ValueError("Say where the off-campus event is")
    if kind == LocationKind.ONLINE:
        parts = urlsplit(online_url.strip())
        if parts.scheme not in ("https", "http") or not parts.netloc:
            raise ValueError("Online events need a link starting with https://")


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
    location_kind: LocationKind = LocationKind.CAMPUS
    room_id: int | None = None
    location: str = Field(default="", max_length=200)
    online_url: str = Field(default="", max_length=500)
    starts_at: datetime
    ends_at: datetime
    majors: list[str] = Field(default_factory=list)  # relevant majors (Recommended)
    repeat: Repeat | None = None
    # Dates (New York) the user chose to skip after seeing conflicts.
    skip_dates: list[date] = Field(default_factory=list)

    _tz = field_validator("starts_at", "ends_at")(_aware)
    _mj = field_validator("majors")(_majors)

    @model_validator(mode="after")
    def _place(self):
        check_place(self.location_kind, self.room_id, self.location, self.online_url)
        return self


class EventUpdate(BaseModel):
    """Edit one occurrence."""

    title: str | None = Field(default=None, min_length=1, max_length=120)
    description: str | None = Field(default=None, max_length=2000)
    location_kind: LocationKind | None = None
    room_id: int | None = None
    location: str | None = Field(default=None, max_length=200)
    online_url: str | None = Field(default=None, max_length=500)
    starts_at: datetime | None = None
    ends_at: datetime | None = None
    majors: list[str] | None = None

    _mj = field_validator("majors")(_majors)

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
    where: list[LocationKind] = Field(default_factory=lambda: list(LocationKind))
    start: datetime | None = None  # default: now
    end: datetime | None = None  # default: end of today (New York)
    happening_now: bool = False
    building_ids: list[int] = Field(default_factory=list)
    room_ids: list[int] = Field(default_factory=list)
    favorites_only: bool = False  # Milestone 4
    # Recommended (ADR-028): main events, or events tagged with this major.
    recommended_for: str | None = None
    # Feed rule: drop events from people / events / series this user has hidden.
    viewer_id: int | None = None
    search: str = ""
