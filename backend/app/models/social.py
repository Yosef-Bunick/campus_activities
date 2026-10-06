"""Favorites (saved events, favorite people; ADR-025) and Hidden (hidden people/events)."""

from __future__ import annotations

from datetime import datetime

from sqlmodel import Field, SQLModel, UniqueConstraint

from app.models.user import utcnow


class UserFavorite(SQLModel, table=True):
    """Follow a person: all their events show on /favorites."""

    user_id: int = Field(foreign_key="user.id", primary_key=True, ondelete="CASCADE")
    favorite_user_id: int = Field(foreign_key="user.id", primary_key=True, ondelete="CASCADE")
    created_at: datetime = Field(default_factory=utcnow)


class SavedEvent(SQLModel, table=True):
    """★ one event, or every date of a series (exactly one of the two ids)."""

    __table_args__ = (
        UniqueConstraint("user_id", "event_id", name="uq_saved_event"),
        UniqueConstraint("user_id", "series_id", name="uq_saved_series"),
    )

    id: int | None = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="user.id", index=True, ondelete="CASCADE")
    event_id: int | None = Field(default=None, foreign_key="event.id", ondelete="CASCADE")
    series_id: int | None = Field(default=None, foreign_key="eventseries.id", ondelete="CASCADE")
    created_at: datetime = Field(default_factory=utcnow)


class UserHidden(SQLModel, table=True):
    """Hide a person: none of their events show in your feeds (/hidden to undo)."""

    user_id: int = Field(foreign_key="user.id", primary_key=True, ondelete="CASCADE")
    hidden_user_id: int = Field(foreign_key="user.id", primary_key=True, ondelete="CASCADE")
    created_at: datetime = Field(default_factory=utcnow)


class HiddenEvent(SQLModel, table=True):
    """Hide one event, or every date of a series (exactly one of the two ids)."""

    __table_args__ = (
        UniqueConstraint("user_id", "event_id", name="uq_hidden_event"),
        UniqueConstraint("user_id", "series_id", name="uq_hidden_series"),
    )

    id: int | None = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="user.id", index=True, ondelete="CASCADE")
    event_id: int | None = Field(default=None, foreign_key="event.id", ondelete="CASCADE")
    series_id: int | None = Field(default=None, foreign_key="eventseries.id", ondelete="CASCADE")
    created_at: datetime = Field(default_factory=utcnow)
