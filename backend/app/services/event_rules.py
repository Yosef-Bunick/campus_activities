"""Event rules (architecture §6), checked on the server for every create and edit,
including each occurrence of a recurring event. All limits come from permissions.py."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from sqlmodel import Session, func, select

from app.core import permissions as P
from app.models.event import Event, EventSeries, EventStatus, EventType
from app.models.place import Room
from app.models.user import User
from app.services.recurrence import ny_date

MAX_LENGTH = timedelta(hours=12)

CREATE_PERM = {
    EventType.MAIN: "event.create.main",
    EventType.CLUB: "event.create.club",
    EventType.FRIEND: "event.create.friend",
}


class RuleError(Exception):
    """A rule that blocks the whole request (not just some dates)."""

    def __init__(self, message: str, status: int = 400):
        super().__init__(message)
        self.message, self.status = message, status


def check_type(user: User, event_type: EventType) -> None:
    # Rule 1: exactly one type, and your role must be allowed to create it.
    if not P.can(P.Role(user.role), CREATE_PERM[event_type]):
        raise RuleError(f"Your role can't create a {event_type.value}", 403)


def check_times(starts_at: datetime, ends_at: datetime) -> None:
    # Rule 6.
    if ends_at <= starts_at:
        raise RuleError("An event must end after it starts")
    if ends_at - starts_at > MAX_LENGTH:
        raise RuleError("An event can be at most 12 hours long. Use a repeat instead")


def check_daily_cap(session: Session, user: User) -> None:
    # Rule 5: one-off events + series created in the last 24 hours.
    cap = P.MAX_EVENTS_CREATED_PER_DAY.get(P.Role(user.role))
    if cap is None:
        return
    since = datetime.now(UTC) - timedelta(days=1)
    singles = session.exec(
        select(func.count()).select_from(Event).where(
            Event.creator_id == user.id, Event.series_id.is_(None), Event.created_at >= since
        )
    ).one()
    series = session.exec(
        select(func.count()).select_from(EventSeries).where(
            EventSeries.creator_id == user.id, EventSeries.created_at >= since
        )
    ).one()
    if singles + series >= cap:
        raise RuleError(f"You can create at most {cap} events a day", 429)


def last_allowed_date(user: User):
    """Rule 2: how far ahead (New York date) this role may schedule."""
    return ny_date(datetime.now(UTC)) + timedelta(days=P.MAX_DAYS_AHEAD[P.Role(user.role)])


def _overlapping(start: datetime, end: datetime, exclude_ids: set[int]):
    q = select(Event).where(
        Event.status == EventStatus.ACTIVE.value, Event.starts_at < end, Event.ends_at > start
    )
    if exclude_ids:
        q = q.where(Event.id.not_in(exclude_ids))
    return q


def occurrence_problem(
    session: Session,
    user: User,
    room: Room,
    start: datetime,
    end: datetime,
    exclude_ids: set[int] = frozenset(),
) -> str | None:
    """Why this one occurrence can't happen, or None if it can."""
    if end <= datetime.now(UTC):
        return "Already over"
    if ny_date(start) > last_allowed_date(user):
        days = P.MAX_DAYS_AHEAD[P.Role(user.role)]
        return f"More than {days} days ahead"
    # Rule 3: no double-booking yourself (students, security).
    if P.Role(user.role) not in P.CAN_DOUBLE_BOOK_SELF:
        mine = session.exec(
            _overlapping(start, end, exclude_ids).where(Event.creator_id == user.id)
        ).first()
        if mine is not None:
            return f"You already have “{mine.title}” then"
    # Rule 4: room limit. P1 blocks the 3rd; P2 turns it into an approval request.
    limit = room.max_overlapping or P.ROOM_MAX_OVERLAPPING
    in_room = session.exec(
        select(func.count()).select_from(
            _overlapping(start, end, exclude_ids).where(Event.room_id == room.id).subquery()
        )
    ).one()
    if in_room >= limit:
        return "Room is full at that time"
    return None
