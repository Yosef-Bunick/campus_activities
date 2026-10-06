from dataclasses import replace

import pytest

from app.routers import dev_auth
from tests.conftest import client_for


@pytest.fixture
def enabled(monkeypatch):
    monkeypatch.setattr(dev_auth, "settings", replace(dev_auth.settings, dev_login_flag=True))


def test_off_by_default(db):
    c = client_for(db)
    assert c.get("/auth/config").json()["dev_login"] is False
    assert c.post("/auth/dev-login", json={"email": "a@my.sunywcc.edu"}).status_code == 404


def test_never_on_an_https_frontend(db, monkeypatch):
    s = replace(dev_auth.settings, dev_login_flag=True, frontend_origin="https://app.example.edu")
    monkeypatch.setattr(dev_auth, "settings", s)
    assert client_for(db).post("/auth/dev-login", json={"email": "a@my.sunywcc.edu"}).status_code == 404


def test_signs_in_with_chosen_role(db, enabled):
    c = client_for(db)
    r = c.post("/auth/dev-login", json={"email": "a@my.sunywcc.edu", "role": "manager"})
    assert r.status_code == 200
    me = c.get("/auth/me").json()
    assert me["user"]["role"] == "manager" and me["user"]["email"] == "a@my.sunywcc.edu"


def test_still_gated_to_school_domains(db, enabled):
    r = client_for(db).post("/auth/dev-login", json={"email": "a@fakesunywcc.edu"})
    assert r.status_code == 403


def test_stale_session_cookie_does_not_block_signing_in(db, enabled):
    c = client_for(db)
    c.cookies.set("session", "stale-token-from-a-reset-db")
    assert c.post("/auth/dev-login", json={"email": "a@my.sunywcc.edu"}).status_code == 200
    assert c.get("/auth/me").status_code == 200


def test_logout_from_the_app_origin_works_without_a_token(db):
    from tests.conftest import make_user

    c = client_for(db, make_user(db))
    del c.headers["X-CSRF-Token"]
    assert c.post("/auth/logout", headers={"Origin": "http://localhost:5173"}).status_code == 200
    assert c.get("/auth/me").status_code == 401
