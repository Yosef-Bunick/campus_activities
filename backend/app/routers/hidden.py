"""Hidden (architecture §3, §10): hide a person, one event, or a whole series.
Hidden things drop out of every feed; /hidden lists them with Unhide."""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlmodel import Session, col, select

from app.core.auth import current_user
from app.core.database import get_session
from app.models.event import Event
from app.models.social import HiddenEvent, UserHidden
from app.models.user import User
from app.routers.auth import user_public
from app.routers.events import events_out
from app.schemas.events import CancelScope

router = APIRouter(tags=["hidden"])


class HideBody(BaseModel):
    # "this" = this date only; "series" = every date of its series.
    scope: CancelScope = CancelScope.THIS


def _event(session: Session, event_id: int) -> Event:
    ev = session.get(Event, event_id)
    if ev is None:
        raise HTTPException(404, "No such event")
    return ev


def _rows_for(session: Session, me: User, ev: Event) -> list[HiddenEvent]:
    """The hide rows covering this event: its own and its series'."""
    q = select(HiddenEvent).where(HiddenEvent.user_id == me.id)
    rows = list(session.exec(q.where(HiddenEvent.event_id == ev.id)))
    if ev.series_id:
        rows += list(session.exec(q.where(HiddenEvent.series_id == ev.series_id)))
    return rows


@router.post("/events/{event_id}/hide")
def hide_event(
    event_id: int, body: HideBody, me: User = Depends(current_user),
    session: Session = Depends(get_session),
) -> dict:  # fmt: skip
    ev = _event(session, event_id)
    whole = body.scope != CancelScope.THIS and ev.series_id
    cond = HiddenEvent.series_id == ev.series_id if whole else HiddenEvent.event_id == ev.id
    exists = session.exec(select(HiddenEvent).where(HiddenEvent.user_id == me.id, cond)).first()
    if exists is None:
        session.add(
            HiddenEvent(user_id=me.id, series_id=ev.series_id)
            if whole
            else HiddenEvent(user_id=me.id, event_id=ev.id)
        )
        session.commit()
    return {"ok": True}


@router.post("/events/{event_id}/unhide")
def unhide_event(
    event_id: int, me: User = Depends(current_user), session: Session = Depends(get_session)
) -> dict:
    for row in _rows_for(session, me, _event(session, event_id)):
        session.delete(row)
    session.commit()
    return {"ok": True}


@router.post("/users/{user_id}/hide")
def hide_person(
    user_id: int, me: User = Depends(current_user), session: Session = Depends(get_session)
) -> dict:
    if user_id == me.id or session.get(User, user_id) is None:
        raise HTTPException(400, "You can't hide that person")
    if session.get(UserHidden, (me.id, user_id)) is None:
        session.add(UserHidden(user_id=me.id, hidden_user_id=user_id))
        session.commit()
    return {"ok": True}


@router.post("/users/{user_id}/unhide")
def unhide_person(
    user_id: int, me: User = Depends(current_user), session: Session = Depends(get_session)
) -> dict:
    row = session.get(UserHidden, (me.id, user_id))
    if row is not None:
        session.delete(row)
        session.commit()
    return {"ok": True}


@router.get("/hidden")
def my_hidden(me: User = Depends(current_user), session: Session = Depends(get_session)) -> dict:
    """People, single events and series you've hidden. A series shows as its
    first date, with `hidden: "series"`."""
    ids = [
        h.hidden_user_id
        for h in session.exec(select(UserHidden).where(UserHidden.user_id == me.id))
    ]
    people = list(session.exec(select(User).where(col(User.id).in_(ids)))) if ids else []
    rows = list(session.exec(select(HiddenEvent).where(HiddenEvent.user_id == me.id)))
    events: list[tuple[str, Event]] = []
    for r in rows:
        if r.event_id:
            ev = session.get(Event, r.event_id)
            if ev:
                events.append(("event", ev))
        elif r.series_id:
            ev = session.exec(
                select(Event).where(Event.series_id == r.series_id).order_by(Event.starts_at)
            ).first()
            if ev:
                events.append(("series", ev))
    events.sort(key=lambda kv: kv[1].starts_at)
    out = events_out(session, [ev for _, ev in events], me)
    for item, (kind, _) in zip(out, events, strict=True):
        item["hidden"] = kind
    return {
        "people": [user_public(p) for p in sorted(people, key=lambda p: p.display_name.lower())],
        "events": out,
    }
