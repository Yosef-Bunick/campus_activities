from datetime import datetime, timedelta

from app.services.recurrence import NY
from tests.conftest import client_for, make_user
from tests.test_events_api import at, body, rooms  # noqa: F401  (fixture)

WINDOW = {"start": at(0, 0).isoformat(), "end": at(10).isoformat()}


def titles(c):
    return [e["title"] for e in c.get("/events", params=WINDOW).json()]


def test_hide_a_person_removes_all_their_events(db, rooms):  # noqa: F811
    poster = make_user(db, "student_gov")
    pc = client_for(db, poster)
    pc.post("/events", json=body(rooms["38"], title="A"))
    pc.post("/events", json=body(rooms["26"], title="B"))
    client_for(db, make_user(db)).post("/events", json=body(rooms["108"], title="Other"))
    me = client_for(db, make_user(db))
    me.post(f"/users/{poster.id}/hide")
    assert titles(me) == ["Other"]
    assert me.get(f"/users/{poster.id}").json()["is_hidden"] is True
    assert [p["id"] for p in me.get("/hidden").json()["people"]] == [poster.id]
    me.post(f"/users/{poster.id}/unhide")
    assert len(titles(me)) == 3


def test_hide_one_event_or_whole_series(db, rooms):  # noqa: F811
    until = (datetime.now(NY).date() + timedelta(days=3)).isoformat()
    evs = client_for(db, make_user(db)).post(
        "/events", json=body(rooms["38"], title="Daily", repeat={"freq": "daily", "until": until})
    ).json()
    me = client_for(db, make_user(db))
    me.post(f"/events/{evs[0]['id']}/hide", json={})
    assert titles(me) == ["Daily"] * (len(evs) - 1)
    me.post(f"/events/{evs[1]['id']}/hide", json={"scope": "series"})
    assert titles(me) == []
    hidden = me.get("/hidden").json()["events"]
    assert sorted(h["hidden"] for h in hidden) == ["event", "series"]
    # Unhide any date clears both its own row and its series row.
    me.post(f"/events/{evs[0]['id']}/unhide")
    assert len(titles(me)) == len(evs)


def test_hidden_only_affects_the_person_who_hid(db, rooms):  # noqa: F811
    ev = client_for(db, make_user(db)).post("/events", json=body(rooms["38"])).json()[0]
    me, other = client_for(db, make_user(db)), client_for(db, make_user(db))
    me.post(f"/events/{ev['id']}/hide", json={})
    assert titles(me) == [] and len(titles(other)) == 1


def test_cannot_hide_yourself(db):
    user = make_user(db)
    assert client_for(db, user).post(f"/users/{user.id}/hide").status_code == 400


def test_alerts_list_and_read_state(db, rooms):  # noqa: F811
    creator = make_user(db)
    cc = client_for(db, creator)
    ev = cc.post("/events", json=body(rooms["38"], title="Jam")).json()[0]
    sga = client_for(db, make_user(db, "student_gov"))
    sga.post(f"/events/{ev['id']}/cancel", json={"reason": "Room closed"})

    assert cc.get("/alerts/unread").json() == {"unread": 1}
    alerts = cc.get("/alerts").json()
    assert alerts["unread"] == 1 and "Room closed" in alerts["alerts"][0]["message"]
    alert_id = alerts["alerts"][0]["id"]
    assert sga.post(f"/alerts/{alert_id}/read").status_code == 404  # not theirs
    assert cc.post(f"/alerts/{alert_id}/read").json() == {"unread": 0}
    assert cc.get("/alerts").json()["alerts"][0]["read"] is True


def test_read_all(db, rooms):  # noqa: F811
    creator = make_user(db)
    cc = client_for(db, creator)
    sga = client_for(db, make_user(db, "student_gov"))
    for d in (1, 2):
        ev = cc.post("/events", json=body(rooms["38"], days=d)).json()[0]
        sga.post(f"/events/{ev['id']}/cancel", json={})
    assert cc.get("/alerts/unread").json()["unread"] == 2
    assert cc.post("/alerts/read-all").json() == {"unread": 0}
