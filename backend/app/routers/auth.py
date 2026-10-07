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
from app.core import majors as majors_list
from app.core.majors import is_major
from app.core.terms import TERMS, TERMS_VERSION
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
        "user": {
            **user_public(user), "email": user.email, "major": user.major,
            "major_label": majors_list.majors().get(user.major or ""),
        },
        # Ask for a major at first sign-in, and again if their major was removed
        # from majors.txt (ADR-032).
        "needs_major": not is_major(user.major or ""),
        "permissions": permissions_for(role),
        "limits": limits_for(role),
        "csrf_token": csrf,
        # Shown once at first sign-in, and again whenever TERMS_VERSION changes.
        "terms": None if user.terms_version >= TERMS_VERSION
        else {"version": TERMS_VERSION, "items": TERMS},
    }


@router.get("/majors")
def list_majors(_: User = Depends(current_user)) -> list[dict]:
    """The pickable majors, from backend/majors.txt."""
    return [{"key": k, "label": v} for k, v in majors_list.majors().items()]


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


class TermsBody(BaseModel):
    version: int


@router.post("/me/accept-terms")
def accept_terms(
    body: TermsBody, user: User = Depends(current_user), session: Session = Depends(get_session)
) -> dict:
    if body.version != TERMS_VERSION:
        raise HTTPException(409, "The terms changed. Please reload.")
    user.terms_version = TERMS_VERSION
    session.add(user)
    session.commit()
    return {"ok": True}


class DeleteBody(BaseModel):
    confirm: str  # must be the literal "DELETE" (same guard as unified)


@router.post("/me/delete")
def delete_me(
    body: DeleteBody, response: Response, user: User = Depends(current_user),
    session: Session = Depends(get_session),
) -> dict:  # fmt: skip
    """Delete my account and everything that's mine, now (architecture §9)."""
    from app.services.purge import delete_user

    if body.confirm != "DELETE":
        raise HTTPException(400, 'Type DELETE to confirm')
    delete_user(session, user)
    clear_session_cookies(response)
    return {"deleted": True}


@router.post("/logout")
def logout(request: Request, response: Response, session: Session = Depends(get_session)) -> dict:
    row = sessions.resolve(session, request.cookies.get(SESSION_COOKIE, ""))
    if row is not None:
        sessions.revoke(session, row)
    clear_session_cookies(response)
    return {"ok": True}
