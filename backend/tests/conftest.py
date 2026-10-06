import os

# Tests never touch dev.db: an in-memory SQLite (shared via StaticPool), and a
# fixed owner + WCC tenant. Set before app.core.config is imported.
# CI also runs some files against real Postgres via TEST_DATABASE_URL.
os.environ["DATABASE_URL"] = os.environ.get("TEST_DATABASE_URL", "sqlite://")
os.environ["OWNER_EMAIL"] = "owner@gmail.com"
os.environ["ALLOWED_TENANT_IDS"] = "4981a704-f6a3-4ac0-89c2-a3812354a3ff"
os.environ["EMAIL_DOMAIN_REQUIREMENT"] = "sunywcc.edu"
os.environ["FRONTEND_ORIGIN"] = "http://localhost:5173"
os.environ["DEV_LOGIN"] = "0"
os.environ["WORKER_ENABLED"] = "0"

import itertools  # noqa: E402

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from sqlmodel import Session, SQLModel  # noqa: E402

import app.models.event  # noqa: E402,F401  (registers tables)
import app.models.moderation  # noqa: E402,F401
import app.models.place  # noqa: E402,F401
import app.models.social  # noqa: E402,F401
import app.models.user  # noqa: E402,F401
from app.core.auth import CSRF_COOKIE, SESSION_COOKIE  # noqa: E402
from app.core.database import engine  # noqa: E402
from app.main import app  # noqa: E402
from app.services import sessions  # noqa: E402
from app.services.accounts import MicrosoftIdentity, sign_in  # noqa: E402

WCC = "4981a704-f6a3-4ac0-89c2-a3812354a3ff"
_oids = itertools.count(1)


@pytest.fixture(autouse=True)
def db():
    # Tests build the schema directly; real databases use `alembic upgrade head`.
    SQLModel.metadata.create_all(engine)
    with Session(engine) as s:
        yield s
    SQLModel.metadata.drop_all(engine)


def make_user(db: Session, role: str = "student", email: str | None = None):
    n = next(_oids)
    user = sign_in(db, MicrosoftIdentity(WCC, f"oid-{n}", email or f"s{n}@my.sunywcc.edu", f"Person {n}"))
    if role != user.role:
        user.role = role
        db.add(user)
        db.commit()
        db.refresh(user)
    return user


def client_for(db: Session, user=None) -> TestClient:
    """A browser-like client: signed in as `user` (if given), with the CSRF
    header set the way the frontend's api.js sets it."""
    c = TestClient(app)
    if user is not None:
        c.cookies.set(SESSION_COOKIE, sessions.create(db, user))
        c.cookies.set(CSRF_COOKIE, "t" * 64)
        c.headers["X-CSRF-Token"] = "t" * 64
    return c
