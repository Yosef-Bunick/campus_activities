"""Revocable login sessions (unified's AuthSession pattern, opaque tokens)."""

from __future__ import annotations

import hashlib
import secrets
from datetime import UTC, datetime, timedelta

from sqlmodel import Session, select

from app.models.user import AuthSession, User, as_utc

SESSION_TTL = timedelta(days=30)


def _hash(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def create(session: Session, user: User) -> str:
    """Returns the raw token for the cookie; only its hash is stored."""
    token = secrets.token_urlsafe(32)
    session.add(
        AuthSession(user_id=user.id, jti=_hash(token), expires_at=datetime.now(UTC) + SESSION_TTL)
    )
    session.commit()
    return token


def resolve(session: Session, token: str) -> AuthSession | None:
    """The active session for this token, or None (unknown, revoked, expired)."""
    if not token:
        return None
    row = session.exec(select(AuthSession).where(AuthSession.jti == _hash(token))).first()
    if row is None or row.revoked_at is not None:
        return None
    if as_utc(row.expires_at) <= datetime.now(UTC):
        return None
    return row


def revoke(session: Session, row: AuthSession) -> None:
    row.revoked_at = datetime.now(UTC)
    session.add(row)
    session.commit()


def revoke_all(session: Session, user_id: int) -> None:
    now = datetime.now(UTC)
    for row in session.exec(
        select(AuthSession).where(AuthSession.user_id == user_id, AuthSession.revoked_at.is_(None))
    ):
        row.revoked_at = now
        session.add(row)
    session.commit()
