// Times are stored in UTC and always shown in New York time, on every device,
// using the browser's built-in Intl time-zone data (no date library).
export const NY = 'America/New_York';

const timeFmt = new Intl.DateTimeFormat('en-US', { timeZone: NY, hour: 'numeric', minute: '2-digit' });
const dayFmt = new Intl.DateTimeFormat('en-US', { timeZone: NY, weekday: 'short', month: 'short', day: 'numeric' });
const keyFmt = new Intl.DateTimeFormat('en-CA', { timeZone: NY, year: 'numeric', month: '2-digit', day: '2-digit' });
const partsFmt = new Intl.DateTimeFormat('en-US', {
  timeZone: NY, hourCycle: 'h23', year: 'numeric', month: 'numeric', day: 'numeric', hour: 'numeric', minute: 'numeric', second: 'numeric',
});

export const fmtTime = (d) => timeFmt.format(new Date(d));
export const fmtDay = (d) => dayFmt.format(new Date(d));
/** "YYYY-MM-DD" of the New York calendar day containing instant `d`. */
export const nyDateKey = (d = new Date()) => keyFmt.format(new Date(d));
/** "HH:MM" New York wall-clock time of instant `d`. */
export function nyTimeKey(d) {
  const p = Object.fromEntries(partsFmt.formatToParts(new Date(d)).map((x) => [x.type, x.value]));
  return `${p.hour.padStart(2, '0')}:${p.minute.padStart(2, '0')}`;
}

// New York's UTC offset (ms) at instant t.
function offsetAt(t) {
  const p = Object.fromEntries(partsFmt.formatToParts(new Date(t)).map((x) => [x.type, +x.value]));
  return Date.UTC(p.year, p.month - 1, p.day, p.hour, p.minute, p.second) - Math.floor(t / 1000) * 1000;
}

/** New York wall clock ("2026-10-06", "15:00") → Date (UTC instant). DST-safe. */
export function nyToDate(dateKey, timeKey = '00:00') {
  const [y, m, d] = dateKey.split('-').map(Number);
  const [h, mi] = timeKey.split(':').map(Number);
  const guess = Date.UTC(y, m - 1, d, h, mi);
  let t = guess - offsetAt(guess);
  t = guess - offsetAt(t); // second pass fixes guesses that straddle a DST switch
  return new Date(t);
}

/** Add whole days to a "YYYY-MM-DD" key. */
export function addDays(dateKey, n) {
  const [y, m, d] = dateKey.split('-').map(Number);
  return new Date(Date.UTC(y, m - 1, d + n)).toISOString().slice(0, 10);
}

/** Monday-based weekday (0 = Mon) of a "YYYY-MM-DD" key. */
export function weekday(dateKey) {
  const [y, m, d] = dateKey.split('-').map(Number);
  return (new Date(Date.UTC(y, m - 1, d)).getUTCDay() + 6) % 7;
}

/** Group events by New York day: [[dateKey, events], ...] in order. */
export function groupByDay(events) {
  const groups = new Map();
  for (const e of events) {
    const k = nyDateKey(e.starts_at);
    if (!groups.has(k)) groups.set(k, []);
    groups.get(k).push(e);
  }
  return [...groups.entries()];
}
