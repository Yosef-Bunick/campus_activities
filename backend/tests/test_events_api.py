from datetime import UTC, datetime, timedelta

import pytest

from app.models.event import Alert, Event
from app.seed import seed
from app.services.recurrence import NY
from tests.conftest import client_for, make_user


@pytest.fixture
def rooms(db):
    seed(db)
    from sqlmodel import select

    from app.models.place import Room

    return {r.name: r.id for r in db.exec(select(Room))}


def at(days: int, hour: int = 15) -> datetime:
    """New York `hour`:00, `days` from today, as UTC."""
    d = datetime.now(NY).date() + timedelta(days=days)
    return datetime(d.year, d.month, d.day, hour, tzinfo=NY).astimezone(UTC)


def body(room_id, days=1, hours=2, **kw):
    s = at(days)
    return {"title": "Study group", "type": "friend_event", "room_id": room_id,
            "starts_at": s.isoformat(), "ends_at": (s + timedelta(hours=hours)).isoformat(), **kw}  # fmt: skip


def test_seed_is_idempotent(db, rooms):
    assert seed(db) == 0
    assert set(rooms) == {"38", "26", "108", "25D"}


def test_student_posts_weekly_study_group(db, rooms):
    c = client_for(db, make_user(db))
    r = c.post("/events", json=body(rooms["38"], repeat={
        "freq": "weekly", "until": (datetime.now(NY).date() + timedelta(days=30)).isoformat()}))  # fmt: skip
    assert r.status_code == 201, r.text
    assert len(r.json()) >= 4
    assert len({e["series_id"] for e in r.json()}) == 1
    # Everyone sees it.
    other = client_for(db, make_user(db))
    found = other.get("/events", params={"start": at(0, 0).isoformat(), "end": at(40).isoformat()})
    assert len(found.json()) == len(r.json())
    assert found.json()[0]["room"]["name"] == "38"


def test_type_permission(db, rooms):
    c = client_for(db, make_user(db))
    assert c.post("/events", json=body(rooms["38"], type="main_event")).status_code == 403
    sga = client_for(db, make_user(db, "student_gov"))
    assert sga.post("/events", json=body(rooms["38"], type="main_event")).status_code == 201


def test_times_rules(db, rooms):
    c = client_for(db, make_user(db))
    assert c.post("/events", json=body(rooms["38"], hours=13)).status_code == 400
    assert c.post("/events", json=body(rooms["38"], hours=-1)).status_code == 400


def test_schedule_ahead_limit(db, rooms):
    student = client_for(db, make_user(db))
    r = student.post("/events", json=body(rooms["38"], days=100))
    assert r.status_code == 409 and "90 days" in r.json()["conflicts"][0]["reason"]
    sga = client_for(db, make_user(db, "student_gov"))
    assert sga.post("/events", json=body(rooms["38"], days=100)).status_code == 201


def test_series_until_past_limit_is_rejected(db, rooms):
    c = client_for(db, make_user(db))
    until = (datetime.now(NY).date() + timedelta(days=120)).isoformat()
    r = c.post("/events", json=body(rooms["38"], repeat={"freq": "weekly", "until": until}))
    assert r.status_code == 400


def test_student_cannot_double_book_self(db, rooms):
    c = client_for(db, make_user(db))
    assert c.post("/events", json=body(rooms["38"])).status_code == 201
    r = c.post("/events", json=body(rooms["26"]))
    assert r.status_code == 409 and "already have" in r.json()["conflicts"][0]["reason"]
    sga = client_for(db, make_user(db, "student_gov"))
    assert sga.post("/events", json=body(rooms["38"])).status_code == 201
    assert sga.post("/events", json=body(rooms["26"])).status_code == 201


def test_third_overlap_in_a_room_waits_for_approval(db, rooms):
    # Phase 2 (ADR-014): the 3rd overlapping event isn't blocked any more; it's
    # saved as pending_approval. Full flow in test_phase2.py.
    for _ in range(2):
        assert client_for(db, make_user(db)).post("/events", json=body(rooms["108"])).status_code == 201
    r = client_for(db, make_user(db)).post("/events", json=body(rooms["108"]))
    assert r.status_code == 201 and r.json()[0]["status"] == "pending_approval"


def test_conflicting_dates_can_be_skipped(db, rooms):
    me = make_user(db)
    c = client_for(db, me)
    c.post("/events", json=body(rooms["26"], days=3))  # I'm already busy three days from now
    until = (datetime.now(NY).date() + timedelta(days=5)).isoformat()
    req = body(rooms["108"], days=1, repeat={"freq": "daily", "until": until})
    r = c.post("/events", json=req)
    assert r.status_code == 409
    bad = [x["date"] for x in r.json()["conflicts"]]
    assert len(bad) == 1
    r = c.post("/events", json={**req, "skip_dates": bad})
    assert r.status_code == 201 and len(r.json()) == 4


def test_daily_cap(db, rooms):
    c = client_for(db, make_user(db))
    for i in range(10):
        assert c.post("/events", json=body(rooms["25D"], days=1 + i)).status_code == 201
    assert c.post("/events", json=body(rooms["25D"], days=20)).status_code == 429


def test_edit_own_event(db, rooms):
    c = client_for(db, make_user(db))
    ev = c.post("/events", json=body(rooms["38"])).json()[0]
    r = c.patch(f"/events/{ev['id']}", json={"title": "Renamed", "room_id": rooms["26"]})
    assert r.status_code == 200 and r.json()["title"] == "Renamed" and r.json()["room"]["name"] == "26"
    other = client_for(db, make_user(db))
    assert other.patch(f"/events/{ev['id']}", json={"title": "x"}).status_code == 403


def test_cancel_scopes(db, rooms):
    c = client_for(db, make_user(db))
    until = (datetime.now(NY).date() + timedelta(days=4)).isoformat()
    evs = c.post("/events", json=body(rooms["38"], repeat={"freq": "daily", "until": until})).json()
    assert len(evs) == 4
    assert c.post(f"/events/{evs[0]['id']}/cancel", json={"scope": "this"}).json()["cancelled"] == 1
    assert c.post(f"/events/{evs[2]['id']}/cancel", json={"scope": "future"}).json()["cancelled"] == 2
    statuses = [db.get(Event, e["id"]).status for e in evs]
    assert statuses == ["cancelled", "active", "cancelled", "cancelled"]
    assert c.post(f"/events/{evs[1]['id']}/cancel", json={"scope": "series"}).json()["cancelled"] == 1


def test_cancelled_events_stay_visible_until_they_end(db, rooms):
    c = client_for(db, make_user(db))
    ev = c.post("/events", json=body(rooms["38"])).json()[0]
    c.post(f"/events/{ev['id']}/cancel", json={})
    listed = c.get("/events", params={"start": at(0, 0).isoformat(), "end": at(3).isoformat()}).json()
    assert listed[0]["status"] == "cancelled"


def test_only_creator_or_cancel_any(db, rooms):
    owner_of_event = make_user(db)
    ev = client_for(db, owner_of_event).post("/events", json=body(rooms["38"])).json()[0]
    assert client_for(db, make_user(db)).post(f"/events/{ev['id']}/cancel", json={}).status_code == 403
    sga = client_for(db, make_user(db, "student_gov"))
    assert sga.post(f"/events/{ev['id']}/cancel", json={"reason": "Room closed"}).status_code == 200
    from sqlmodel import select

    alert = db.exec(select(Alert).where(Alert.user_id == owner_of_event.id)).one()
    assert "Room closed" in alert.message


def test_ban_cancels_upcoming_events(db, rooms):
    student = make_user(db)
    ev = client_for(db, student).post("/events", json=body(rooms["38"])).json()[0]
    manager = client_for(db, make_user(db, "manager"))
    assert manager.post(f"/users/{student.id}/ban").json()["events_cancelled"] == 1
    assert db.get(Event, ev["id"]).status == "cancelled"


def test_filter_by_type_room_search_and_now(db, rooms):
    c = client_for(db, make_user(db, "student_gov"))
    c.post("/events", json=body(rooms["38"], title="Chess club", type="club_event"))
    c.post("/events", json=body(rooms["26"], title="Movie night"))
    window = {"start": at(0, 0).isoformat(), "end": at(3).isoformat()}
    get = lambda **p: [e["title"] for e in c.get("/events", params={**window, **p}).json()]  # noqa: E731
    assert get(types=["club_event"]) == ["Chess club"]
    assert get(room_ids=[rooms["26"]]) == ["Movie night"]
    assert get(search="chess") == ["Chess club"]
    assert c.get("/events", params={"happening_now": True}).json() == []


def test_events_require_sign_in(db):
    assert client_for(db).get("/events").status_code == 401
