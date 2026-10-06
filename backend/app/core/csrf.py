"""Double-submit CSRF check (unified main.py CSRFTokenMiddleware, P41 + R29-P0-SEC-3).

Any POST/PUT/PATCH/DELETE that carries the session cookie must:
  1. come from an allowed Origin (FRONTEND_ORIGIN or the API's own host), and
  2. send X-CSRF-Token equal to the csrf_token cookie.
It fails CLOSED: a session cookie without a CSRF cookie is rejected.

The frontend gets the token from GET /auth/me (in the body as well as the
cookie), because on a cross-site deploy the SPA can't read the API's cookie.
"""

from __future__ import annotations

import secrets
from urllib.parse import urlsplit

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

from app.core.auth import CSRF_COOKIE, CSRF_HEADER, SESSION_COOKIE
from app.core.config import settings

UNSAFE = {"POST", "PUT", "PATCH", "DELETE"}

# Sign-in runs before a (valid) session exists, so there is nothing to protect
# yet, and a stale session cookie (expired, or from a reset dev.db) must not
# lock people out of signing in again. Same list idea as unified's
# CSRF_EXEMPT_PREFIXES (R29-P0-SEC-3).
EXEMPT_PREFIXES = ("/auth/dev-login", "/auth/microsoft/")
# Logout is exempt when it comes from the app's own Origin (unified R40): a
# signed-out page with a stale cookie has no CSRF token to send.
LOGOUT = "/auth/logout"


def _origin_allowed(request) -> bool:
    origin = request.headers.get("origin", "")
    if not origin:
        referer = request.headers.get("referer", "")
        if not referer:
            return True  # not a browser; judged on the token pair alone
        parts = urlsplit(referer)
        origin = f"{parts.scheme}://{parts.netloc}"
    if origin == settings.frontend_origin:
        return True
    return origin.split("://", 1)[-1] == request.headers.get("host", "")


class CSRFMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        path = request.url.path
        exempt = path.startswith(EXEMPT_PREFIXES) or (
            path == LOGOUT and request.headers.get("origin") == settings.frontend_origin
        )
        if request.method in UNSAFE and SESSION_COOKIE in request.cookies and not exempt:
            if not _origin_allowed(request):
                return JSONResponse({"detail": "Cross-origin request rejected"}, status_code=403)
            cookie = request.cookies.get(CSRF_COOKIE, "")
            header = request.headers.get(CSRF_HEADER, "")
            if not cookie or not header or not secrets.compare_digest(cookie, header):
                return JSONResponse({"detail": "CSRF token missing or wrong"}, status_code=403)
        return await call_next(request)
