"""GET /auth/microsoft/login and /auth/microsoft/callback (architecture §8)."""

from urllib.parse import urlencode

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import RedirectResponse
from sqlmodel import Session

from app.core import microsoft_auth as ms
from app.core.auth import set_session_cookies
from app.core.config import settings
from app.core.database import get_session
from app.services import sessions
from app.services.accounts import MicrosoftIdentity, SignInRejected, sign_in

router = APIRouter(prefix="/auth/microsoft", tags=["auth"])


def _flow_cookie_opts() -> dict:
    # Lax: the browser sends it on Microsoft's top-level redirect back to us.
    secure = settings.ms_redirect_uri.startswith("https://")
    return {"httponly": True, "secure": secure, "samesite": "lax", "path": "/auth/microsoft"}


def _back_to_app(error: str | None = None) -> RedirectResponse:
    url = f"{settings.frontend_origin}/home"
    if error:
        url = f"{settings.frontend_origin}/?{urlencode({'signin_error': error})}"
    resp = RedirectResponse(url, status_code=303)
    resp.delete_cookie(ms.FLOW_COOKIE, **_flow_cookie_opts())
    return resp


@router.get("/login")
def login():
    if not ms.configured():
        raise HTTPException(503, "Microsoft sign-in isn't set up yet")
    url, flow = ms.start_flow()
    resp = RedirectResponse(url, status_code=303)
    resp.set_cookie(ms.FLOW_COOKIE, flow, max_age=ms.FLOW_TTL, **_flow_cookie_opts())
    return resp


@router.get("/callback")
def callback(
    request: Request,
    code: str = "",
    state: str = "",
    error: str = "",
    session: Session = Depends(get_session),
):
    if not ms.configured():
        raise HTTPException(503, "Microsoft sign-in isn't set up yet")
    if error:
        # e.g. the user cancelled, or "Need admin approval" (consent not granted).
        return _back_to_app("Microsoft sign-in was cancelled or not approved.")
    try:
        flow = ms.check_state(request.cookies.get(ms.FLOW_COOKIE, ""), state)
        claims = ms.validate_id_token(ms.exchange_code(code, flow["verifier"]), flow["nonce"])
        ident = MicrosoftIdentity(
            tid=claims["tid"], oid=claims["oid"], email=ms.email_from(claims),
            name=claims.get("name", ""),
        )  # fmt: skip
        user = sign_in(session, ident)
    except (ms.MicrosoftAuthError, SignInRejected) as e:
        return _back_to_app(str(e))
    resp = _back_to_app()
    set_session_cookies(resp, sessions.create(session, user))
    return resp
