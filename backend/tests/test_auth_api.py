from datetime import UTC, datetime, timedelta

from tests.conftest import client_for, make_user

from app.models.user import BannedAccount
from app.services.accounts import account_hash


def test_me_requires_sign_in(db):
    assert client_for(db).get("/auth/me").status_code == 401


def test_me_returns_role_permissions_limits_and_csrf(db):
    c = client_for(db, make_user(db, "student_gov"))
    body = c.get("/auth/me").json()
    assert body["user"]["role"] == "student_gov"
    assert "event.approve_overlap" in body["permissions"]
    assert "user.ban" not in body["permissions"]
    assert body["limits"]["max_days_ahead"] == 365
    assert body["csrf_token"] == "t" * 64


def test_logout_revokes_the_session(db):
    c = client_for(db, make_user(db))
    assert c.post("/auth/logout").status_code == 200
    assert c.get("/auth/me").status_code == 401


# ── CSRF ──


def test_write_without_csrf_header_is_rejected(db):
    c = client_for(db, make_user(db))
    del c.headers["X-CSRF-Token"]
    assert c.post("/auth/logout").status_code == 403


def test_write_with_wrong_csrf_header_is_rejected(db):
    c = client_for(db, make_user(db))
    c.headers["X-CSRF-Token"] = "x" * 64
    assert c.post("/auth/logout").status_code == 403


def test_write_with_session_but_no_csrf_cookie_fails_closed(db):
    c = client_for(db, make_user(db))
    c.cookies.delete("csrf_token")
    assert c.post("/auth/logout").status_code == 403


def test_write_from_foreign_origin_is_rejected(db):
    c = client_for(db, make_user(db))
    r = c.post("/auth/logout", headers={"Origin": "https://evil.example"})
    assert r.status_code == 403


def test_write_from_frontend_origin_passes(db):
    c = client_for(db, make_user(db))
    r = c.post("/auth/logout", headers={"Origin": "http://localhost:5173"})
    assert r.status_code == 200


# ── last_active_at ──


def test_last_active_is_stamped_at_most_hourly(db):
    user = make_user(db)
    c = client_for(db, user)
    recent = datetime.now(UTC) - timedelta(minutes=10)
    user.last_active_at = recent
    db.add(user)
    db.commit()
    c.get("/auth/me")
    db.refresh(user)
    assert user.last_active_at.replace(tzinfo=UTC) == recent  # untouched

    user.last_active_at = datetime.now(UTC) - timedelta(hours=2)
    db.add(user)
    db.commit()
    c.get("/auth/me")
    db.refresh(user)
    assert datetime.now(UTC) - user.last_active_at.replace(tzinfo=UTC) < timedelta(minutes=1)


# ── hierarchy: ban + change role ──


def test_manager_bans_student(db):
    student = make_user(db)
    student_client = client_for(db, student)
    manager = client_for(db, make_user(db, "manager"))

    assert manager.post(f"/users/{student.id}/ban").status_code == 200
    # Sessions revoked, account hash stored.
    assert student_client.get("/auth/me").status_code == 401
    assert db.get(BannedAccount, account_hash(student.ms_tenant_id, student.ms_object_id))
    db.refresh(student)
    assert student.is_banned

    assert manager.post(f"/users/{student.id}/unban").status_code == 200
    assert db.get(BannedAccount, account_hash(student.ms_tenant_id, student.ms_object_id)) is None


def test_sga_cannot_ban(db):
    student = make_user(db)
    sga = client_for(db, make_user(db, "student_gov"))
    assert sga.post(f"/users/{student.id}/ban").status_code == 403


def test_manager_cannot_ban_a_peer_or_the_owner(db):
    manager = client_for(db, make_user(db, "manager"))
    peer = make_user(db, "manager")
    owner = make_user(db, "owner")
    assert manager.post(f"/users/{peer.id}/ban").status_code == 403
    assert manager.post(f"/users/{owner.id}/ban").status_code == 403


def test_manager_can_promote_to_sga_but_not_to_manager(db):
    student = make_user(db)
    manager = client_for(db, make_user(db, "manager"))
    assert manager.put(f"/users/{student.id}/role", json={"role": "student_gov"}).status_code == 200
    assert manager.put(f"/users/{student.id}/role", json={"role": "manager"}).status_code == 403


def test_only_owner_creates_managers(db):
    student = make_user(db)
    owner = client_for(db, make_user(db, "owner"))
    r = owner.put(f"/users/{student.id}/role", json={"role": "manager"})
    assert r.status_code == 200
    db.refresh(student)
    assert student.role == "manager"


def test_person_sheet_shows_only_allowed_buttons(db):
    student = make_user(db)
    manager_user = make_user(db, "manager")
    as_manager = client_for(db, manager_user).get(f"/users/{student.id}").json()
    assert as_manager["actions"] == {"favorite": True, "hide": True, "ban": True, "change_role": True}
    assert as_manager["assignable_roles"] == ["student_gov", "security", "student"]

    as_student = client_for(db, make_user(db)).get(f"/users/{manager_user.id}").json()
    assert as_student["actions"]["ban"] is False
    assert as_student["actions"]["change_role"] is False
    assert as_student["assignable_roles"] == []
