"""Speed guards: list endpoints run a fixed number of queries however much data
there is (no N+1), and big responses are gzipped."""

import gzip
from contextlib import contextmanager
from datetime import timedelta

from sqlalchemy import event as sa_event

from app.core.database import engine
from app.models.event import Alert, Event, EventSeries
from app.models.social import HiddenEvent, SavedEvent, UserFavorite
from tests.conftest import client_for, make_user
from tests.test_events_api import at, rooms  # noqa: F401  (fixture)


@contextmanager
def count_queries():
    seen = []

    def _count(conn, cursor, statement, *args):
        seen.append(statement)

    sa_event.listen(engine, "before_cursor_execute", _count)
    try:
        yield seen
    finally:
        sa_event.remove(engine, "before_cursor_execute", _count)


def add_events(db, rooms, n: int, start: int = 0) -> list[Event]:  # noqa: F811
    """n events tomorrow, each by a different person in a different series."""
    room_ids = list(rooms.values())
    s = at(1)
    events = []
    for i in range(start, start + n):
        creator = make_user(db)
        series = EventSeries(creator_id=creator.id, freq="weekly", starts_on=s.date(), ends_on=s.date())
        db.add(series)
        db.flush()
        events.append(Event(
            title=f"Event {i}", description="x" * 200, type="friend_event",
            room_id=room_ids[i % len(room_ids)], series_id=series.id, creator_id=creator.id,
            starts_at=s + timedelta(minutes=i), ends_at=s + timedelta(hours=2),
        ))  # fmt: skip
    db.add_all(events)
    db.commit()
    return events


def queries_for(client, url: str) -> int:
    with count_queries() as seen:
        assert client.get(url).status_code == 200
    return len(seen)


def feed_url() -> str:
    return f"/events?start={at(0, 0).isoformat()}&end={at(3).isoformat()}".replace("+", "%2B")


def test_events_query_count_is_constant(db, rooms):  # noqa: F811
    c = client_for(db, make_user(db))
    add_events(db, rooms, 2)
    small = queries_for(c, feed_url())
    add_events(db, rooms, 20, start=2)
    assert len(c.get(feed_url()).json()) == 22
    assert queries_for(c, feed_url()) == small


def test_alerts_query_count_is_constant(db, rooms):  # noqa: F811
    me = make_user(db)
    c = client_for(db, me)

    def alert_each(events):
        db.add_all(Alert(user_id=me.id, kind="event_cancelled", event_id=e.id, message="m") for e in events)
        db.commit()

    alert_each(add_events(db, rooms, 2))
    small = queries_for(c, "/alerts")
    alert_each(add_events(db, rooms, 20, start=2))
    body = c.get("/alerts").json()
    assert len(body["alerts"]) == 22
    assert all(a["event_status"] == "active" for a in body["alerts"])
    assert queries_for(c, "/alerts") == small


def test_hidden_and_favorites_query_counts_are_constant(db, rooms):  # noqa: F811
    me = make_user(db)
    c = client_for(db, me)

    def mark(events):
        for i, e in enumerate(events):
            # Alternate: hide one date / hide a series / save one / save a series.
            if i % 2:
                db.add(HiddenEvent(user_id=me.id, event_id=e.id))
                db.add(SavedEvent(user_id=me.id, series_id=e.series_id))
            else:
                db.add(HiddenEvent(user_id=me.id, series_id=e.series_id))
                db.add(SavedEvent(user_id=me.id, event_id=e.id))
            db.add(UserFavorite(user_id=me.id, favorite_user_id=e.creator_id))
        db.commit()

    mark(add_events(db, rooms, 2))
    small = queries_for(c, "/hidden"), queries_for(c, "/favorites")
    mark(add_events(db, rooms, 20, start=2))
    assert len(c.get("/hidden").json()["events"]) == 22
    assert len(c.get("/favorites").json()["saved"]) == 22
    assert (queries_for(c, "/hidden"), queries_for(c, "/favorites")) == small


def test_big_event_list_is_gzipped(db, rooms):  # noqa: F811
    c = client_for(db, make_user(db))
    add_events(db, rooms, 20)
    r = c.get(feed_url(), headers={"Accept-Encoding": "gzip"})
    assert r.status_code == 200
    assert r.headers["content-encoding"] == "gzip"
    assert len(r.json()) == 20  # the client unzips it

    # Without Accept-Encoding the body is plain JSON.
    raw = c.get(feed_url(), headers={"Accept-Encoding": "identity"})
    assert "content-encoding" not in raw.headers
    assert len(raw.content) > len(gzip.compress(raw.content))
