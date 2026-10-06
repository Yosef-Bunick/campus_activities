"""Create, edit, cancel and list events. Rules live in event_rules.py."""

from __future__ import annotations

from datetime import UTC, datetime, time, timedelta

from sqlmodel import Session, col, or_, select

from app.core import permissions as P
from app.models.event import Alert, Event, EventSeries, EventStatus, EventType
from app.models.place import Floor, Room
from app.models.user import User, as_utc
from app.schemas.events import CancelScope, EventCreate, EventFilter, EventUpdate
from app.services import event_rules as R
from app.services.recurrence import NY, expand, ny_date


class Conflicts(Exception):
    """Some dates break a rule. The form lists them; the user can skip them."""

    def __init__(self, conflicts: list[dict]):
        super().__init__("Some dates conflict")
        self.conflicts = conflicts


def _room(session: Session, room_id: int) -> Room:
    room = session.get(Room, room_id)
    if room is None:
        raise R.RuleError("No such room", 404)
    return room


def create(session: Session, user: User, body: EventCreate) -> list[Event]:
    R.check_type(user, body.type)
    R.check_times(body.starts_at, body.ends_at)
    room = _room(session, body.room_id)
    R.check_daily_cap(session, user)

    rep = body.repeat
    if rep is not None:
        limit = R.last_allowed_date(user)
        if rep.until > limit:
            days = P.MAX_DAYS_AHEAD[P.Role(user.role)]
            raise R.RuleError(f"A series can run at most {days} days ahead (until {limit})")
        if rep.until < ny_date(body.starts_at):
            raise R.RuleError("The repeat end date is before the first date")
    occurrences = expand(
        body.starts_at, body.ends_at, rep.freq if rep else None,
        rep.until if rep else None, rep.weekdays if rep else None,
    )  # fmt: skip
    skip = set(body.skip_dates)
    occurrences = [(s, e) for s, e in occurrences if ny_date(s) not in skip]
    if not occurrences:
        raise R.RuleError("No dates left to create")

    conflicts = []
    for s, e in occurrences:
        problem = R.occurrence_problem(session, user, room, s, e)
        if problem:
            conflicts.append({"date": ny_date(s).isoformat(), "starts_at": s, "reason": problem})
    if conflicts:
        raise Conflicts(conflicts)

    series = None
    if rep is not None:
        series = EventSeries(
            creator_id=user.id,
            freq=rep.freq.value,
            weekdays=",".join(map(str, rep.weekdays)),
            starts_on=ny_date(occurrences[0][0]),
            ends_on=rep.until,
        )
        session.add(series)
        session.flush()
    events = [
        Event(
            series_id=series.id if series else None,
            title=body.title.strip(),
            description=body.description.strip(),
            type=body.type.value,
            room_id=room.id,
            starts_at=s,
            ends_at=e,
            creator_id=user.id,
        )
        for s, e in occurrences
    ]
    session.add_all(events)
    session.commit()
    for ev in events:
        session.refresh(ev)
    return events


def _get(session: Session, event_id: int) -> Event:
    ev = session.get(Event, event_id)
    if ev is None:
        raise R.RuleError("No such event", 404)
    return ev


def update(session: Session, user: User, event_id: int, body: EventUpdate) -> Event:
    """Edit one occurrence: your own, or any with event.edit_any."""
    ev = _get(session, event_id)
    if ev.creator_id != user.id and not P.can(P.Role(user.role), "event.edit_any"):
        raise R.RuleError("You can only edit your own events", 403)
    if ev.status != EventStatus.ACTIVE.value:
        raise R.RuleError("A cancelled event can't be edited")
    if as_utc(ev.ends_at) <= datetime.now(UTC):
        raise R.RuleError("Past events can't be changed")
    starts_at = body.starts_at or as_utc(ev.starts_at)
    ends_at = body.ends_at or as_utc(ev.ends_at)
    R.check_times(starts_at, ends_at)
    room = _room(session, body.room_id or ev.room_id)
    # Rules are checked as the creator, so the owner editing doesn't lift their limits.
    creator = session.get(User, ev.creator_id)
    problem = R.occurrence_problem(session, creator, room, starts_at, ends_at, {ev.id})
    if problem:
        raise Conflicts([{"date": ny_date(starts_at).isoformat(), "starts_at": starts_at, "reason": problem}])
    for field in ("title", "description"):
        value = getattr(body, field)
        if value is not None:
            setattr(ev, field, value.strip())
    ev.room_id, ev.starts_at, ev.ends_at = room.id, starts_at, ends_at
    ev.updated_at = datetime.now(UTC)
    session.add(ev)
    session.commit()
    session.refresh(ev)
    return ev


def _cancel_rows(session: Session, actor: User, rows: list[Event], reason: str) -> int:
    now = datetime.now(UTC)
    count = 0
    for ev in rows:
        if ev.status != EventStatus.ACTIVE.value or as_utc(ev.ends_at) <= now:
            continue  # dates that already happened are never changed
        ev.status = EventStatus.CANCELLED.value
        ev.cancelled_by_id = actor.id
        ev.cancelled_reason = reason or None
        ev.updated_at = now
        session.add(ev)
        count += 1
    session.flush()
    return count


def _alert_creator(session: Session, actor: User, ev: Event, count: int, reason: str) -> None:
    """The creator gets a notice when someone else cancels their event."""
    if actor.id == ev.creator_id or count == 0:
        return
    when = as_utc(ev.starts_at).astimezone(NY).strftime("%a %b %d")
    what = f"“{ev.title}” on {when}" if count == 1 else f"{count} dates of “{ev.title}”"
    msg = f"{what} was cancelled by {actor.display_name or 'a moderator'}"
    session.add(Alert(user_id=ev.creator_id, kind="event_cancelled", event_id=ev.id,
                      message=msg + (f": {reason}" if reason else "")))  # fmt: skip


def cancel(session: Session, actor: User, event_id: int, scope: CancelScope, reason: str) -> int:
    ev = _get(session, event_id)
    if ev.creator_id != actor.id and not P.can(P.Role(actor.role), "event.cancel_any"):
        raise R.RuleError("You can only cancel your own events", 403)
    if scope != CancelScope.THIS and ev.series_id is None:
        scope = CancelScope.THIS
    if scope == CancelScope.THIS:
        rows = [ev]
    else:
        q = select(Event).where(Event.series_id == ev.series_id)
        if scope == CancelScope.FUTURE:
            q = q.where(Event.starts_at >= ev.starts_at)
        rows = list(session.exec(q))
    count = _cancel_rows(session, actor, rows, reason)
    _alert_creator(session, actor, ev, count, reason)
    session.commit()
    return count


def cancel_upcoming_for_ban(session: Session, actor: User, user_id: int) -> int:
    rows = list(
        session.exec(
            select(Event).where(
                Event.creator_id == user_id,
                Event.status == EventStatus.ACTIVE.value,
                Event.ends_at > datetime.now(UTC),
            )
        )
    )
    count = _cancel_rows(session, actor, rows, "Creator was banned")
    session.commit()
    return count


def end_of_today() -> datetime:
    tomorrow = datetime.now(NY).date() + timedelta(days=1)
    return datetime.combine(tomorrow, time(0), tzinfo=NY).astimezone(UTC)


def list_events(session: Session, f: EventFilter) -> list[Event]:
    """Feed rule (§10): active events, plus cancelled ones until they end.
    Hidden people/events are filtered in Milestone 4."""
    now = datetime.now(UTC)
    start = f.start or now
    end = f.end or end_of_today()
    if f.happening_now:
        start = end = now
        q = select(Event).where(Event.starts_at <= now, Event.ends_at > now)
    else:
        q = select(Event).where(Event.starts_at < end, Event.ends_at > start)
    q = q.where(
        or_(Event.status == EventStatus.ACTIVE.value, Event.ends_at > now),
        col(Event.type).in_([t.value for t in (f.types or list(EventType))]),
    )
    if f.room_ids:
        q = q.where(col(Event.room_id).in_(f.room_ids))
    if f.building_ids:
        q = q.join(Room, Room.id == Event.room_id).join(Floor, Floor.id == Room.floor_id).where(
            col(Floor.building_id).in_(f.building_ids)
        )
    if f.search.strip():
        like = f"%{f.search.strip()}%"
        q = q.where(or_(col(Event.title).ilike(like), col(Event.description).ilike(like)))
    return list(session.exec(q.order_by(Event.starts_at).limit(500)))
