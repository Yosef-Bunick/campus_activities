"""/alerts: your notices, newest first, with read/unread (architecture §3, §10)."""

from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, func, select

from app.core.auth import current_user
from app.core.database import get_session
from app.models.event import Alert
from app.models.user import User, as_utc

router = APIRouter(prefix="/alerts", tags=["alerts"])


def _unread(session: Session, me: User) -> int:
    return session.exec(
        select(func.count()).select_from(Alert).where(Alert.user_id == me.id, Alert.read_at.is_(None))
    ).one()


@router.get("")
def list_alerts(me: User = Depends(current_user), session: Session = Depends(get_session)) -> dict:
    rows = session.exec(
        select(Alert).where(Alert.user_id == me.id).order_by(Alert.created_at.desc()).limit(100)
    )
    return {
        "unread": _unread(session, me),
        "alerts": [
            {
                "id": a.id,
                "kind": a.kind,
                "event_id": a.event_id,
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
