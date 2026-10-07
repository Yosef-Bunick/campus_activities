"""/alerts: your notices, newest first, with read/unread (architecture §3, §10)."""

from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, col, func, select

from app.core.auth import current_user
from app.core.database import get_session
from app.models.event import Alert, Event
from app.models.user import User, as_utc

router = APIRouter(prefix="/alerts", tags=["alerts"])


def _unread(session: Session, me: User) -> int:
    return session.exec(
        select(func.count()).select_from(Alert).where(Alert.user_id == me.id, Alert.read_at.is_(None))
    ).one()


def _event_statuses(session: Session, alerts: list[Alert]) -> dict[int, str]:
    """Status of every event these alerts point at, in one query (not one per alert)."""
    ids = {a.event_id for a in alerts if a.event_id}
    if not ids:
        return {}
    return dict(session.exec(select(Event.id, Event.status).where(col(Event.id).in_(ids))).all())


@router.get("")
def list_alerts(me: User = Depends(current_user), session: Session = Depends(get_session)) -> dict:
    rows = list(session.exec(
        select(Alert).where(Alert.user_id == me.id).order_by(Alert.created_at.desc()).limit(100)
    ))  # fmt: skip
    status = _event_statuses(session, rows)
    return {
        "unread": _unread(session, me),
        "alerts": [
            {
                "id": a.id,
                "kind": a.kind,
                "event_id": a.event_id,
                # Lets the page hide Approve/Reject once someone has decided.
                "event_status": status.get(a.event_id),
                "subject_user_id": a.subject_user_id,
                "message": a.message,
                "read": a.read_at is not None,
                "created_at": as_utc(a.created_at),
            }
            for a in rows
        ],
    }


@router.get("/unread")
def unread_count(me: User = Depends(current_user), session: Session = Depends(get_session)) -> dict:
    """Cheap poll for the tab-bar badge."""
    return {"unread": _unread(session, me)}


@router.post("/{alert_id}/read")
def mark_read(
    alert_id: int, me: User = Depends(current_user), session: Session = Depends(get_session)
) -> dict:
    alert = session.get(Alert, alert_id)
    if alert is None or alert.user_id != me.id:
        raise HTTPException(404, "No such alert")
    if alert.read_at is None:
        alert.read_at = datetime.now(UTC)
        session.add(alert)
        session.commit()
    return {"unread": _unread(session, me)}


@router.post("/read-all")
def mark_all_read(me: User = Depends(current_user), session: Session = Depends(get_session)) -> dict:
    now = datetime.now(UTC)
    for alert in session.exec(select(Alert).where(Alert.user_id == me.id, Alert.read_at.is_(None))):
        alert.read_at = now
        session.add(alert)
    session.commit()
    return {"unread": 0}
