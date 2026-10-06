"""GET /modlog: who did what (owner, manager, security; architecture §5)."""

from fastapi import APIRouter, Depends
from sqlmodel import Session, col, select

from app.core.auth import require
from app.core.database import get_session
from app.models.moderation import ModerationLog
from app.models.user import User, as_utc

router = APIRouter(tags=["moderation"])


@router.get("/modlog")
def modlog(_: User = Depends(require("modlog.view")), session: Session = Depends(get_session)):
    rows = list(session.exec(select(ModerationLog).order_by(col(ModerationLog.id).desc()).limit(200)))
    ids = {i for r in rows for i in (r.actor_id, r.target_user_id) if i}
    people = {u.id: u for u in session.exec(select(User).where(col(User.id).in_(ids)))} if ids else {}

    def who(i):
        return (people[i].display_name or people[i].email) if i in people else None

    return [
        {
            "id": r.id, "action": r.action, "detail": r.detail,
            "actor": who(r.actor_id) if r.actor_id else ("system" if r.action == "flag" else "a deleted user"),
            "target_user_id": r.target_user_id, "target_event_id": r.target_event_id,
            "created_at": as_utc(r.created_at),
        }  # fmt: skip
        for r in rows
    ]
