"""RSVPs (ADR-035): "I'm going" on one event; the feed shows a live count.
Same visibility rule as GET /events/{id}: pending events only for their creator."""

from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session

from app.core.auth import current_user
from app.core.database import get_session
from app.models.event import Event, EventStatus
from app.models.social import Rsvp
from app.models.user import User, as_utc

router = APIRouter(tags=["rsvp"])


def _visible(session: Session, me: User, event_id: int) -> Event:
    ev = session.get(Event, event_id)
    public = ev is not None and ev.status in (EventStatus.ACTIVE.value, EventStatus.CANCELLED.value)
    if ev is None or not (public or ev.creator_id == me.id):
        raise HTTPException(404, "No such event")
    return ev


@router.post("/events/{event_id}/going")
def going(event_id: int, me: User = Depends(current_user), session: Session = Depends(get_session)) -> dict:
    ev = _visible(session, me, event_id)
    # Only a live event can be joined: not cancelled/rejected, not already over.
    if ev.status in (EventStatus.CANCELLED.value, EventStatus.REJECTED.value):
        raise HTTPException(400, "This event isn't happening")
    if as_utc(ev.ends_at) <= datetime.now(UTC):
        raise HTTPException(400, "This event is over")
    if session.get(Rsvp, (me.id, ev.id)) is None:
        session.add(Rsvp(user_id=me.id, event_id=ev.id))
        session.commit()
    return {"ok": True}


@router.post("/events/{event_id}/not-going")
def not_going(event_id: int, me: User = Depends(current_user), session: Session = Depends(get_session)) -> dict:
    # Always allowed (even once over/cancelled), so a mistaken RSVP can be undone.
    ev = _visible(session, me, event_id)
    row = session.get(Rsvp, (me.id, ev.id))
    if row is not None:
        session.delete(row)
        session.commit()
    return {"ok": True}
