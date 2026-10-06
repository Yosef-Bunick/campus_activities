"""Moderation log, notices to everyone holding a permission, and automatic abuse
flags (Phase 2). Flags only ALERT managers/owner; a human decides any ban."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from sqlmodel import Session, func, select

from app.core import permissions as P
from app.models.event import Alert, Event
from app.models.moderation import ModerationLog, Report, RuleHit
from app.models.user import User


def name(user: User | None) -> str:
    return (user.display_name or user.email) if user else "a deleted user"


def log(
    session: Session,
    actor: User | None,
    action: str,
    detail: str,
    target_user: User | None = None,
    target_event: Event | None = None,
) -> None:
    session.add(
        ModerationLog(
            actor_id=actor.id if actor else None,
            action=action,
            target_user_id=target_user.id if target_user else None,
            target_event_id=target_event.id if target_event else None,
            detail=detail[:500],
        )
    )


def notify(
    session: Session,
    perm: str,
    kind: str,
    message: str,
    event_id: int | None = None,
    subject_user_id: int | None = None,
) -> int:
    """One alert to every (non-banned) user whose role holds `perm`."""
    roles = [r.value for r in P.PERMISSIONS[perm]]
    people = session.exec(select(User).where(User.role.in_(roles), User.is_banned == False))
    count = 0
    for person in people:
        session.add(
            Alert(user_id=person.id, kind=kind, message=message[:500], event_id=event_id,
                  subject_user_id=subject_user_id)
        )  # fmt: skip
        count += 1
    return count


def _flag(session: Session, who: User, why: str, event_id: int | None = None) -> None:
    notify(session, "user.ban", "abuse_flag", f"Check {name(who)}: {why}",
           event_id=event_id, subject_user_id=who.id)  # fmt: skip
    log(session, None, "flag", f"{name(who)}: {why}", target_user=who)


def record_hit(session: Session, user: User, kind: str) -> None:
    """Count a rule hit; flag on reaching the weekly threshold (once, not every time)."""
    session.add(RuleHit(user_id=user.id, kind=kind))
    session.flush()
    since = datetime.now(UTC) - timedelta(days=7)
    hits = session.exec(
        select(func.count()).select_from(RuleHit).where(
            RuleHit.user_id == user.id, RuleHit.kind == kind, RuleHit.created_at >= since
        )
    ).one()
    limit = {"daily_cap": P.FLAG_CAP_HITS_PER_WEEK, "room_full": P.FLAG_ROOM_FULL_PER_WEEK}[kind]
    if hits == limit:
        what = "hit the daily event cap" if kind == "daily_cap" else "kept overfilling rooms"
        _flag(session, user, f"{what} {hits} times this week")


def report_event(session: Session, reporter: User, event: Event, reason: str) -> bool:
    """False if this person already reported this event."""
    exists = session.exec(
        select(Report).where(Report.reporter_id == reporter.id, Report.event_id == event.id)
    ).first()
    if exists:
        return False
    session.add(Report(reporter_id=reporter.id, event_id=event.id, reason=reason.strip()))
    session.flush()
    count = session.exec(
        select(func.count()).select_from(Report).where(Report.event_id == event.id)
    ).one()
    if count == P.FLAG_REPORTS_PER_EVENT:
        creator = session.get(User, event.creator_id)
        _flag(session, creator, f"“{event.title}” was reported {count} times", event_id=event.id)
    log(session, reporter, "report", f"Reported “{event.title}”: {reason.strip() or 'no reason'}",
        target_user=session.get(User, event.creator_id), target_event=event)  # fmt: skip
    return True
