"""Local developer sign-in (ADR-023). Off unless DEV_LOGIN=1 AND the frontend
is http://localhost. No passwords: you type an email (still gated to WCC
domains) and pick a role to test with."""

from fastapi import APIRouter, Depends, HTTPException, Response
from pydantic import BaseModel
from sqlmodel import Session

from app.core.auth import set_session_cookies
from app.core.config import settings
from app.core.database import get_session
from app.core.permissions import Role
from app.services import sessions
from app.services.accounts import MicrosoftIdentity, SignInRejected, sign_in

router = APIRouter(prefix="/auth", tags=["auth"])
WCC_TENANT = "4981a704-f6a3-4ac0-89c2-a3812354a3ff"


@router.get("/config")
def auth_config() -> dict:
    """Which sign-in options the sign-in page should show."""
    return {"microsoft": bool(settings.ms_client_id), "dev_login": settings.dev_login}


class DevLogin(BaseModel):
    email: str
    role: Role = Role.STUDENT


@router.post("/dev-login")
def dev_login(body: DevLogin, response: Response, session: Session = Depends(get_session)):
    if not settings.dev_login:
        raise HTTPException(404, "Not found")
    email = body.email.strip().lower()
    name = email.split("@")[0]
    try:
        user = sign_in(session, MicrosoftIdentity(WCC_TENANT, f"dev:{email}", email, name))
    except SignInRejected as e:
        raise HTTPException(403, str(e)) from None
    if user.role != body.role.value:
        user.role = body.role.value
        session.add(user)
        session.commit()
    set_session_cookies(response, sessions.create(session, user))
    return {"ok": True}
