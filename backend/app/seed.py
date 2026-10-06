"""Seed the 4 test rooms from pin-map.html (wcc-pins.json). Safe to run twice.

    python -m app.seed

Rename "Test building" once we know which building the pins are in. Pin x/y
(0..1 on WCC_MAP2.png) wait for Milestone 3; shape_ref keeps the pin number.
"""

from sqlmodel import Session, select

from app.core.database import engine
from app.models.place import Building, Floor, Room

BUILDING = "Test building"
# (pin number, room name, floor) from labels "38 f1", "26 f1", "108 f2", "25 d f1".
PINS = [(1, "38", 1), (6, "26", 1), (2, "108", 2), (3, "25D", 1)]


def seed(session: Session) -> int:
    building = session.exec(select(Building).where(Building.name == BUILDING)).first()
    if building is None:
        building = Building(name=BUILDING)
        session.add(building)
        session.flush()
    added = 0
    for pin, name, level in PINS:
        floor = session.exec(
            select(Floor).where(Floor.building_id == building.id, Floor.level == level)
        ).first()
        if floor is None:
            floor = Floor(building_id=building.id, level=level)
            session.add(floor)
            session.flush()
        if session.exec(select(Room).where(Room.shape_ref == f"pin:{pin}")).first() is None:
            session.add(Room(floor_id=floor.id, name=name, shape_ref=f"pin:{pin}"))
            added += 1
    session.commit()
    return added


if __name__ == "__main__":
    with Session(engine) as s:
        print(f"Added {seed(s)} rooms")
