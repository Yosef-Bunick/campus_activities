"""Sign in with Microsoft (OpenID Connect, architecture §8, ADR-029).

Flow: /auth/microsoft/login redirects to Microsoft with state + nonce + PKCE,
kept in a short-lived signed cookie. /auth/microsoft/callback swaps the code
for an ID token, then `validate_id_token` checks signature (Microsoft's
published keys), audience, issuer, expiry and nonce. Only then does
services/accounts.sign_in() apply the WCC tenant/domain gate.

Token checks use joserfc (shipped with authlib). The authorization-code
exchange uses httpx, the HTTP client authlib itself uses.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import secrets
import time
from urllib.parse import urlencode

import httpx
from joserfc import jwt
from joserfc.errors import JoseError
from joserfc.jwk import KeySet

from app.core.config import settings

# "common" so the owner can use a personal Microsoft account (ADR-029); the
# WCC tenant/domain gate is enforced after validation, in accounts.gate().
AUTHORIZE_URL = "https://login.microsoftonline.com/common/oauth2/v2.0/authorize"
TOKEN_URL = "https://login.microsoftonline.com/common/oauth2/v2.0/token"  # noqa: S105 (a URL)
JWKS_URL = "https://login.microsoftonline.com/common/discovery/v2.0/keys"
SCOPES = "openid profile email"
FLOW_COOKIE = "ms_flow"
FLOW_TTL = 600  # seconds to finish signing in at Microsoft
CLOCK_LEEWAY = 120


class MicrosoftAuthError(Exception):
    """Anything wrong with the Microsoft round trip. The message is shown to the user."""


def configured() -> bool:
    return bool(settings.ms_client_id and settings.ms_client_secret and settings.session_secret)


# ── The signed flow cookie (state, nonce, PKCE verifier) ──


def _sign(payload: bytes) -> str:
    mac = hmac.new(settings.session_secret.encode(), payload, hashlib.sha256).hexdigest()
    return base64.urlsafe_b64encode(payload).decode() + "." + mac


def _unsign(value: str) -> dict:
    try:
        body, mac = value.rsplit(".", 1)
        payload = base64.urlsafe_b64decode(body.encode())
    except (ValueError, TypeError) as e:
        raise MicrosoftAuthError("Sign-in expired. Please try again.") from e
    good = hmac.new(settings.session_secret.encode(), payload, hashlib.sha256).hexdigest()
    if not hmac.compare_digest(mac, good):
        raise MicrosoftAuthError("Sign-in expired. Please try again.")
    flow = json.loads(payload)
    if flow.get("exp", 0) < time.time():
        raise MicrosoftAuthError("Sign-in took too long. Please try again.")
    return flow


def start_flow() -> tuple[str, str]:
    """Returns (Microsoft authorize URL, signed flow cookie value)."""
    flow = {
        "state": secrets.token_urlsafe(24),
        "nonce": secrets.token_urlsafe(24),
        "verifier": secrets.token_urlsafe(48),
        "exp": int(time.time()) + FLOW_TTL,
    }
    challenge = (
        base64.urlsafe_b64encode(hashlib.sha256(flow["verifier"].encode()).digest())
        .rstrip(b"=")
        .decode()
    )
    params = {
        "client_id": settings.ms_client_id,
        "response_type": "code",
        "redirect_uri": settings.ms_redirect_uri,
        "response_mode": "query",
        "scope": SCOPES,
        "state": flow["state"],
        "nonce": flow["nonce"],
        "code_challenge": challenge,
        "code_challenge_method": "S256",
        "prompt": "select_account",
    }
    return f"{AUTHORIZE_URL}?{urlencode(params)}", _sign(json.dumps(flow).encode())


def check_state(cookie_value: str, state: str) -> dict:
    flow = _unsign(cookie_value or "")
    if not state or not hmac.compare_digest(flow["state"], state):
        raise MicrosoftAuthError("Sign-in expired. Please try again.")
    return flow


# ── Code exchange + ID-token validation ──


def exchange_code(code: str, verifier: str) -> str:
    """Authorization code → ID token (server to server, with the client secret)."""
    try:
        r = httpx.post(
            TOKEN_URL,
            data={
                "client_id": settings.ms_client_id,
                "client_secret": settings.ms_client_secret,
                "grant_type": "authorization_code",
                "code": code,
                "redirect_uri": settings.ms_redirect_uri,
                "code_verifier": verifier,
                "scope": SCOPES,
            },
            timeout=15,
        )
    except httpx.HTTPError as e:
        raise MicrosoftAuthError("Couldn't reach Microsoft. Please try again.") from e
    if r.status_code != 200 or "id_token" not in r.json():
        raise MicrosoftAuthError("Microsoft didn't accept the sign-in. Please try again.")
    return r.json()["id_token"]


_jwks: dict = {"keys": None, "fetched": 0.0}


def _keyset(force: bool = False) -> KeySet:
    """Microsoft's signing keys, cached for a day (refetched once on an unknown key id)."""
    if force or _jwks["keys"] is None or time.time() - _jwks["fetched"] > 86400:
        try:
            r = httpx.get(JWKS_URL, timeout=15)
            r.raise_for_status()
        except httpx.HTTPError as e:
            raise MicrosoftAuthError("Couldn't reach Microsoft. Please try again.") from e
        _jwks["keys"], _jwks["fetched"] = r.json(), time.time()
    return KeySet.import_key_set(_jwks["keys"])


def validate_id_token(id_token: str, nonce: str) -> dict:
    """Signature, audience, issuer, expiry, nonce. Returns the claims."""
    try:
        try:
            token = jwt.decode(id_token, _keyset(), algorithms=["RS256"])
        except JoseError:
            token = jwt.decode(id_token, _keyset(force=True), algorithms=["RS256"])  # key rotation
        claims = token.claims
        jwt.JWTClaimsRegistry(
            leeway=CLOCK_LEEWAY,
            aud={"essential": True, "value": settings.ms_client_id},
            exp={"essential": True},
            iat={"essential": True},
            nonce={"essential": True, "value": nonce},
            tid={"essential": True},
            oid={"essential": True},
        ).validate(claims)
    except (JoseError, ValueError) as e:
        raise MicrosoftAuthError("Microsoft's sign-in couldn't be verified.") from e
    # Multi-tenant ("common") issuer: must be exactly this tenant's v2.0 issuer.
    if claims.get("iss") != f"https://login.microsoftonline.com/{claims['tid']}/v2.0":
        raise MicrosoftAuthError("Microsoft's sign-in couldn't be verified.")
    return claims


def email_from(claims: dict) -> str:
    """Work/school accounts often omit `email`; preferred_username is the UPN."""
    return (claims.get("email") or claims.get("preferred_username") or "").strip().lower()
