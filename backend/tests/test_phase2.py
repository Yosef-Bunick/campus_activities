"""Phase 2: room approval, room limits, reports + flags, moderation log,
inactivity purge, delete my account, terms note, extend series."""

from datetime import UTC, datetime, timedelta

from sqlmodel import select

from app.core.terms import TERMS_VERSION
from app.models.event import Alert, Event
from app.models.moderation import ModerationLog
from app.models.social import UserFavorite
from app.models.user import BannedAccount, User
from app.services.accounts import account_hash
from app.services.purge import purge_inactive
from app.services.recurrence import NY
from tests.conftest import client_for, make_user
from tests.test_events_api import at, body, rooms  # noqa: F401  (fixture)

WINDOW = {"start": at(0, 0).isoformat(), "end": at(120).isoformat()}


def fill_108(db, rooms, days=1):  # noqa: F811
    for _ in range(2):
        client_for(db, make_user(db)).post("/events", json=body(rooms["108"], days=days))


def alerts_of(db, user, kind):
    return list(db.exec(select(Alert).where(Alert.user_id == user.id, Alert.kind == kind)))


# ── Room approval ──


def test_pending_event_flow_approve(db, rooms):  # noqa: F811
    sga, owner, bystander = make_user(db, "student_gov"), make_user(db, "owner"), make_user(db)
    fill_108(db, rooms)
    creator = make_user(db)
    cc = client_for(db, creator)
    ev = cc.post("/events", json=body(rooms["108"], title="Third")).json()[0]
    assert ev["status"] == "pending_approval"

    # Only the creator sees it while pending; SGA and owner get an alert.
    assert "Third" in [e["title"] for e in cc.get("/events", params=WINDOW).json()]
    assert "Third" not in [e["title"] for e in client_for(db, bystander).get("/events", params=WINDOW).json()]
    assert len(alerts_of(db, sga, "approval_needed")) == 1
    assert len(alerts_of(db, owner, "approval_needed")) == 1
    assert alerts_of(db, bystander, "approval_needed") == []

    # A student can't approve; SGA can.
    assert client_for(db, bystander).post(f"/events/{ev['id']}/approve", json={}).status_code == 403
    assert client_for(db, sga).post(f"/events/{ev['id']}/approve", json={}).json() == {"updated": 1}
    assert db.get(Event, ev["id"]).status == "active"
    assert "approved" in alerts_of(db, creator, "event_approved")[0].message
    # Deciding twice is refused; the alert page shows the decision.
    assert client_for(db, sga).post(f"/events/{ev['id']}/reject", json={}).status_code == 409
    sga_alerts = client_for(db, sga).get("/alerts").json()["alerts"]
    assert sga_alerts[0]["event_status"] == "active"


def test_reject_a_pending_series(db, rooms):  # noqa: F811
    sga = make_user(db, "student_gov")
    for d in (1, 2):
        fill_108(db, rooms, days=d)
    creator = make_user(db)
    until = (datetime.now(NY).date() + timedelta(days=2)).isoformat()
    evs = client_for(db, creator).post(
        "/events", json=body(rooms["108"], repeat={"freq": "daily", "until": until})
    ).json()
    assert [e["status"] for e in evs] == ["pending_approval", "pending_approval"]
    assert len(alerts_of(db, sga, "approval_needed")) == 1  # one alert per request, not per date
    r = client_for(db, sga).post(f"/events/{evs[0]['id']}/reject", json={"reason": "Too busy"})
    assert r.json() == {"updated": 2}
    assert "Too busy" in alerts_of(db, creator, "event_rejected")[0].message


def test_room_limit_can_be_raised_by_managers(db, rooms):  # noqa: F811
    student = client_for(db, make_user(db))
    assert student.patch(f"/rooms/{rooms['108']}", json={"max_overlapping": 5}).status_code == 403
    manager = client_for(db, make_user(db, "manager"))
    r = manager.patch(f"/rooms/{rooms['108']}", json={"max_overlapping": 5})
    assert r.json()["max_overlapping"] == 5
    fill_108(db, rooms)
    third = client_for(db, make_user(db)).post("/events", json=body(rooms["108"])).json()[0]
    assert third["status"] == "active"
    assert db.exec(select(ModerationLog).where(ModerationLog.action == "room_limit")).first()


# ── Reports, flags, moderation log ──


def test_reports_flag_managers_at_three(db, rooms):  # noqa: F811
    manager = make_user(db, "manager")
    creator = make_user(db)
    ev = client_for(db, creator).post("/events", json=body(rooms["38"], title="Sketchy")).json()[0]
    assert client_for(db, creator).post(f"/events/{ev['id']}/report", json={}).status_code == 400
    reporters = [client_for(db, make_user(db)) for _ in range(3)]
    for i, r in enumerate(reporters):
        assert r.post(f"/events/{ev['id']}/report", json={"reason": "spam"}).json()["already"] is False
        flags = alerts_of(db, manager, "abuse_flag")
        assert len(flags) == (1 if i == 2 else 0)
    assert reporters[0].post(f"/events/{ev['id']}/report", json={}).json()["already"] is True
    flag = alerts_of(db, manager, "abuse_flag")[0]
    assert flag.subject_user_id == creator.id and "Sketchy" in flag.message


def test_repeated_daily_cap_hits_flag_once(db, rooms):  # noqa: F811
    manager = make_user(db, "manager")
    c = client_for(db, make_user(db))
    for i in range(10):
        c.post("/events", json=body(rooms["25D"], days=1 + i))
    for _ in range(4):
        assert c.post("/events", json=body(rooms["25D"], days=30)).status_code == 429
    assert len(alerts_of(db, manager, "abuse_flag")) == 1  # at the 3rd hit, not again at the 4th


def test_moderation_log_records_actions_and_is_restricted(db, rooms):  # noqa: F811
    manager_user = make_user(db, "manager")
    manager = client_for(db, manager_user)
    target = make_user(db)
    manager.put(f"/users/{target.id}/role", json={"role": "security"})
    manager.post(f"/users/{target.id}/ban")
    log = client_for(db, make_user(db, "security")).get("/modlog").json()
    assert [e["action"] for e in log][:2] == ["ban", "change_role"]
    assert log[0]["actor"] == manager_user.display_name
    assert client_for(db, make_user(db)).get("/modlog").status_code == 403
    assert client_for(db, make_user(db, "student_gov")).get("/modlog").status_code == 403


def test_cancelling_someone_elses_event_is_logged(db, rooms):  # noqa: F811
    ev = client_for(db, make_user(db)).post("/events", json=body(rooms["38"])).json()[0]
    client_for(db, make_user(db, "student_gov")).post(f"/events/{ev['id']}/cancel", json={"reason": "x"})
    assert db.exec(select(ModerationLog).where(ModerationLog.action == "cancel_event")).first()


# ── Purge + delete my account ──


def test_inactivity_purge_deletes_everything_but_keeps_bans_and_the_owner(db, rooms):  # noqa: F811
    owner, stale, friend = make_user(db, "owner"), make_user(db), make_user(db)
    client_for(db, stale).post("/events", json=body(rooms["38"], title="Old"))
    client_for(db, friend).post(f"/users/{stale.id}/favorite")
    client_for(db, make_user(db, "manager")).post(f"/users/{stale.id}/ban")
    long_ago = datetime.now(UTC) - timedelta(days=151)
    for u in (owner, stale):
        u.last_active_at = long_ago
        db.add(u)
    db.commit()
    stale_id, ban_hash = stale.id, account_hash(stale.ms_tenant_id, stale.ms_object_id)

    assert purge_inactive(db) == 1
    db.expire_all()
    assert db.get(User, stale_id) is None
    assert db.get(User, owner.id) is not None  # owner is never purged
    assert db.exec(select(Event).where(Event.creator_id == stale_id)).first() is None
    assert db.exec(select(UserFavorite).where(UserFavorite.favorite_user_id == stale_id)).first() is None
    assert db.get(BannedAccount, ban_hash) is not None  # the ban survives
    log = client_for(db, make_user(db, "manager")).get("/modlog").json()
    assert any(e["action"] == "ban" for e in log)  # log text kept


def test_delete_my_account(db, rooms):  # noqa: F811
    me = make_user(db)
    my_id = me.id
    c = client_for(db, me)
    c.post("/events", json=body(rooms["38"]))
    assert c.post("/auth/me/delete", json={"confirm": "yes"}).status_code == 400
    assert c.post("/auth/me/delete", json={"confirm": "DELETE"}).json() == {"deleted": True}
    db.expire_all()
    assert db.get(User, my_id) is None
    assert c.get("/auth/me").status_code == 401


def test_worker_run_once(db):
    from app import worker

    stale = make_user(db)
    stale.last_active_at = datetime.now(UTC) - timedelta(days=200)
    db.add(stale)
    db.commit()
    assert worker.run_once() == 1


# ── Terms note ──


def test_terms_shown_until_accepted(db):
    c = client_for(db, make_user(db))
    terms = c.get("/auth/me").json()["terms"]
    assert terms["version"] == TERMS_VERSION and len(terms["items"]) >= 3
    assert c.post("/auth/me/accept-terms", json={"version": TERMS_VERSION + 1}).status_code == 409
    assert c.post("/auth/me/accept-terms", json={"version": TERMS_VERSION}).status_code == 200
    assert c.get("/auth/me").json()["terms"] is None


# ── Extend series ──


def test_extend_series_up_to_the_limit(db, rooms):  # noqa: F811
    me = make_user(db)
    c = client_for(db, me)
    until = (datetime.now(NY).date() + timedelta(days=14)).isoformat()
    evs = c.post("/events", json=body(rooms["38"], repeat={"freq": "weekly", "until": until})).json()
    sid = evs[0]["series_id"]
    assert evs[0]["series_ends_on"] == until
    assert client_for(db, make_user(db)).post(f"/series/{sid}/extend", json={}).status_code == 403
    more = c.post(f"/series/{sid}/extend", json={}).json()
    assert len(more) >= 10  # student limit is 90 days: about 13 weeks in total
    last = max(datetime.fromisoformat(e["starts_at"]) for e in more).astimezone(NY).date()
    assert last <= datetime.now(NY).date() + timedelta(days=90)
    assert c.post(f"/series/{sid}/extend", json={}).status_code == 400  # already at the limit
