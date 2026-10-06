"""Person sheet actions: view a person, ban/unban, change role (architecture §3, §5)."""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlmodel import Session

from app.core.auth import current_user, require
from app.core.database import get_session
from app.core.permissions import Role, can, outranks
from app.models.social import UserFavorite, UserHidden
from app.models.user import BannedAccount, User
from app.routers.auth import user_public
from app.services import events as event_svc
from app.services import sessions
from app.services.accounts import account_hash

router = APIRouter(prefix="/users", tags=["users"])


def _target(session: Session, user_id: int) -> User:
    user = session.get(User, user_id)
    if user is None:
        raise HTTPException(404, "No such person")
    return user


def _check_hierarchy(actor: User, target: User) -> None:
    if actor.id == target.id or not outranks(Role(actor.role), Role(target.role)):
        raise HTTPException(403, "You can only act on people below your role")


@router.get("/{user_id}")
def person(
    user_id: int, me: User = Depends(current_user), session: Session = Depends(get_session)
) -> dict:
    """What the person sheet shows, including which buttons this viewer gets."""
    target = _target(session, user_id)
    mine, theirs = Role(me.role), Role(target.role)
    above = me.id != target.id and outranks(mine, theirs)
    can_change_role = above and can(mine, "user.change_role")
    return {
        **user_public(target),
        "is_banned": target.is_banned,
        "is_favorite": session.get(UserFavorite, (me.id, target.id)) is not None,
        "is_hidden": session.get(UserHidden, (me.id, target.id)) is not None,
        "actions": {
            "favorite": me.id != target.id,
            "hide": me.id != target.id,
            "ban": above and can(mine, "user.ban"),
            "change_role": can_change_role,
        },
        # Roles this viewer may assign: strictly below their own.
        "assignable_roles": [r.value for r in Role if outranks(mine, r)] if can_change_role else [],
    }


@router.post("/{user_id}/ban")
def ban(
    user_id: int, me: User = Depends(require("user.ban")), session: Session = Depends(get_session)
) -> dict:
    target = _target(session, user_id)
    _check_hierarchy(me, target)
    target.is_banned = True
    session.add(target)
    h = account_hash(target.ms_tenant_id, target.ms_object_id)
    if session.get(BannedAccount, h) is None:
        session.add(BannedAccount(account_sha256=h))
    session.commit()
    sessions.revoke_all(session, target.id)
    cancelled = event_svc.cancel_upcoming_for_ban(session, me, target.id)
    return {"ok": True, "events_cancelled": cancelled}


@router.post("/{user_id}/unban")
def unban(
    user_id: int, me: User = Depends(require("user.ban")), session: Session = Depends(get_session)
) -> dict:
    target = _target(session, user_id)
    _check_hierarchy(me, target)
    target.is_banned = False
    session.add(target)
    row = session.get(BannedAccount, account_hash(target.ms_tenant_id, target.ms_object_id))
    if row is not None:
        session.delete(row)
    session.commit()
    return {"ok": True}


class RoleChange(BaseModel):
    role: Role


@router.put("/{user_id}/role")
def change_role(
    user_id: int,
    body: RoleChange,
    me: User = Depends(require("user.change_role")),
    session: Session = Depends(get_session),
) -> dict:
    target = _target(session, user_id)
    _check_hierarchy(me, target)
    if not outranks(Role(me.role), body.role):
        raise HTTPException(403, "You can only assign roles below your own")
    target.role = body.role.value
    session.add(target)
    session.commit()
    return user_public(target)
