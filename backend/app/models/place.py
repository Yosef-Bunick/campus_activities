"""Building, Floor, Room (architecture §10). Map drawing comes in Milestone 3."""

from __future__ import annotations

from sqlmodel import Field, SQLModel


class Building(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    name: str = Field(max_length=120, unique=True)


class Floor(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    building_id: int = Field(foreign_key="building.id", index=True, ondelete="CASCADE")
    level: int
    floor_plan_svg: str | None = Field(default=None, max_length=300)  # path, Milestone 3


class Room(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    floor_id: int | None = Field(default=None, foreign_key="floor.id", index=True)
    name: str = Field(max_length=120)
    # Id of the room's shape on the floor-plan SVG (Milestone 3). For now, the
    # pin from pin-map.html, e.g. "pin:1".
    shape_ref: str | None = Field(default=None, max_length=60)
    is_outdoor: bool = False
    max_overlapping: int | None = None  # None = permissions.ROOM_MAX_OVERLAPPING
