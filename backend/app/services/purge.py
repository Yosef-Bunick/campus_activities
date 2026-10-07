"""Hard-delete a user and everything that is theirs (architecture §9, ADR-006).

Used by the daily 150-day inactivity purge and by "Delete my account". Done
with explicit statements (not relying on database cascades) so it behaves the
same on SQLite and Postgres:
  * deleted: the user, their sessions, events + series, favorites/hides/saves/RSVPs in
    BOTH directions, alerts, reports they made, rule hits;
  * kept: moderation-log text (ids go null → "a deleted user") and the ban hash
    in banned_accounts, so a ban outlives the account.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from sqlalchemy import delete, update
from sqlmodel import Session, col, or_, select

from app.core.config import settings
from app.core.permissions import Role
from app.models.event import Alert, Event, EventSeries
from app.models.moderation import ModerationLog, Report, RuleHit
from app.models.social import HiddenEvent, Rsvp, SavedEvent, UserFavorite, UserHidden
from app.models.user import AuthSession, User


def delete_user(session: Session, user: User) -> None:
    uid = user.id
    event_ids = list(session.exec(select(Event.id).where(Event.creator_id == uid)))
    series_ids = list(session.exec(select(EventSeries.id).where(EventSeries.creator_id == uid)))

    # Things pointing at their events / series.
    if event_ids:
        session.exec(delete(SavedEvent).where(col(SavedEvent.event_id).in_(event_ids)))
        session.exec(delete(HiddenEvent).where(col(HiddenEvent.event_id).in_(event_ids)))
        session.exec(delete(Rsvp).where(col(Rsvp.event_id).in_(event_ids)))
        session.exec(delete(Report).where(col(Report.event_id).in_(event_ids)))
        session.exec(update(Alert).where(col(Alert.event_id).in_(event_ids)).values(event_id=None))
        session.exec(
            update(ModerationLog)
            .where(col(ModerationLog.target_event_id).in_(event_ids))
            .values(target_event_id=None)
        )
    if series_ids:
        session.exec(delete(SavedEvent).where(col(SavedEvent.series_id).in_(series_ids)))
        session.exec(delete(HiddenEvent).where(col(HiddenEvent.series_id).in_(series_ids)))

    # Their own rows, and other people's favorites/hides that point at them.
    for stmt in (
        delete(SavedEvent).where(SavedEvent.user_id == uid),
        delete(HiddenEvent).where(HiddenEvent.user_id == uid),
        delete(Rsvp).where(Rsvp.user_id == uid),
        delete(UserFavorite).where(or_(UserFavorite.user_id == uid, UserFavorite.favorite_user_id == uid)),
        delete(UserHidden).where(or_(UserHidden.user_id == uid, UserHidden.hidden_user_id == uid)),
        delete(Alert).where(Alert.user_id == uid),
        delete(RuleHit).where(RuleHit.user_id == uid),
        delete(AuthSession).where(AuthSession.user_id == uid),
        update(Alert).where(Alert.subject_user_id == uid).values(subject_user_id=None),
        update(Report).where(Report.reporter_id == uid).values(reporter_id=None),
        update(Report).where(Report.resolved_by_id == uid).values(resolved_by_id=None),
        update(Event).where(Event.cancelled_by_id == uid).values(cancelled_by_id=None),
        update(ModerationLog).where(ModerationLog.actor_id == uid).values(actor_id=None),
        update(ModerationLog).where(ModerationLog.target_user_id == uid).values(target_user_id=None),
    ):
        session.exec(stmt)

    # Their events (occurrences first, then the series), then the user.
    if event_ids:
        session.exec(delete(Event).where(col(Event.id).in_(event_ids)))
    if series_ids:
        session.exec(delete(EventSeries).where(col(EventSeries.id).in_(series_ids)))
    session.exec(delete(User).where(User.id == uid))
    session.commit()


def purge_inactive(session: Session, days: int | None = None) -> int:
    """Delete everyone inactive for more than `days` (INACTIVITY_DELETE_DAYS),
    except the owner. Returns how many were deleted."""
    cutoff = datetime.now(UTC) - timedelta(days=days or settings.inactivity_delete_days)
    stale = list(
        session.exec(
            select(User).where(User.last_active_at < cutoff, User.role != Role.OWNER.value)
        )
    )
    for user in stale:
        delete_user(session, user)
    return len(stale)
