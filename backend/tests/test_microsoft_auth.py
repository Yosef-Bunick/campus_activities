"""Sign in with Microsoft, end to end, with a fake Microsoft: our own RSA key
signs the ID tokens and stands in for Microsoft's published keys."""

import time
from dataclasses import replace
from urllib.parse import parse_qs, urlsplit

import pytest
from joserfc import jwt
from joserfc.jwk import KeySet, RSAKey

from app.core import config, microsoft_auth as ms
from app.routers import dev_auth, microsoft_auth as ms_router
from tests.conftest import WCC, client_for

CLIENT_ID = "test-client-id"
KEY = RSAKey.generate_key(2048, parameters={"kid": "k1", "use": "sig", "alg": "RS256"})
OTHER_KEY = RSAKey.generate_key(2048, parameters={"kid": "k1", "use": "sig", "alg": "RS256"})


@pytest.fixture(autouse=True)
def fake_microsoft(monkeypatch):
    s = replace(
        config.settings, ms_client_id=CLIENT_ID, ms_client_secret="secret",
        session_secret="x" * 32, ms_redirect_uri="http://localhost:8000/auth/microsoft/callback",
    )  # fmt: skip
    for mod in (ms, ms_router, dev_auth):
        monkeypatch.setattr(mod, "settings", s)
    monkeypatch.setattr(ms, "_keyset", lambda force=False: KeySet([KEY]))
    state = {}
    monkeypatch.setattr(ms, "exchange_code", lambda code, verifier: state["id_token"])
    return state


def id_token(expected_nonce, key=KEY, **over):
    now = int(time.time())
    claims = {
        "iss": f"https://login.microsoftonline.com/{WCC}/v2.0", "aud": CLIENT_ID,
        "iat": now, "nbf": now, "exp": now + 3600, "nonce": expected_nonce,
        "tid": WCC, "oid": "oid-123", "name": "Ana Student",
        "preferred_username": "ana@my.sunywcc.edu",
    }  # fmt: skip
    claims.update(over)
    return jwt.encode({"alg": "RS256", "kid": "k1"}, claims, key)


def start(c):
    r = c.get("/auth/microsoft/login", follow_redirects=False)
    assert r.status_code == 303
    q = parse_qs(urlsplit(r.headers["location"]).query)
    assert q["client_id"] == [CLIENT_ID] and q["code_challenge_method"] == ["S256"]
    return q["state"][0], q["nonce"][0]


def finish(c, state):
    return c.get(f"/auth/microsoft/callback?code=abc&state={state}", follow_redirects=False)


def test_config_reports_microsoft_ready(db):
    assert client_for(db).get("/auth/config").json()["microsoft"] is True


def test_happy_path_signs_in_and_lands_on_home(db, fake_microsoft):
    c = client_for(db)
    state, nonce = start(c)
    fake_microsoft["id_token"] = id_token(nonce)
    r = finish(c, state)
    assert r.status_code == 303 and r.headers["location"] == "http://localhost:5173/home"
    me = c.get("/auth/me").json()
    assert me["user"]["email"] == "ana@my.sunywcc.edu" and me["user"]["display_name"] == "Ana Student"


@pytest.mark.parametrize(
    "bad",
    [
        {"aud": "someone-else"},
        {"exp": int(time.time()) - 3600, "iat": int(time.time()) - 7200},
        {"iss": "https://evil.example/v2.0"},
        {"nonce": "replayed"},
    ],
    ids=["audience", "expired", "issuer", "nonce"],
)
def test_bad_tokens_are_rejected(db, fake_microsoft, bad):
    c = client_for(db)
    state, nonce = start(c)
    fake_microsoft["id_token"] = id_token(nonce, **bad)
    r = finish(c, state)
    assert "signin_error" in r.headers["location"]
    assert c.get("/auth/me").status_code == 401


def test_token_signed_by_wrong_key_is_rejected(db, fake_microsoft):
    c = client_for(db)
    state, nonce = start(c)
    fake_microsoft["id_token"] = id_token(nonce, key=OTHER_KEY)
    assert "signin_error" in finish(c, state).headers["location"]


def test_state_must_match_the_flow_cookie(db, fake_microsoft):
    c = client_for(db)
    _, nonce = start(c)
    fake_microsoft["id_token"] = id_token(nonce)
    assert "signin_error" in finish(c, "forged-state").headers["location"]


def test_callback_without_flow_cookie_is_rejected(db, fake_microsoft):
    c = client_for(db)
    fake_microsoft["id_token"] = id_token("n")
    assert "signin_error" in finish(c, "s").headers["location"]


def test_other_school_is_rejected_with_a_clear_message(db, fake_microsoft):
    c = client_for(db)
    state, nonce = start(c)
    other = "11111111-2222-3333-4444-555555555555"
    fake_microsoft["id_token"] = id_token(
        nonce, tid=other, iss=f"https://login.microsoftonline.com/{other}/v2.0",
        preferred_username="bob@otherschool.edu",
    )  # fmt: skip
    loc = finish(c, state).headers["location"]
    assert "Westchester+Community+College" in loc


def test_user_cancel_at_microsoft(db):
    r = client_for(db).get("/auth/microsoft/callback?error=access_denied", follow_redirects=False)
    assert "signin_error" in r.headers["location"]


def test_not_configured_is_503(db, monkeypatch):
    monkeypatch.setattr(ms, "settings", replace(config.settings, ms_client_id=""))
    assert client_for(db).get("/auth/microsoft/login", follow_redirects=False).status_code == 503
