"""Favorites (ADR-025): ★ save one event or a whole series, ♥ follow a person.
/favorites lists saved events + events from people you follow."""

from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlmodel import Session, col, or_, select

from app.core.auth import current_user
from app.core.database import get_session
from app.models.event import Event, EventStatus
from app.models.social import SavedEvent, UserFavorite
from app.models.user import User
from app.routers.auth import user_public
from app.routers.events import events_out
from app.schemas.events import CancelScope
from app.services.events import exclude_hidden

router = APIRouter(tags=["favorites"])


class SaveBody(BaseModel):
    # "this" = this date only; "series" = every date of its series.
    scope: CancelScope = CancelScope.THIS


def _event(session: Session, event_id: int) -> Event:
    ev = session.get(Event, event_id)
    if ev is None:
        raise HTTPException(404, "No such event")
    return ev


def _saved_row(session: Session, me: User, ev: Event, scope: CancelScope):
    if scope != CancelScope.THIS and ev.series_id:
        cond = SavedEvent.series_id == ev.series_id
    else:
        cond = SavedEvent.event_id == ev.id
    return session.exec(select(SavedEvent).where(SavedEvent.user_id == me.id, cond)).first()


@router.post("/events/{event_id}/save")
def save(
    event_id: int, body: SaveBody, me: User = Depends(current_user),
    session: Session = Depends(get_session),
) -> dict:  # fmt: skip
    ev = _event(session, event_id)
    if _saved_row(session, me, ev, body.scope) is None:
        whole = body.scope != CancelScope.THIS and ev.series_id
        session.add(
            SavedEvent(user_id=me.id, series_id=ev.series_id)
            if whole
            else SavedEvent(user_id=me.id, event_id=ev.id)
        )
        session.commit()
    return {"ok": True}


@router.post("/events/{event_id}/unsave")
def unsave(event_id: int, me: User = Depends(current_user), session: Session = Depends(get_session)) -> dict:
    """Removes both the date and its series, so the ★ always clears."""
    ev = _event(session, event_id)
    for scope in (CancelScope.THIS, CancelScope.SERIES):
        row = _saved_row(session, me, ev, scope)
        if row is not None:
            session.delete(row)
    session.commit()
    return {"ok": True}


@router.post("/users/{user_id}/favorite")
def favorite(user_id: int, me: User = Depends(current_user), session: Session = Depends(get_session)) -> dict:
    if user_id == me.id or session.get(User, user_id) is None:
        raise HTTPException(400, "You can't favorite that person")
    if session.get(UserFavorite, (me.id, user_id)) is None:
        session.add(UserFavorite(user_id=me.id, favorite_user_id=user_id))
        session.commit()
    return {"ok": True}


@router.post("/users/{user_id}/unfavorite")
def unfavorite(user_id: int, me: User = Depends(current_user), session: Session = Depends(get_session)) -> dict:
    row = session.get(UserFavorite, (me.id, user_id))
    if row is not None:
        session.delete(row)
        session.commit()
    return {"ok": True}


@router.get("/favorites")
def my_favorites(me: User = Depends(current_user), session: Session = Depends(get_session)) -> dict:
    now = datetime.now(UTC)
    upcoming = (Event.ends_at > now, or_(Event.status == EventStatus.ACTIVE.value, Event.ends_at > now))
    saved_rows = list(session.exec(select(SavedEvent).where(SavedEvent.user_id == me.id)))
    ev_ids = [r.event_id for r in saved_rows if r.event_id]
    series_ids = [r.series_id for r in saved_rows if r.series_id]
    saved = list(
        session.exec(
            select(Event)
            .where(*upcoming, or_(col(Event.id).in_(ev_ids), col(Event.series_id).in_(series_ids)))
            .order_by(Event.starts_at)
            .limit(200)
        )
    ) if saved_rows else []  # fmt: skip
    fav_ids = [
        f.favorite_user_id
        for f in session.exec(select(UserFavorite).where(UserFavorite.user_id == me.id))
    ]
    people = list(session.exec(select(User).where(col(User.id).in_(fav_ids)))) if fav_ids else []
    from_people = list(
        session.exec(
            exclude_hidden(select(Event), me.id)
            .where(*upcoming, col(Event.creator_id).in_(fav_ids))
            .order_by(Event.starts_at)
            .limit(200)
        )
    ) if fav_ids else []  # fmt: skip
    return {
        "saved": events_out(session, saved, me),
        "from_people": events_out(session, from_people, me),
        "people": [user_public(p) for p in sorted(people, key=lambda p: p.display_name.lower())],
    }
