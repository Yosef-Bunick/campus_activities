"""`python -m app.seed --demo`: demo people + events, safe to run twice."""

from datetime import UTC, datetime

from sqlmodel import select

from app.core.majors import is_major
from app.core.terms import TERMS_VERSION
from app.models.event import Event, EventStatus
from app.models.user import as_utc
from app.seed import DEMO_PEOPLE, demo_people, seed, seed_demo


def test_demo_seed_fills_and_is_idempotent(db):
    seed(db)
    people, events = seed_demo(db)
    assert people == len(DEMO_PEOPLE)
    assert events >= 10

    rows = db.exec(select(Event)).all()
    assert len(rows) == events
    assert all(e.status == EventStatus.ACTIVE.value for e in rows)
    now = datetime.now(UTC)
    assert any(as_utc(e.starts_at) <= now < as_utc(e.ends_at) for e in rows)
    kinds = {e.location_kind for e in rows}
    assert {"online", "off_campus", "campus"} <= kinds
    assert any(e.series_id for e in rows)  # the weekly club meeting
    assert any(e.type == "main_event" and e.majors for e in rows)
    assert len({e.creator_id for e in rows}) >= 5

    # Second run: nothing new.
    assert seed(db) == 0
    assert seed_demo(db) == (0, 0)
    assert len(db.exec(select(Event)).all()) == len(rows)


def test_demo_people_skip_dialogs(db):
    people, _ = demo_people(db)
    assert len(people) == len(DEMO_PEOPLE)
    for user in people.values():
        assert user.terms_version == TERMS_VERSION
        assert user.major and is_major(user.major)
    assert people["demo.sga"].role == "student_gov"
    assert people["demo.manager"].role == "manager"
    assert people["demo.security"].role == "security"
