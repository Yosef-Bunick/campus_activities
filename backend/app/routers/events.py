from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import JSONResponse
from fastapi.encoders import jsonable_encoder
from sqlmodel import Session, col, select

from app.core.auth import current_user, require
from app.core.database import get_session
from app.models.event import Event, EventType
from app.models.place import Building, Floor, Room
from app.models.user import User, as_utc
from app.schemas.events import EventCancel, EventCreate, EventFilter, EventUpdate
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


def rooms_out(session: Session) -> dict[int, dict]:
    rows = session.exec(
        select(Room, Floor, Building)
        .join(Floor, Floor.id == Room.floor_id, isouter=True)
        .join(Building, Building.id == Floor.building_id, isouter=True)
    ).all()
    return {
        r.id: {
            "id": r.id,
            "name": r.name,
            "floor": f.level if f else None,
            "building_id": b.id if b else None,
            "building": b.name if b else None,
            "is_outdoor": r.is_outdoor,
        }
        for r, f, b in rows
    }


def events_out(session: Session, events: list[Event]) -> list[dict]:
    rooms = rooms_out(session)
    ids = {e.creator_id for e in events}
    people = (
        {u.id: u for u in session.exec(select(User).where(col(User.id).in_(ids)))} if ids else {}
    )
    return [
        {
            "id": e.id,
            "series_id": e.series_id,
            "title": e.title,
            "description": e.description,
            "type": e.type,
            "status": e.status,
            "starts_at": as_utc(e.starts_at),
            "ends_at": as_utc(e.ends_at),
            "room": rooms.get(e.room_id),
            "creator": {"id": e.creator_id, "display_name": people[e.creator_id].display_name}
            if e.creator_id in people
            else None,
            "cancelled_reason": e.cancelled_reason,
        }
        for e in events
    ]


@router.get("/rooms")
def list_rooms(_: User = Depends(current_user), session: Session = Depends(get_session)):
    return sorted(rooms_out(session).values(), key=lambda r: (r["building"] or "", r["name"]))


@router.get("/events")
def list_events(
    types: list[EventType] = Query(default=list(EventType)),
    start: datetime | None = None,
    end: datetime | None = None,
    happening_now: bool = False,
    building_ids: list[int] = Query(default=[]),
    room_ids: list[int] = Query(default=[]),
    search: str = "",
    _: User = Depends(require("event.view")),
    session: Session = Depends(get_session),
):
    """Used by Home, Calendar and (Milestone 3) Map — one shared filter."""
    f = EventFilter(
        types=types, start=start, end=end, happening_now=happening_now,
        building_ids=building_ids, room_ids=room_ids, search=search,
    )  # fmt: skip
    return events_out(session, svc.list_events(session, f))


@router.post("/events", status_code=201)
def create_event(
    body: EventCreate,
    user: User = Depends(current_user),
    session: Session = Depends(get_session),
):
    def run():
        return events_out(session, svc.create(session, user, body))

    return _rule_errors(run)


@router.patch("/events/{event_id}")
def update_event(
    event_id: int,
    body: EventUpdate,
    user: User = Depends(current_user),
    session: Session = Depends(get_session),
):
    return _rule_errors(lambda: events_out(session, [svc.update(session, user, event_id, body)])[0])


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
