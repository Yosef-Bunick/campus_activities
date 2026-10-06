"""Seed the 4 test rooms from pin-map.html (wcc-pins.json). Safe to run twice.

    python -m app.seed

All 4 pins sit on TEC on the campus map.
shape_ref keeps the pin number; map_x/map_y place the pin on the campus map.
"""

from sqlmodel import Session, select

from app.core.database import engine
from app.models.place import Building, Floor, Room

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


if __name__ == "__main__":
    with Session(engine) as s:
        print(f"Added {seed(s)} rooms")
