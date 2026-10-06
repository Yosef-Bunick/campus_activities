from tests.conftest import client_for, make_user
from tests.test_events_api import at, body, rooms  # noqa: F401  (fixture)

WINDOW = {"start": at(0, 0).isoformat(), "end": at(3).isoformat()}


def titles(c, **params):
    return [e["title"] for e in c.get("/events", params={**WINDOW, **params}).json()]


def test_set_and_clear_major(db):
    c = client_for(db, make_user(db))
    keys = [m["key"] for m in c.get("/auth/majors").json()]
    assert "nursing" in keys
    assert c.put("/auth/me/major", json={"major": "nursing"}).json() == {"major": "nursing"}
    assert c.get("/auth/me").json()["user"]["major"] == "nursing"
    assert c.put("/auth/me/major", json={"major": "astrology"}).status_code == 400
    assert c.put("/auth/me/major", json={"major": None}).json() == {"major": None}


def test_event_majors_are_validated(db, rooms):  # noqa: F811
    c = client_for(db, make_user(db))
    assert c.post("/events", json=body(rooms["38"], majors=["nope"])).status_code == 422
    four = ["business", "nursing", "engineering", "visual_arts"]
    assert c.post("/events", json=body(rooms["38"], majors=four)).status_code == 422
    ev = c.post("/events", json=body(rooms["38"], majors=["nursing"])).json()[0]
    assert ev["majors"] == ["nursing"]


def test_recommended_is_main_events_or_my_major(db, rooms):  # noqa: F811
    sga = client_for(db, make_user(db, "student_gov"))
    sga.post("/events", json=body(rooms["38"], title="Convocation", type="main_event"))
    sga.post("/events", json=body(rooms["26"], title="Nursing study", majors=["nursing"]))
    sga.post("/events", json=body(rooms["108"], title="Coding night", majors=["computer_science"]))
    sga.post("/events", json=body(rooms["25D"], title="Board games"))

    me = client_for(db, make_user(db))
    assert titles(me, recommended=True) == ["Convocation"]  # no major yet: main events only
    me.put("/auth/me/major", json={"major": "nursing"})
    assert titles(me, recommended=True) == ["Convocation", "Nursing study"]
    assert len(titles(me)) == 4  # without the flag, everything


def test_majors_match_exactly_not_by_prefix(db, rooms):  # noqa: F811
    sga = client_for(db, make_user(db, "student_gov"))
    sga.post("/events", json=body(rooms["38"], title="Arts", majors=["liberal_arts", "visual_arts"]))
    me = client_for(db, make_user(db))
    me.put("/auth/me/major", json={"major": "visual_arts"})
    assert titles(me, recommended=True) == ["Arts"]
    me.put("/auth/me/major", json={"major": "business"})
    assert titles(me, recommended=True) == []


def test_edit_changes_majors(db, rooms):  # noqa: F811
    c = client_for(db, make_user(db))
    ev = c.post("/events", json=body(rooms["38"])).json()[0]
    r = c.patch(f"/events/{ev['id']}", json={"majors": ["business"]})
    assert r.json()["majors"] == ["business"]
