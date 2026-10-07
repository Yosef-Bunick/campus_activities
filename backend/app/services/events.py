"""Create, edit, cancel and list events. Rules live in event_rules.py."""

from __future__ import annotations

from datetime import UTC, datetime, time, timedelta

from sqlmodel import Session, col, or_, select

from app.core import permissions as P
from app.models.event import Alert, Event, EventSeries, EventStatus, EventType, Freq, LocationKind
from app.models.place import Floor, Room
from app.models.user import User, as_utc
from app.schemas.events import CancelScope, EventCreate, EventFilter, EventUpdate, check_place
from app.services import event_rules as R
from app.services import moderation as M
from app.services.recurrence import NY, expand, ny_date


class Conflicts(Exception):
    """Some dates break a rule. The form lists them; the user can skip them."""

    def __init__(self, conflicts: list[dict]):
        super().__init__("Some dates conflict")
        self.conflicts = conflicts


def pack_majors(majors: list[str]) -> str:
    return f",{','.join(majors)}," if majors else ""


def _room(session: Session, room_id: int) -> Room:
    room = session.get(Room, room_id)
    if room is None:
        raise R.RuleError("No such room", 404)
    return room


def _place(session: Session, kind: str, room_id, location: str, online_url: str):
    """(Room or None, the place fields to store). Only campus events have a room."""
    try:
        check_place(LocationKind(kind), room_id, location, online_url)
    except ValueError as e:
        raise R.RuleError(str(e)) from None
    campus = kind == LocationKind.CAMPUS.value
    room = _room(session, room_id) if campus else None
    return room, {
        "location_kind": kind,
        "room_id": room.id if room else None,
        "location": "" if campus or kind == LocationKind.ONLINE.value else location.strip(),
        "online_url": online_url.strip() if kind == LocationKind.ONLINE.value else "",
    }


def create(session: Session, user: User, body: EventCreate) -> list[Event]:
    R.check_type(user, body.type)
    R.check_times(body.starts_at, body.ends_at)
    room, place = _place(
        session, body.location_kind.value, body.room_id, body.location, body.online_url
    )
    try:
        R.check_daily_cap(session, user)
    except R.RuleError:
        M.record_hit(session, user, "daily_cap")
        session.commit()
        raise

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

    check_dates(session, user, room, occurrences)

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
    template = {
        "title": body.title.strip(), "description": body.description.strip(),
        "type": body.type.value, "majors": pack_majors(body.majors), **place,
    }  # fmt: skip
    return save_dates(session, user, room, occurrences, template, series)


def check_dates(session: Session, user: User, room: Room | None, occurrences) -> set:
    """Every date must pass the rules. A full room isn't a conflict any more
    (Phase 2): those dates go to SGA/owner approval. Returns their start times."""
    conflicts, pending = [], set()
    for s, e in occurrences:
        problem = R.occurrence_problem(session, user, room, s, e)
        if problem == R.ROOM_FULL:
            pending.add(s)
        elif problem:
            conflicts.append({"date": ny_date(s).isoformat(), "starts_at": s, "reason": problem})
    if conflicts:
        raise Conflicts(conflicts)
    return pending


def save_dates(
    session: Session, user: User, room: Room | None, occurrences, template: dict,
    series: EventSeries | None,
) -> list[Event]:  # fmt: skip
    pending = check_dates(session, user, room, occurrences)
    events = [
        Event(
            series_id=series.id if series else None, starts_at=s, ends_at=e,
            creator_id=user.id, **template,
            status=EventStatus.PENDING.value if s in pending else EventStatus.ACTIVE.value,
        )  # fmt: skip
        for s, e in occurrences
    ]
    session.add_all(events)
    session.flush()
    if pending and room is not None:
        first = next(ev for ev in events if ev.status == EventStatus.PENDING.value)
        days = sorted({ny_date(s) for s in pending})
        when = ", ".join(d.strftime("%a %b %d") for d in days[:5])
        more = f" (+{len(days) - 5} more)" if len(days) > 5 else ""
        M.notify(
            session, "event.approve_overlap", "approval_needed",
            f"{M.name(user)} wants “{template['title']}” in Room {room.name} on {when}{more}, "
            f"while {room.max_overlapping or P.ROOM_MAX_OVERLAPPING} other events are there. "
            "Approve or reject?",
            event_id=first.id, subject_user_id=user.id,
        )  # fmt: skip
        M.record_hit(session, user, "room_full")
    session.commit()
    for ev in events:
        session.refresh(ev)
    return events


def extend_series(
    session: Session, user: User, series_id: int, until=None, skip_dates=(),
) -> list[Event]:  # fmt: skip
    """Add dates to a series, up to the creator's schedule-ahead limit (Phase 2).
    Same rules as creating; conflicting dates can be skipped."""
    series = session.get(EventSeries, series_id)
    if series is None:
        raise R.RuleError("No such series", 404)
    if series.creator_id != user.id and not P.can(P.Role(user.role), "event.edit_any"):
        raise R.RuleError("You can only extend your own series", 403)
    creator = session.get(User, series.creator_id)
    rows = list(session.exec(
        select(Event).where(Event.series_id == series_id).order_by(Event.starts_at)
    ))  # fmt: skip
    if not rows:
        raise R.RuleError("This series has no dates")
    first, last = rows[0], rows[-1]
    limit = R.last_allowed_date(creator)
    until = until or limit
    if until > limit:
        raise R.RuleError(f"A series can run at most until {limit}")
    last_day = ny_date(as_utc(last.starts_at))
    if until <= last_day:
        raise R.RuleError(f"This series already runs until {last_day}")
    weekdays = [int(d) for d in series.weekdays.split(",") if d]
    skip = set(skip_dates)
    occurrences = [
        (s, e)
        for s, e in expand(as_utc(first.starts_at), as_utc(first.ends_at), Freq(series.freq), until, weekdays)
        if ny_date(s) > last_day and ny_date(s) not in skip
    ]
    if not occurrences:
        raise R.RuleError("No new dates to add")
    template = {
        "title": last.title, "description": last.description, "type": last.type,
        "majors": last.majors, "location_kind": last.location_kind, "room_id": last.room_id,
        "location": last.location, "online_url": last.online_url,
    }  # fmt: skip
    room = _room(session, last.room_id) if last.room_id else None
    events = save_dates(session, creator, room, occurrences, template, series)
    series.ends_on = until
    session.add(series)
    session.commit()
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
    kind = body.location_kind.value if body.location_kind else ev.location_kind
    room, place = _place(
        session, kind,
        body.room_id if body.room_id is not None else ev.room_id,
        body.location if body.location is not None else ev.location,
        body.online_url if body.online_url is not None else ev.online_url,
    )  # fmt: skip
    # Rules are checked as the creator, so the owner editing doesn't lift their limits.
    creator = session.get(User, ev.creator_id)
    problem = R.occurrence_problem(session, creator, room, starts_at, ends_at, {ev.id})
    if problem:
        raise Conflicts([{"date": ny_date(starts_at).isoformat(), "starts_at": starts_at, "reason": problem}])
    for field in ("title", "description"):
        value = getattr(body, field)
        if value is not None:
            setattr(ev, field, value.strip())
    if body.majors is not None:
        ev.majors = pack_majors(body.majors)
    for k, v in place.items():
        setattr(ev, k, v)
    ev.starts_at, ev.ends_at = starts_at, ends_at
    ev.updated_at = datetime.now(UTC)
    session.add(ev)
    session.commit()
    session.refresh(ev)
    return ev


def _cancel_rows(session: Session, actor: User, rows: list[Event], reason: str) -> int:
    now = datetime.now(UTC)
    cancelled = []
    for ev in rows:
        live = (EventStatus.ACTIVE.value, EventStatus.PENDING.value)
        if ev.status not in live or as_utc(ev.ends_at) <= now:
            continue  # dates that already happened are never changed
        ev.status = EventStatus.CANCELLED.value
        ev.cancelled_by_id = actor.id
        ev.cancelled_reason = reason or None
        ev.updated_at = now
        session.add(ev)
        cancelled.append(ev)
    session.flush()
    _alert_going(session, actor, cancelled, reason)
    return len(cancelled)


def _alert_going(session: Session, actor: User, cancelled: list[Event], reason: str) -> None:
    """Everyone who said Going hears about a cancellation: one alert per person
    per cancel, however many dates it covers (ADR-035). The person cancelling
    and the creator (alerted separately) are skipped."""
    from app.models.social import Rsvp

    if not cancelled:
        return
    by_id = {ev.id: ev for ev in cancelled}
    who: dict[int, list[Event]] = {}
    for r in session.exec(select(Rsvp).where(col(Rsvp.event_id).in_(list(by_id)))):
        ev = by_id[r.event_id]
        if r.user_id not in (actor.id, ev.creator_id):
            who.setdefault(r.user_id, []).append(ev)
    for user_id, evs in who.items():
        first = min(evs, key=lambda e: e.starts_at)
        when = as_utc(first.starts_at).astimezone(NY).strftime("%a %b %d")
        what = f"“{first.title}” on {when}" if len(evs) == 1 else f"{len(evs)} dates of “{first.title}”"
        session.add(Alert(
            user_id=user_id, kind="event_cancelled", event_id=first.id,
            message=f"{what}, which you're going to, was cancelled" + (f": {reason}" if reason else ""),
        ))  # fmt: skip


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
    if count and actor.id != ev.creator_id:
        creator = session.get(User, ev.creator_id)
        M.log(session, actor, "cancel_event",
              f"Cancelled {count} date(s) of “{ev.title}” by {M.name(creator)}"
              + (f": {reason}" if reason else ""), target_user=creator, target_event=ev)  # fmt: skip
    session.commit()
    return count


def decide(session: Session, actor: User, event_id: int, approve: bool, reason: str = "") -> int:
    """SGA/owner approve or reject a pending event (and the rest of its series'
    pending dates). The creator gets an alert either way."""
    if not P.can(P.Role(actor.role), "event.approve_overlap"):
        raise R.RuleError("You can't approve room overlaps", 403)
    ev = _get(session, event_id)
    if ev.status != EventStatus.PENDING.value:
        raise R.RuleError("This event isn't waiting for approval", 409)
    q = select(Event).where(Event.status == EventStatus.PENDING.value)
    q = q.where(Event.series_id == ev.series_id) if ev.series_id else q.where(Event.id == ev.id)
    rows = list(session.exec(q))
    new = EventStatus.ACTIVE.value if approve else EventStatus.REJECTED.value
    for row in rows:
        row.status = new
        row.updated_at = datetime.now(UTC)
        session.add(row)
    verb = "approved" if approve else "rejected"
    what = f"“{ev.title}”" + (f" ({len(rows)} dates)" if len(rows) > 1 else "")
    session.add(Alert(
        user_id=ev.creator_id, kind=f"event_{verb}", event_id=ev.id,
        message=f"{what} was {verb} by {M.name(actor)}" + (f": {reason}" if reason else ""),
    ))  # fmt: skip
    M.log(session, actor, "approve" if approve else "reject", f"{verb.capitalize()} {what}",
          target_user=session.get(User, ev.creator_id), target_event=ev)  # fmt: skip
    session.commit()
    return len(rows)


def cancel_upcoming_for_ban(session: Session, actor: User, user_id: int) -> int:
    rows = list(
        session.exec(
            select(Event).where(
                Event.creator_id == user_id,
                col(Event.status).in_([EventStatus.ACTIVE.value, EventStatus.PENDING.value]),
                Event.ends_at > datetime.now(UTC),
            )
        )
    )
    # Neutral wording: people going are told it was cancelled, not why (privacy).
    count = _cancel_rows(session, actor, rows, "Cancelled by moderators")
    session.commit()
    return count


def end_of_today() -> datetime:
    tomorrow = datetime.now(NY).date() + timedelta(days=1)
    return datetime.combine(tomorrow, time(0), tzinfo=NY).astimezone(UTC)


def exclude_hidden(q, viewer_id: int):
    """Feed rule (§10): leave out events from people and events/series this
    viewer has hidden."""
    from app.models.social import HiddenEvent, UserHidden

    people = select(UserHidden.hidden_user_id).where(UserHidden.user_id == viewer_id)
    events = select(HiddenEvent.event_id).where(
        HiddenEvent.user_id == viewer_id, HiddenEvent.event_id.is_not(None)
    )
    series = select(HiddenEvent.series_id).where(
        HiddenEvent.user_id == viewer_id, HiddenEvent.series_id.is_not(None)
    )
    return q.where(
        col(Event.creator_id).not_in(people),
        col(Event.id).not_in(events),
        or_(Event.series_id.is_(None), col(Event.series_id).not_in(series)),
    )


def list_events(session: Session, f: EventFilter) -> list[Event]:
    """Feed rule (§10): active events, plus cancelled ones until they end,
    minus anything the viewer has hidden."""
    now = datetime.now(UTC)
    start = f.start or now
    end = f.end or end_of_today()
    if f.happening_now:
        start = end = now
        q = select(Event).where(Event.starts_at <= now, Event.ends_at > now)
    else:
        q = select(Event).where(Event.starts_at < end, Event.ends_at > start)
    visible = [
        Event.status == EventStatus.ACTIVE.value,
        (Event.status == EventStatus.CANCELLED.value) & (Event.ends_at > now),
    ]
    if f.viewer_id is not None:  # your own events waiting for approval
        visible.append((Event.status == EventStatus.PENDING.value) & (Event.creator_id == f.viewer_id))
    q = q.where(or_(*visible), col(Event.type).in_([t.value for t in (f.types or list(EventType))]))
    if f.viewer_id is not None:
        q = exclude_hidden(q, f.viewer_id)
    if f.where and len(f.where) < len(LocationKind):
        q = q.where(col(Event.location_kind).in_([w.value for w in f.where]))
    if f.room_ids:
        q = q.where(col(Event.room_id).in_(f.room_ids))
    if f.recommended_for is not None:
        rec = [Event.type == EventType.MAIN.value]
        if f.recommended_for:
            rec.append(col(Event.majors).like(f"%,{f.recommended_for},%"))
        q = q.where(or_(*rec))
    if f.building_ids:
        q = q.join(Room, Room.id == Event.room_id).join(Floor, Floor.id == Room.floor_id).where(
            col(Floor.building_id).in_(f.building_ids)
        )
    if f.search.strip():
        like = f"%{f.search.strip()}%"
        q = q.where(or_(col(Event.title).ilike(like), col(Event.description).ilike(like)))
    return list(session.exec(q.order_by(Event.starts_at).limit(500)))
