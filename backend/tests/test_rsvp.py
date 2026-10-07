"""RSVPs (ADR-035): "I'm going" + a live count on every event."""

from datetime import timedelta

from sqlmodel import select

from app.models.event import Event
from app.models.social import Rsvp
from app.services.purge import delete_user
from tests.conftest import client_for, make_user
from tests.test_events_api import at, body, rooms  # noqa: F401  (fixture)


def _post(db, rooms, **kw):  # noqa: F811
    return client_for(db, make_user(db)).post("/events", json=body(rooms["38"], **kw)).json()[0]


def _get(c, ev_id):
    return c.get(f"/events/{ev_id}").json()


def test_going_is_idempotent_and_counts_across_users(db, rooms):  # noqa: F811
    ev = _post(db, rooms)
    assert ev["going_count"] == 0 and ev["going"] is False
    a, b = client_for(db, make_user(db)), client_for(db, make_user(db))
    for _ in range(2):  # twice: still one RSVP
        assert a.post(f"/events/{ev['id']}/going").status_code == 200
    b.post(f"/events/{ev['id']}/going")
    assert _get(a, ev["id"])["going_count"] == 2
    a.post(f"/events/{ev['id']}/not-going")
    a.post(f"/events/{ev['id']}/not-going")
    assert _get(b, ev["id"])["going_count"] == 1


def test_going_flag_is_per_viewer(db, rooms):  # noqa: F811
    ev = _post(db, rooms)
    me, other = client_for(db, make_user(db)), client_for(db, make_user(db))
    me.post(f"/events/{ev['id']}/going")
    assert _get(me, ev["id"])["going"] is True
    assert _get(other, ev["id"])["going"] is False
    listed = [e for e in other.get("/events", params={"end": at(3).isoformat()}).json() if e["id"] == ev["id"]][0]
    assert listed["going_count"] == 1 and listed["going"] is False


def test_unknown_event_is_404(db):
    c = client_for(db, make_user(db))
    assert c.post("/events/999/going").status_code == 404
    assert c.post("/events/999/not-going").status_code == 404


def test_refused_on_cancelled_and_over_events(db, rooms):  # noqa: F811
    ev = _post(db, rooms)
    row = db.get(Event, ev["id"])
    row.status = "cancelled"
    db.add(row)
    db.commit()
    c = client_for(db, make_user(db))
    assert c.post(f"/events/{ev['id']}/going").status_code == 400
    row.status, row.ends_at = "active", row.starts_at - timedelta(days=5)
    row.starts_at = row.ends_at - timedelta(hours=1)
    db.add(row)
    db.commit()
    assert c.post(f"/events/{ev['id']}/going").status_code == 400


def test_pending_event_only_for_its_creator(db, rooms):  # noqa: F811
    creator = make_user(db)
    ev = client_for(db, creator).post("/events", json=body(rooms["38"])).json()[0]
    row = db.get(Event, ev["id"])
    row.status = "pending_approval"
    db.add(row)
    db.commit()
    assert client_for(db, make_user(db)).post(f"/events/{ev['id']}/going").status_code == 404
    assert client_for(db, creator).post(f"/events/{ev['id']}/going").status_code == 200


def test_purge_removes_rsvps(db, rooms):  # noqa: F811
    poster, goer = make_user(db), make_user(db)
    mine = client_for(db, poster).post("/events", json=body(rooms["38"])).json()[0]
    theirs = _post(db, rooms)
    client_for(db, goer).post(f"/events/{mine['id']}/going")
    client_for(db, poster).post(f"/events/{theirs['id']}/going")
    client_for(db, goer).post(f"/events/{theirs['id']}/going")
    delete_user(db, poster)  # their event + their own RSVP go
    assert [(r.user_id, r.event_id) for r in db.exec(select(Rsvp))] == [(goer.id, theirs["id"])]


def test_feed_query_count_stays_constant_with_rsvps(db, rooms):  # noqa: F811
    from tests.test_speed import add_events, feed_url, queries_for

    me = make_user(db)
    c = client_for(db, me)

    def rsvp_each(events):
        for e in events:
            db.add(Rsvp(user_id=me.id, event_id=e.id))
            db.add(Rsvp(user_id=make_user(db).id, event_id=e.id))
        db.commit()

    rsvp_each(add_events(db, rooms, 2))
    small = queries_for(c, feed_url())
    rsvp_each(add_events(db, rooms, 20, start=2))
    feed = c.get(feed_url()).json()
    assert len(feed) == 22 and all(e["going_count"] == 2 and e["going"] for e in feed)
    assert queries_for(c, feed_url()) == small


def test_people_going_hear_about_a_cancellation(db, rooms):  # noqa: F811
    from sqlmodel import select

    from app.models.event import Alert

    creator = make_user(db)
    cc = client_for(db, creator)
    ev = cc.post("/events", json=body(rooms["38"], title="Jam")).json()[0]
    fan, other = make_user(db), make_user(db)
    client_for(db, fan).post(f"/events/{ev['id']}/going")
    cc.post(f"/events/{ev['id']}/going")  # the creator going too: no extra alert
    cc.post(f"/events/{ev['id']}/cancel", json={"reason": "Sick"})

    fan_alerts = list(db.exec(select(Alert).where(Alert.user_id == fan.id)))
    assert len(fan_alerts) == 1 and "you're going to" in fan_alerts[0].message and "Sick" in fan_alerts[0].message
    assert list(db.exec(select(Alert).where(Alert.user_id == other.id))) == []
    assert list(db.exec(select(Alert).where(Alert.user_id == creator.id))) == []  # they cancelled it


def test_one_alert_for_a_whole_cancelled_series(db, rooms):  # noqa: F811
    from datetime import datetime, timedelta

    from sqlmodel import select

    from app.models.event import Alert
    from app.services.recurrence import NY

    cc = client_for(db, make_user(db))
    until = (datetime.now(NY).date() + timedelta(days=3)).isoformat()
    evs = cc.post("/events", json=body(rooms["38"], repeat={"freq": "daily", "until": until})).json()
    fan = make_user(db)
    for e in evs:
        client_for(db, fan).post(f"/events/{e['id']}/going")
    cc.post(f"/events/{evs[0]['id']}/cancel", json={"scope": "series"})
    alerts = list(db.exec(select(Alert).where(Alert.user_id == fan.id)))
    assert len(alerts) == 1 and f"{len(evs)} dates" in alerts[0].message
