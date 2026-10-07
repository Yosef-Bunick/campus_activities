from datetime import date, datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import JSONResponse
from fastapi.encoders import jsonable_encoder
from sqlmodel import Session, col, select

from app.core.auth import current_user, require
from app.core.database import get_session
from app.models.event import Event, EventSeries, EventType, LocationKind
from app.models.place import Building, Floor, Room
from app.models.user import User, as_utc
from pydantic import BaseModel, Field

from app.schemas.events import EventCancel, EventCreate, EventFilter, EventUpdate
from app.services import moderation as M
from app.services import events as svc
from app.services.event_rules import RuleError

router = APIRouter(tags=["events"])


def _rule_errors(fn):
    """Turn rule failures into HTTP responses the form can show."""
    try:
        return fn()
    except svc.Conflicts as c:
        return JSONResponse(
            status_code=409,
            content=jsonable_encoder({"detail": "Some dates conflict", "conflicts": c.conflicts}),
        )
    except RuleError as e:
        raise HTTPException(e.status, e.message) from None


def rooms_out(session: Session, ids: set[int] | None = None) -> dict[int, dict]:
    """Rooms with their floor and building; only `ids` if given."""
    q = (
        select(Room, Floor, Building)
        .join(Floor, Floor.id == Room.floor_id, isouter=True)
        .join(Building, Building.id == Floor.building_id, isouter=True)
    )
    if ids is not None:
        q = q.where(col(Room.id).in_(ids))
    rows = session.exec(q).all()
    return {
        r.id: {
            "id": r.id,
            "name": r.name,
            "floor": f.level if f else None,
            "building_id": b.id if b else None,
            "building": b.name if b else None,
            "is_outdoor": r.is_outdoor,
            "max_overlapping": r.max_overlapping,
            "map_x": r.map_x,
            "map_y": r.map_y,
        }
        for r, f, b in rows
    }


def _saved_by(session: Session, viewer: User | None) -> tuple[set[int], set[int]]:
    from app.models.social import SavedEvent

    if viewer is None:
        return set(), set()
    rows = session.exec(
        select(SavedEvent.event_id, SavedEvent.series_id).where(SavedEvent.user_id == viewer.id)
    ).all()
    return {e for e, _ in rows if e}, {s for _, s in rows if s}


def events_out(session: Session, events: list[Event], viewer: User | None = None) -> list[dict]:
    # A fixed number of queries per call (no N+1), each limited to what these
    # events refer to, so a long feed costs the same round trips as a short one.
    if not events:
        return []
    room_ids = {e.room_id for e in events if e.room_id}
    rooms = rooms_out(session, room_ids) if room_ids else {}
    saved_events, saved_series = _saved_by(session, viewer)
    sids = {e.series_id for e in events if e.series_id}
    series_end = dict(
        session.exec(select(EventSeries.id, EventSeries.ends_on).where(col(EventSeries.id).in_(sids))).all()
    ) if sids else {}  # fmt: skip
    ids = {e.creator_id for e in events}
    names = dict(session.exec(select(User.id, User.display_name).where(col(User.id).in_(ids))).all())
    return [
        {
            "id": e.id,
            "series_id": e.series_id,
            "series_ends_on": series_end.get(e.series_id),  # for "Extend series"
            "title": e.title,
            "description": e.description,
            "type": e.type,
            "status": e.status,
            "starts_at": as_utc(e.starts_at),
            "ends_at": as_utc(e.ends_at),
            "location_kind": e.location_kind,
            "room": rooms.get(e.room_id) if e.room_id else None,
            "location": e.location,
            "online_url": e.online_url,
            "creator": {"id": e.creator_id, "display_name": names[e.creator_id]}
            if e.creator_id in names
            else None,
            "cancelled_reason": e.cancelled_reason,
            "majors": [m for m in e.majors.split(",") if m],
            # Saved state for the viewer: "series" (every date), "event" (this date) or None.
            "saved": "series" if e.series_id in saved_series
            else "event" if e.id in saved_events
            else None,
        }
        for e in events
    ]


@router.get("/rooms")
def list_rooms(_: User = Depends(current_user), session: Session = Depends(get_session)):
    return sorted(rooms_out(session).values(), key=lambda r: (r["building"] or "", r["name"]))


@router.get("/events")
def list_events(
    types: list[EventType] = Query(default=list(EventType)),
    where: list[LocationKind] = Query(default=list(LocationKind)),
    start: datetime | None = None,
    end: datetime | None = None,
    happening_now: bool = False,
    building_ids: list[int] = Query(default=[]),
    room_ids: list[int] = Query(default=[]),
    search: str = "",
    recommended: bool = False,
    me: User = Depends(require("event.view")),
    session: Session = Depends(get_session),
):
    """Used by Home, Calendar and Map — one shared filter."""
    f = EventFilter(
        types=types, where=where, start=start, end=end, happening_now=happening_now,
        building_ids=building_ids, room_ids=room_ids, search=search,
        recommended_for=(me.major or "") if recommended else None,
        viewer_id=me.id,
    )  # fmt: skip
    return events_out(session, svc.list_events(session, f), me)


@router.post("/events", status_code=201)
def create_event(
    body: EventCreate,
    user: User = Depends(current_user),
    session: Session = Depends(get_session),
):
    def run():
        return events_out(session, svc.create(session, user, body), user)

    return _rule_errors(run)


@router.patch("/events/{event_id}")
def update_event(
    event_id: int,
    body: EventUpdate,
    user: User = Depends(current_user),
    session: Session = Depends(get_session),
):
    return _rule_errors(
        lambda: events_out(session, [svc.update(session, user, event_id, body)], user)[0]
    )


class Reason(BaseModel):
    reason: str = Field(default="", max_length=300)


@router.post("/events/{event_id}/approve")
def approve_event(
    event_id: int, body: Reason, user: User = Depends(current_user),
    session: Session = Depends(get_session),
):  # fmt: skip
    """SGA/owner: let a 3rd overlapping event (and its series' pending dates) go ahead."""
    return _rule_errors(lambda: {"updated": svc.decide(session, user, event_id, True, body.reason)})


@router.post("/events/{event_id}/reject")
def reject_event(
    event_id: int, body: Reason, user: User = Depends(current_user),
    session: Session = Depends(get_session),
):  # fmt: skip
    return _rule_errors(lambda: {"updated": svc.decide(session, user, event_id, False, body.reason)})


@router.post("/events/{event_id}/report")
def report_event(
    event_id: int, body: Reason, user: User = Depends(current_user),
    session: Session = Depends(get_session),
) -> dict:  # fmt: skip
    ev = session.get(Event, event_id)
    if ev is None:
        raise HTTPException(404, "No such event")
    if ev.creator_id == user.id:
        raise HTTPException(400, "You can't report your own event")
    new = M.report_event(session, user, ev, body.reason)
    session.commit()
    return {"reported": True, "already": not new}


class Extend(BaseModel):
    until: date | None = None  # default: as far ahead as the creator's role allows
    skip_dates: list[date] = Field(default_factory=list)


@router.post("/series/{series_id}/extend", status_code=201)
def extend_series(
    series_id: int, body: Extend, user: User = Depends(current_user),
    session: Session = Depends(get_session),
):  # fmt: skip
    return _rule_errors(lambda: events_out(
        session, svc.extend_series(session, user, series_id, body.until, body.skip_dates), user
    ))  # fmt: skip


class RoomLimit(BaseModel):
    max_overlapping: int | None = Field(default=None, ge=1, le=50)  # None = default


@router.patch("/rooms/{room_id}")
def set_room_limit(
    room_id: int, body: RoomLimit, user: User = Depends(require("map.manage")),
    session: Session = Depends(get_session),
) -> dict:  # fmt: skip
    """Per-room overlap limit, e.g. the cafeteria or the quad (Phase 2)."""
    room = session.get(Room, room_id)
    if room is None:
        raise HTTPException(404, "No such room")
    room.max_overlapping = body.max_overlapping
    session.add(room)
    M.log(session, user, "room_limit",
          f"Room {room.name}: overlap limit {body.max_overlapping or 'default'}")  # fmt: skip
    session.commit()
    return rooms_out(session, {room.id})[room.id]


@router.post("/events/{event_id}/cancel")
def cancel_event(
    event_id: int,
    body: EventCancel,
    user: User = Depends(current_user),
    session: Session = Depends(get_session),
):
    return _rule_errors(
        lambda: {"cancelled": svc.cancel(session, user, event_id, body.scope, body.reason)}
    )
