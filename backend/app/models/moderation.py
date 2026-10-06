"""Phase 2 moderation (architecture §6, §10): reports, the moderation log, and
rule hits that feed the automatic abuse flags. A human always decides bans."""

from __future__ import annotations

from datetime import datetime

from sqlmodel import Field, SQLModel, UniqueConstraint

from app.models.user import utcnow


class Report(SQLModel, table=True):
    """Someone reported an event. One report per person per event."""

    __table_args__ = (UniqueConstraint("reporter_id", "event_id", name="uq_report_once"),)

    id: int | None = Field(default=None, primary_key=True)
    reporter_id: int | None = Field(default=None, foreign_key="user.id", ondelete="SET NULL")
    event_id: int = Field(foreign_key="event.id", index=True, ondelete="CASCADE")
    reason: str = Field(default="", max_length=300)
    created_at: datetime = Field(default_factory=utcnow)
    resolved_by_id: int | None = Field(default=None, foreign_key="user.id", ondelete="SET NULL")
    resolved_at: datetime | None = None


class ModerationLog(SQLModel, table=True):
    """Who did what to whom. Survives deletions: ids go null, the text stays."""

    id: int | None = Field(default=None, primary_key=True)
    actor_id: int | None = Field(default=None, foreign_key="user.id", ondelete="SET NULL")
    action: str = Field(max_length=40)  # ban, unban, change_role, cancel_event, approve, reject, …
    target_user_id: int | None = Field(default=None, foreign_key="user.id", ondelete="SET NULL")
    target_event_id: int | None = Field(default=None, foreign_key="event.id", ondelete="SET NULL")
    detail: str = Field(default="", max_length=500)  # human-readable, kept after deletions
    created_at: datetime = Field(default_factory=utcnow, index=True)


class RuleHit(SQLModel, table=True):
    """A rule stopped someone (daily cap) or sent their event to approval (room
    full). Repeated hits raise an abuse flag to managers (services/flags.py)."""

    id: int | None = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="user.id", index=True, ondelete="CASCADE")
    kind: str = Field(max_length=20)  # daily_cap | room_full
    created_at: datetime = Field(default_factory=utcnow, index=True)
