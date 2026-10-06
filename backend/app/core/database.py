"""Database engine + session (unified's core/database.py, trimmed).

Local dev and tests: SQLite. Production: Neon Postgres. Same DATABASE_URL var.
The schema is built by Alembic (`alembic upgrade head`), never create_all().
"""

from __future__ import annotations

from collections.abc import Iterator

from sqlmodel import Session, create_engine

from app.core.config import settings

_connect_args = (
    {"check_same_thread": False} if settings.database_url.startswith("sqlite") else {}
)
engine = create_engine(settings.database_url, connect_args=_connect_args, pool_pre_ping=True)


def get_session() -> Iterator[Session]:
    with Session(engine) as session:
        yield session
