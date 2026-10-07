"""Off-campus and online events (ADR-032), and majors from a plain text file."""

import os
import time

from app.core import majors
from tests.conftest import client_for, make_user
from tests.test_events_api import at, body, rooms  # noqa: F401  (fixture)

WINDOW = {"start": at(0, 0).isoformat(), "end": at(3).isoformat()}


def off_campus(**kw):
    b = body(None, location_kind="off_campus", location="Kensico Dam Plaza", **kw)
    b.pop("room_id")
    return b


def online(**kw):
    b = body(None, location_kind="online", online_url="https://zoom.us/j/123", **kw)
    b.pop("room_id")
    return b


# ── Off campus / online ──


def test_off_campus_and_online_events(db, rooms):  # noqa: F811
    c = client_for(db, make_user(db, "student_gov"))
    a = c.post("/events", json=off_campus(title="Hike")).json()[0]
    b = c.post("/events", json=online(title="Study call")).json()[0]
    assert a["location_kind"] == "off_campus" and a["location"] == "Kensico Dam Plaza" and a["room"] is None
    assert b["location_kind"] == "online" and b["online_url"] == "https://zoom.us/j/123"


def test_each_kind_needs_its_own_detail(db, rooms):  # noqa: F811
    c = client_for(db, make_user(db))
    assert c.post("/events", json={**off_campus(), "location": " "}).status_code == 422
    assert c.post("/events", json={**online(), "online_url": "javascript:alert(1)"}).status_code == 422
    assert c.post("/events", json={**online(), "online_url": "zoom.us/j/1"}).status_code == 422
    no_room = body(rooms["38"])
    no_room.pop("room_id")
    assert c.post("/events", json=no_room).status_code == 422


def test_room_limit_only_applies_on_campus(db, rooms):  # noqa: F811
    for _ in range(4):  # many off-campus events at once: no room, no limit
        r = client_for(db, make_user(db)).post("/events", json=off_campus())
        assert r.json()[0]["status"] == "active"


def test_you_still_cant_double_book_yourself_online(db, rooms):  # noqa: F811
    c = client_for(db, make_user(db))
    assert c.post("/events", json=body(rooms["38"])).status_code == 201
    r = c.post("/events", json=online())
    assert r.status_code == 409 and "already have" in r.json()["conflicts"][0]["reason"]


def test_filter_by_where(db, rooms):  # noqa: F811
    c = client_for(db, make_user(db, "student_gov"))
    c.post("/events", json=body(rooms["38"], title="Campus"))
    c.post("/events", json=off_campus(title="Off"))
    c.post("/events", json=online(title="Web"))
    titles = lambda **p: sorted(e["title"] for e in c.get("/events", params={**WINDOW, **p}).json())  # noqa: E731
    assert titles() == ["Campus", "Off", "Web"]
    assert titles(where=["online", "off_campus"]) == ["Off", "Web"]
    assert titles(where=["campus"]) == ["Campus"]


def test_edit_moves_an_event_online(db, rooms):  # noqa: F811
    c = client_for(db, make_user(db))
    ev = c.post("/events", json=body(rooms["38"])).json()[0]
    r = c.patch(f"/events/{ev['id']}", json={"location_kind": "online", "online_url": "https://meet.google.com/x"})
    assert r.status_code == 200
    assert r.json()["location_kind"] == "online" and r.json()["room"] is None
    assert c.patch(f"/events/{ev['id']}", json={"location_kind": "off_campus"}).status_code == 400


def test_recurring_online_series_and_extend(db, rooms):  # noqa: F811
    from datetime import datetime, timedelta

    from app.services.recurrence import NY

    c = client_for(db, make_user(db))
    until = (datetime.now(NY).date() + timedelta(days=14)).isoformat()
    evs = c.post("/events", json=online(repeat={"freq": "weekly", "until": until})).json()
    more = c.post(f"/series/{evs[0]['series_id']}/extend", json={}).json()
    assert more and all(e["location_kind"] == "online" for e in more)


# ── Majors file ──


def test_majors_come_from_the_text_file(db, tmp_path, monkeypatch):
    f = tmp_path / "majors.txt"
    f.write_text("# comment\nNursing\n\nComputer Science\nNursing\n", encoding="utf-8")
    monkeypatch.setattr(majors, "MAJORS_FILE", f)
    assert majors.majors() == {"nursing": "Nursing", "computer_science": "Computer Science"}
    # Adding a line is picked up without a restart.
    time.sleep(0.01)
    f.write_text("Nursing\nComputer Science\nRadiologic Technology\n", encoding="utf-8")
    os.utime(f, (time.time() + 5, time.time() + 5))
    keys = [m["key"] for m in client_for(db, make_user(db)).get("/auth/majors").json()]
    assert keys == ["nursing", "computer_science", "radiologic_technology"]


def test_new_users_are_asked_for_their_major(db):
    c = client_for(db, make_user(db))
    assert c.get("/auth/me").json()["needs_major"] is True
    c.put("/auth/me/major", json={"major": "nursing"})
    me = c.get("/auth/me").json()
    assert me["needs_major"] is False and me["user"]["major_label"] == "Nursing"


def test_removed_major_asks_again(db, tmp_path, monkeypatch):
    c = client_for(db, make_user(db))
    c.put("/auth/me/major", json={"major": "nursing"})
    f = tmp_path / "majors.txt"
    f.write_text("Computer Science\n", encoding="utf-8")
    monkeypatch.setattr(majors, "MAJORS_FILE", f)
    assert c.get("/auth/me").json()["needs_major"] is True


# ── Shared links: one event ──


def test_get_one_event_for_a_shared_link(db, rooms):  # noqa: F811
    creator = client_for(db, make_user(db))
    ev = creator.post("/events", json=body(rooms["38"], title="Shared")).json()[0]
    other = client_for(db, make_user(db))
    assert other.get(f"/events/{ev['id']}").json()["title"] == "Shared"
    assert other.get("/events/999999").status_code == 404
    assert client_for(db).get(f"/events/{ev['id']}").status_code == 401  # signed out


def test_pending_event_link_only_works_for_its_creator(db, rooms):  # noqa: F811
    for _ in range(2):
        client_for(db, make_user(db)).post("/events", json=body(rooms["108"]))
    creator = client_for(db, make_user(db))
    ev = creator.post("/events", json=body(rooms["108"])).json()[0]
    assert ev["status"] == "pending_approval"
    assert creator.get(f"/events/{ev['id']}").status_code == 200
    assert client_for(db, make_user(db)).get(f"/events/{ev['id']}").status_code == 404
