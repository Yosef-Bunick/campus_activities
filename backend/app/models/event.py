"""EventSeries + one Event row per occurrence (ADR-013), and Alert (architecture §10)."""

from __future__ import annotations

from datetime import date, datetime
from enum import Enum

from sqlmodel import Field, SQLModel

from app.models.user import utcnow


class EventType(str, Enum):
    MAIN = "main_event"
    CLUB = "club_event"
    FRIEND = "friend_event"


class EventStatus(str, Enum):
    ACTIVE = "active"
    CANCELLED = "cancelled"


class Freq(str, Enum):
    DAILY = "daily"
    WEEKLY = "weekly"
    BIWEEKLY = "biweekly"


class EventSeries(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    creator_id: int = Field(foreign_key="user.id", index=True, ondelete="CASCADE")
    freq: str = Field(max_length=10)  # a Freq value
    weekdays: str = Field(default="", max_length=20)  # "0,2" = Mon, Wed (Python weekday())
    starts_on: date
    ends_on: date
    created_at: datetime = Field(default_factory=utcnow)


class Event(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    series_id: int | None = Field(
        default=None, foreign_key="eventseries.id", index=True, ondelete="CASCADE"
    )
    title: str = Field(max_length=120)
    description: str = Field(default="", max_length=2000)
    type: str = Field(max_length=20)  # exactly one EventType value
    room_id: int = Field(foreign_key="room.id", index=True)
    # Majors this event is relevant to, stored ",key1,key2," so a LIKE match is exact.
    majors: str = Field(default="", max_length=200)
    starts_at: datetime = Field(index=True)  # UTC
    ends_at: datetime = Field(index=True)  # UTC
    creator_id: int = Field(foreign_key="user.id", index=True, ondelete="CASCADE")
    status: str = Field(default=EventStatus.ACTIVE.value, max_length=20)
    cancelled_by_id: int | None = Field(default=None, foreign_key="user.id")
    cancelled_reason: str | None = Field(default=None, max_length=300)
    created_at: datetime = Field(default_factory=utcnow)
    updated_at: datetime = Field(default_factory=utcnow)


class Alert(SQLModel, table=True):
    """Notices for /alerts. Milestone 2 writes them; the page arrives in Milestone 4."""

    id: int | None = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="user.id", index=True, ondelete="CASCADE")
    kind: str = Field(max_length=30)  # event_cancelled [P1]
    event_id: int | None = Field(default=None, foreign_key="event.id", ondelete="SET NULL")
    message: str = Field(max_length=500)
    read_at: datetime | None = None
    created_at: datetime = Field(default_factory=utcnow)
