import { describe, expect, it } from 'vitest';
import { addDays, nyDateKey, nyTimeKey, nyToDate, weekday } from '../lib/time';
import { toApiParams, toSearch } from '../contexts/FilterContext';

describe('New York time', () => {
  it('converts wall clock to UTC on both sides of daylight saving', () => {
    expect(nyToDate('2026-10-27', '15:00').toISOString()).toBe('2026-10-27T19:00:00.000Z'); // EDT
    expect(nyToDate('2026-11-03', '15:00').toISOString()).toBe('2026-11-03T20:00:00.000Z'); // EST
  });

  it('round-trips date and time keys', () => {
    const d = nyToDate('2026-03-08', '09:30'); // the spring-forward day
    expect(nyDateKey(d)).toBe('2026-03-08');
    expect(nyTimeKey(d)).toBe('09:30');
  });

  it('does day math on keys', () => {
    expect(addDays('2026-12-31', 1)).toBe('2027-01-01');
    expect(weekday('2026-10-05')).toBe(0); // Monday
  });
});

describe('shared filter', () => {
  it('keeps the URL short and maps to API params', () => {
    const f = { types: ['club_event'], rooms: [2, 3], q: 'chess' };
    expect(toSearch(f)).toBe('?types=club_event&rooms=2%2C3&q=chess');
    expect(toApiParams(f).toString()).toBe('types=club_event&room_ids=2&room_ids=3&search=chess');
    expect(toSearch({ types: ['main_event', 'club_event', 'friend_event'], rooms: [], q: '' })).toBe('');
  });
});
