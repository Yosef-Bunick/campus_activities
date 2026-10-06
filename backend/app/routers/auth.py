from fastapi import APIRouter, Depends, HTTPException, Request, Response
from pydantic import BaseModel
from sqlmodel import Session

from app.core.auth import (
    CSRF_COOKIE,
    SESSION_COOKIE,
    clear_session_cookies,
    current_user,
    set_csrf_cookie,
)
from app.core.database import get_session
from app.core.majors import MAJORS, is_major
from app.core.permissions import Role, limits_for, permissions_for
from app.models.user import User
from app.services import sessions

router = APIRouter(prefix="/auth", tags=["auth"])


def user_public(user: User) -> dict:
    return {"id": user.id, "display_name": user.display_name, "role": user.role}


@router.get("/me")
def me(request: Request, response: Response, user: User = Depends(current_user)) -> dict:
    """Who am I + what may I do. The frontend uses this only to show/hide buttons."""
    csrf = request.cookies.get(CSRF_COOKIE) or set_csrf_cookie(response)
    role = Role(user.role)
    return {
        "user": {**user_public(user), "email": user.email, "major": user.major},
        "permissions": permissions_for(role),
        "limits": limits_for(role),
        "csrf_token": csrf,
    }


@router.get("/majors")
def majors(_: User = Depends(current_user)) -> list[dict]:
    """The pickable majors (core/majors.py)."""
    return [{"key": k, "label": v} for k, v in MAJORS.items()]


class MajorBody(BaseModel):
    major: str | None


@router.put("/me/major")
def set_major(
    body: MajorBody, user: User = Depends(current_user), session: Session = Depends(get_session)
) -> dict:
    if body.major is not None and not is_major(body.major):
        raise HTTPException(400, "Unknown major")
    user.major = body.major
    session.add(user)
    session.commit()
    return {"major": user.major}


@router.post("/logout")
def logout(request: Request, response: Response, session: Session = Depends(get_session)) -> dict:
    row = sessions.resolve(session, request.cookies.get(SESSION_COOKIE, ""))
    if row is not None:
        sessions.revoke(session, row)
    clear_session_cookies(response)
    return {"ok": True}
