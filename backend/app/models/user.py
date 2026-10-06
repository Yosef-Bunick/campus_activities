"""User, AuthSession, BannedAccount (architecture §10)."""

from __future__ import annotations

from datetime import UTC, datetime

from sqlmodel import Field, SQLModel, UniqueConstraint

from app.core.permissions import Role


def utcnow() -> datetime:
    return datetime.now(UTC)


def as_utc(dt: datetime) -> datetime:
    """SQLite (and some Postgres drivers) hand back naive datetimes; they are UTC."""
    return dt if dt.tzinfo else dt.replace(tzinfo=UTC)


class User(SQLModel, table=True):
    __table_args__ = (UniqueConstraint("ms_tenant_id", "ms_object_id", name="uq_user_ms_identity"),)

    id: int | None = Field(default=None, primary_key=True)
    # Identity is (tid, oid), never email alone (architecture §8).
    ms_tenant_id: str = Field(max_length=64)
    ms_object_id: str = Field(max_length=64)
    email: str = Field(max_length=320, index=True)
    display_name: str = Field(default="", max_length=200)
    role: str = Field(default=Role.STUDENT.value, max_length=20)  # a Role value; plain string so adding a role needs no DB enum migration
    is_banned: bool = False
    major: str | None = Field(default=None, max_length=40)  # a key from core/majors.py
    last_active_at: datetime = Field(default_factory=utcnow)
    created_at: datetime = Field(default_factory=utcnow)


class AuthSession(SQLModel, table=True):
    """A revocable login session (unified SEC24-10). The cookie holds a random
    token; `jti` stores only its SHA-256, so a database leak yields no sessions."""

    id: int | None = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="user.id", index=True, ondelete="CASCADE")
    jti: str = Field(unique=True, index=True, max_length=64)
    created_at: datetime = Field(default_factory=utcnow)
    expires_at: datetime
    revoked_at: datetime | None = None


class BannedAccount(SQLModel, table=True):
    """sha256("tid:oid"). Survives user deletion, so a ban outlives the account."""

    account_sha256: str = Field(primary_key=True, max_length=64)
    banned_at: datetime = Field(default_factory=utcnow)
