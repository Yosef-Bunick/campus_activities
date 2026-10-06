"""Expand a repeat rule into occurrences (architecture §7).

Repeats keep the same New York wall-clock time, so "Tuesdays 3-5pm" stays 3-5pm
across daylight-saving changes even though the UTC times shift.
"""

from __future__ import annotations

from datetime import UTC, date, datetime, timedelta
from zoneinfo import ZoneInfo

from app.models.event import Freq

NY = ZoneInfo("America/New_York")


def expand(
    starts_at: datetime,
    ends_at: datetime,
    freq: Freq | None,
    until: date | None = None,
    weekdays: list[int] | None = None,
) -> list[tuple[datetime, datetime]]:
    """[(start_utc, end_utc), ...]. No freq = just the one event.

    weekly/biweekly use `weekdays` (0 = Monday); if empty, the start's weekday.
    `until` is the last allowed date (New York), inclusive.
    """
    if freq is None:
        return [(starts_at, ends_at)]
    first = starts_at.astimezone(NY)
    length = ends_at - starts_at
    days = set(weekdays or [first.weekday()])
    week0 = first.date() - timedelta(days=first.weekday())  # Monday of the first week

    out = []
    d = first.date()
    while d <= until:
        if freq == Freq.DAILY:
            take = True
        else:
            weeks = (d - week0).days // 7
            take = d.weekday() in days and (freq == Freq.WEEKLY or weeks % 2 == 0)
        if take:
            local = datetime.combine(d, first.timetz().replace(tzinfo=None), tzinfo=NY)
            start = local.astimezone(UTC)
            out.append((start, start + length))
        d += timedelta(days=1)
    return out


def ny_date(dt: datetime) -> date:
    return dt.astimezone(NY).date()
