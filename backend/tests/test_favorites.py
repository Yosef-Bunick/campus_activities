from datetime import datetime, timedelta

from app.models.event import Event
from app.services.recurrence import NY
from tests.conftest import client_for, make_user
from tests.test_events_api import body, rooms  # noqa: F401  (fixture)


def test_save_one_event_then_unsave(db, rooms):  # noqa: F811
    me = client_for(db, make_user(db))
    ev = client_for(db, make_user(db)).post("/events", json=body(rooms["38"])).json()[0]
    assert me.post(f"/events/{ev['id']}/save", json={}).status_code == 200
    fav = me.get("/favorites").json()
    assert [e["id"] for e in fav["saved"]] == [ev["id"]]
    assert fav["saved"][0]["saved"] == "event"
    me.post(f"/events/{ev['id']}/unsave")
    assert me.get("/favorites").json()["saved"] == []


def test_save_whole_series(db, rooms):  # noqa: F811
    until = (datetime.now(NY).date() + timedelta(days=3)).isoformat()
    evs = client_for(db, make_user(db)).post(
        "/events", json=body(rooms["38"], repeat={"freq": "daily", "until": until})
    ).json()
    me = client_for(db, make_user(db))
    me.post(f"/events/{evs[1]['id']}/save", json={"scope": "series"})
    saved = me.get("/favorites").json()["saved"]
    assert len(saved) == len(evs) and {e["saved"] for e in saved} == {"series"}
    # Unsaving any date clears the series star.
    me.post(f"/events/{evs[0]['id']}/unsave")
    assert me.get("/favorites").json()["saved"] == []


def test_favorite_a_person_shows_all_their_events(db, rooms):  # noqa: F811
    poster = make_user(db, "student_gov")
    c = client_for(db, poster)
    c.post("/events", json=body(rooms["38"], title="A"))
    c.post("/events", json=body(rooms["26"], title="B", days=2))
    me_user = make_user(db)
    me = client_for(db, me_user)
    assert me.get(f"/users/{poster.id}").json()["is_favorite"] is False
    me.post(f"/users/{poster.id}/favorite")
    fav = me.get("/favorites").json()
    assert [e["title"] for e in fav["from_people"]] == ["A", "B"]
    assert [p["id"] for p in fav["people"]] == [poster.id]
    assert me.get(f"/users/{poster.id}").json()["is_favorite"] is True
    me.post(f"/users/{poster.id}/unfavorite")
    assert me.get("/favorites").json()["people"] == []


def test_cannot_favorite_yourself(db):
    user = make_user(db)
    assert client_for(db, user).post(f"/users/{user.id}/favorite").status_code == 400


def test_events_list_carries_saved_flag_and_room_position(db, rooms):  # noqa: F811
    me = client_for(db, make_user(db))
    ev = me.post("/events", json=body(rooms["38"])).json()[0]
    assert ev["saved"] is None and ev["room"]["map_x"] == 0.6805
    me.post(f"/events/{ev['id']}/save", json={})
    listed = me.get("/events", params={"end": (datetime.now(NY) + timedelta(days=3)).isoformat()})
    assert listed.json()[0]["saved"] == "event"


def test_going_lists_events_i_rsvpd_to(db, rooms):  # noqa: F811
    me = client_for(db, make_user(db))
    ev = client_for(db, make_user(db)).post("/events", json=body(rooms["38"])).json()[0]
    assert me.get("/favorites").json()["going"] == []
    me.post(f"/events/{ev['id']}/going")
    going = me.get("/favorites").json()["going"]
    assert [e["id"] for e in going] == [ev["id"]] and going[0]["going"] is True
    me.post(f"/events/{ev['id']}/not-going")
    assert me.get("/favorites").json()["going"] == []


def test_mine_lists_my_events_including_pending(db, rooms):  # noqa: F811
    creator = make_user(db)
    me = client_for(db, creator)
    a = me.post("/events", json=body(rooms["38"], title="A")).json()[0]
    b = me.post("/events", json=body(rooms["26"], title="B", days=2)).json()[0]
    gone = me.post("/events", json=body(rooms["26"], title="R", days=3)).json()[0]
    for ev_id, status in ((b["id"], "pending_approval"), (gone["id"], "rejected")):
        row = db.get(Event, ev_id)
        row.status = status
        db.add(row)
    db.commit()
    mine = me.get("/favorites").json()["mine"]
    assert [(e["id"], e["status"]) for e in mine] == [(a["id"], "active"), (b["id"], "pending_approval")]
    # Someone else never sees my events in their "mine".
    assert client_for(db, make_user(db)).get("/favorites").json()["mine"] == []
