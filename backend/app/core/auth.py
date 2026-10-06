"""Session cookie + CSRF helpers and the `current_user` / `require` dependencies.

Copied from unified's _auth_shared.py and main.py (SEC24-10, P41, R29-P0-SEC-3),
trimmed to one cookie policy derived from FRONTEND_ORIGIN:
  * local dev (http://localhost:5173 -> http://localhost:8000) is same-site: Lax.
  * production over HTTPS may be cross-site (Vercel -> Render): None + Secure.
"""

from __future__ import annotations

import secrets
from datetime import UTC, datetime, timedelta

from fastapi import Depends, HTTPException, Request, Response
from sqlmodel import Session

from app.core.config import settings
from app.core.database import get_session
from app.core.permissions import Role, can
from app.models.user import User, as_utc
from app.services import sessions

SESSION_COOKIE = "session"
CSRF_COOKIE = "csrf_token"
CSRF_HEADER = "X-CSRF-Token"
ACTIVE_STAMP_EVERY = timedelta(hours=1)


def _cookie_opts() -> dict:
    secure = settings.frontend_origin.startswith("https://")
    return {"path": "/", "secure": secure, "samesite": "none" if secure else "lax"}


def set_session_cookies(response: Response, token: str) -> str:
    """Session cookie (httpOnly) + a fresh CSRF token, rotated on every sign-in
    so a token captured under an old session is useless."""
    max_age = int(sessions.SESSION_TTL.total_seconds())
    response.set_cookie(SESSION_COOKIE, token, max_age=max_age, httponly=True, **_cookie_opts())
    return set_csrf_cookie(response)


def set_csrf_cookie(response: Response, token: str | None = None) -> str:
    token = token or secrets.token_hex(32)
    max_age = int(sessions.SESSION_TTL.total_seconds())
    response.set_cookie(CSRF_COOKIE, token, max_age=max_age, httponly=False, **_cookie_opts())
    return token


def clear_session_cookies(response: Response) -> None:
    opts = _cookie_opts()
    response.delete_cookie(SESSION_COOKIE, httponly=True, **opts)
    response.delete_cookie(CSRF_COOKIE, httponly=False, **opts)


def current_user(request: Request, session: Session = Depends(get_session)) -> User:
    row = sessions.resolve(session, request.cookies.get(SESSION_COOKIE, ""))
    if row is None:
        raise HTTPException(401, "Not signed in")
    user = session.get(User, row.user_id)
    if user is None or user.is_banned:
        raise HTTPException(401, "Not signed in")
    # last_active_at feeds the 150-day purge; write it at most once an hour.
    now = datetime.now(UTC)
    if now - as_utc(user.last_active_at) >= ACTIVE_STAMP_EVERY:
        user.last_active_at = now
        session.add(user)
        session.commit()
        session.refresh(user)
    return user


def require(perm: str):
    """Dependency factory: 403 unless the signed-in user's role has `perm`."""

    def _dep(user: User = Depends(current_user)) -> User:
        if not can(Role(user.role), perm):
            raise HTTPException(403, "You don't have permission to do that")
        return user

    return _dep
