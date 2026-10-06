from datetime import UTC, date, datetime

from app.models.event import Freq
from app.services.recurrence import NY, expand


def ny(y, m, d, h, mi=0):
    return datetime(y, m, d, h, mi, tzinfo=NY).astimezone(UTC)


def test_one_off():
    s, e = ny(2026, 10, 6, 15), ny(2026, 10, 6, 17)
    assert expand(s, e, None) == [(s, e)]


def test_weekly_tuesdays_keep_3pm_across_daylight_saving():
    # DST ends Nov 1 2026: UTC hour shifts from 19 to 20, New York stays 3pm.
    out = expand(ny(2026, 10, 27, 15), ny(2026, 10, 27, 17), Freq.WEEKLY, date(2026, 11, 10))
    assert [s.astimezone(NY).strftime("%a %d %H:%M") for s, _ in out] == [
        "Tue 27 15:00", "Tue 03 15:00", "Tue 10 15:00",
    ]  # fmt: skip
    assert [s.hour for s, _ in out] == [19, 20, 20]
    assert all(e - s == out[0][1] - out[0][0] for s, e in out)


def test_weekly_on_chosen_days():
    out = expand(ny(2026, 10, 5, 9), ny(2026, 10, 5, 10), Freq.WEEKLY, date(2026, 10, 11), [0, 2])
    assert [s.astimezone(NY).day for s, _ in out] == [5, 7]  # Mon, Wed


def test_biweekly_skips_every_other_week():
    out = expand(ny(2026, 10, 5, 9), ny(2026, 10, 5, 10), Freq.BIWEEKLY, date(2026, 11, 2))
    assert [s.astimezone(NY).day for s, _ in out] == [5, 19, 2]


def test_daily_until_inclusive():
    out = expand(ny(2026, 10, 5, 9), ny(2026, 10, 5, 10), Freq.DAILY, date(2026, 10, 7))
    assert len(out) == 3
