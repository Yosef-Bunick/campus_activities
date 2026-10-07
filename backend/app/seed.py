"""Seed the 4 test rooms from pin-map.html (wcc-pins.json). Safe to run twice.

    python -m app.seed           # rooms only
    python -m app.seed --demo    # rooms + demo people and events (local testing)

All 4 pins sit on TEC on the campus map.
shape_ref keeps the pin number; map_x/map_y place the pin on the campus map.
"""

import sys
from datetime import UTC, datetime, timedelta

from sqlmodel import Session, select

from app.core.database import engine
from app.core.majors import is_major
from app.core.terms import TERMS_VERSION
from app.models.event import Event, EventType, Freq, LocationKind
from app.models.place import Building, Floor, Room
from app.models.user import User
from app.schemas.events import EventCreate, Repeat
from app.services import events as E
from app.services.accounts import MicrosoftIdentity, sign_in
from app.services.event_rules import RuleError
from app.services.recurrence import NY

BUILDING = "TEC"
# (pin number, room name, floor, x, y) from labels "38 f1", "26 f1", "108 f2",
# "25 d f1"; x/y are 0..1 on WCC_MAP2.png.
PINS = [
    (1, "38", 1, 0.6805, 0.3227),
    (6, "26", 1, 0.7484, 0.3111),
    (2, "108", 2, 0.6941, 0.2281),
    (3, "25D", 1, 0.746, 0.2371),
]


def seed(session: Session) -> int:
    building = session.exec(select(Building).where(Building.name == BUILDING)).first()
    if building is None:
        building = Building(name=BUILDING)
        session.add(building)
        session.flush()
    added = 0
    for pin, name, level, x, y in PINS:
        floor = session.exec(
            select(Floor).where(Floor.building_id == building.id, Floor.level == level)
        ).first()
        if floor is None:
            floor = Floor(building_id=building.id, level=level)
            session.add(floor)
            session.flush()
        room = session.exec(select(Room).where(Room.shape_ref == f"pin:{pin}")).first()
        if room is None:
            room = Room(floor_id=floor.id, name=name, shape_ref=f"pin:{pin}")
            added += 1
        room.map_x, room.map_y = x, y
        session.add(room)
    session.commit()
    return added


# ── Demo data (--demo): people + events that always look current ──

WCC_TENANT = "4981a704-f6a3-4ac0-89c2-a3812354a3ff"
# (slug, name, role, major). Majors are keys from majors.txt; ones missing from
# the current list are left unset (tests use a smaller list).
DEMO_PEOPLE = [
    ("demo.student", "Demo Student", "student", "nursing"),
    ("demo.sga", "Demo SGA", "student_gov", "liberal_arts_and_sciences_humanities"),
    ("demo.manager", "Demo Manager", "manager", "undeclared"),
    ("demo.security", "Demo Security", "security", "undeclared"),
    ("demo.alex", "Alex Rivera", "student", "computer_science"),
    ("demo.maya", "Maya Chen", "student", "digital_filmmaking"),
    ("demo.jordan", "Jordan Brooks", "student", "undeclared"),
]


def demo_email(slug: str) -> str:
    return f"{slug}@my.sunywcc.edu"


def demo_people(session: Session) -> tuple[dict[str, User], int]:
    """{slug: User}, and how many were new. The oid matches what the local dev
    sign-in uses for that email, so typing the email signs in as this person."""
    people, added = {}, 0
    for slug, name, role, major in DEMO_PEOPLE:
        email = demo_email(slug)
        ident = MicrosoftIdentity(WCC_TENANT, f"dev:{email}", email, name)
        known = select(User).where(User.ms_tenant_id == ident.tid, User.ms_object_id == ident.oid)
        added += session.exec(known).first() is None
        user = sign_in(session, ident)
        # Terms + major set so the first-sign-in dialogs don't get in the way.
        user.role, user.terms_version = role, TERMS_VERSION
        user.major = major if is_major(major) else "undeclared" if is_major("undeclared") else None
        session.add(user)
        session.commit()
        session.refresh(user)
        people[slug] = user
    return people, added


def demo_events(session: Session, people: dict[str, User]) -> int:
    """A spread of events relative to now (New York). Skipped entirely if the
    demo people already have events, so a second run adds nothing."""
    ids = [u.id for u in people.values()]
    if session.exec(select(Event).where(Event.creator_id.in_(ids))).first() is not None:
        return 0
    rooms = {r.name: r.id for r in session.exec(select(Room)).all()}
    now = datetime.now(NY).replace(second=0, microsecond=0)
    base = now - timedelta(minutes=now.minute % 15)  # round down to a quarter hour

    def soon(hours: float, length: float = 1.0):
        start = base + timedelta(hours=hours)
        return start, start + timedelta(hours=length)

    def on(days: int, hour: int, length: float = 1.5):
        start = datetime.combine(now.date() + timedelta(days=days), datetime.min.time(), NY)
        start += timedelta(hours=hour)
        return start, start + timedelta(hours=length)

    tags = [m for m in ("computer_science", "nursing", "undeclared") if is_major(m)][:2]
    first_club = on(1, 17)
    # (creator, title, type, (start, end), place, extras)
    plan = [
        ("demo.student", "Anatomy study group", EventType.FRIEND, soon(-0.5, 1.5), "38", {}),
        ("demo.alex", "Coding club drop-in", EventType.CLUB, soon(1), "26", {}),
        ("demo.maya", "Online study hall", EventType.FRIEND, soon(1.5), "online", {}),
        ("demo.security", "Campus safety Q&A", EventType.FRIEND, soon(2.5), "108", {}),
        ("demo.student", "Clinical skills practice", EventType.FRIEND, soon(3, 1.5), "25D", {}),
        ("demo.jordan", "Board game night", EventType.FRIEND, soon(5, 2), "38", {}),
        ("demo.manager", "Resume workshop", EventType.CLUB, on(1, 12), "108", {}),
        ("demo.maya", "Film club screening", EventType.CLUB, on(2, 18, 2), "26", {}),
        ("demo.sga", "Fall involvement fair", EventType.MAIN, on(3, 11, 3), "38",
         {"majors": tags}),
        ("demo.sga", "Kensico Dam fall walk", EventType.CLUB, on(4, 10, 2), "off",
         {"location": "Kensico Dam Plaza"}),
        ("demo.alex", "Robotics club meeting", EventType.CLUB, first_club, "25D",
         {"repeat": Repeat(freq=Freq.WEEKLY, until=first_club[0].date() + timedelta(weeks=4))}),
        ("demo.jordan", "Pickup basketball", EventType.FRIEND, on(5, 15), "off",
         {"location": "Gateway Center courts"}),
    ]  # fmt: skip
    made = 0
    for slug, title, kind, (start, end), where, extra in plan:
        if where == "online":
            place = {"location_kind": LocationKind.ONLINE,
                     "online_url": "https://zoom.us/j/1234567890"}  # fmt: skip
        elif where == "off":
            place = {"location_kind": LocationKind.OFF_CAMPUS}
        else:
            place = {"room_id": rooms.get(where)}
        try:
            body = EventCreate(
                title=title, description=f"Demo event by {people[slug].display_name}.",
                type=kind, starts_at=start.astimezone(UTC), ends_at=end.astimezone(UTC),
                **place, **extra,
            )  # fmt: skip
            made += len(E.create(session, people[slug], body))
        except (E.Conflicts, RuleError, ValueError) as e:
            # A rule said no (e.g. late at night "now" pushes one past a limit): skip it.
            session.rollback()
            print(f"  skipped “{title}”: {getattr(e, 'message', e)}")
    return made


def seed_demo(session: Session) -> tuple[int, int]:
    """(new demo people, new demo events). Needs the rooms (seed) first."""
    people, added = demo_people(session)
    return added, demo_events(session, people)


if __name__ == "__main__":
    with Session(engine) as s:
        rooms = seed(s)
        if "--demo" not in sys.argv[1:]:
            print(f"Added {rooms} rooms")
        else:
            people, events = seed_demo(s)
            print(f"Rooms: {rooms} added; demo people: {people} added; demo events: {events}")
            print("Sign in with the local dev sign-in as any of (pick the matching role):")
            for slug, name, role, _ in DEMO_PEOPLE:
                print(f"  {demo_email(slug):32} {name} ({role})")
