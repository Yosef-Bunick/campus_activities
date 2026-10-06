// "Add to calendar" without a library (ADR-026):
//  * .ics file: Apple Calendar (iPhone/Mac), Outlook, Samsung/Android calendar
//    apps that open .ics, Thunderbird/GNOME on Linux.
//  * Google Calendar link: Android/Chrome and anyone on Google Calendar.
import { roomLabel } from './labels';

const stamp = (d) => new Date(d).toISOString().replace(/[-:]/g, '').replace(/\.\d{3}/, ''); // 20261006T190000Z
const escapeIcs = (s) => String(s || '').replace(/\\/g, '\\\\').replace(/\n/g, '\\n').replace(/[,;]/g, (c) => `\\${c}`);

function fold(line) {
  // RFC 5545: lines longer than 75 octets continue on the next line after a space.
  const out = [];
  for (let i = 0; i < line.length; i += 73) out.push((i ? ' ' : '') + line.slice(i, i + 73));
  return out.join('\r\n');
}

export function icsText(event) {
  const lines = [
    'BEGIN:VCALENDAR', 'VERSION:2.0', 'PRODID:-//Campus Events//EN', 'CALSCALE:GREGORIAN', 'METHOD:PUBLISH',
    'BEGIN:VEVENT',
    `UID:event-${event.id}@campus-events`,
    `DTSTAMP:${stamp(Date.now())}`,
    `DTSTART:${stamp(event.starts_at)}`,
    `DTEND:${stamp(event.ends_at)}`,
    `SUMMARY:${escapeIcs(event.title)}`,
    `LOCATION:${escapeIcs(roomLabel(event.room))}`,
    `DESCRIPTION:${escapeIcs(event.description)}`,
    'END:VEVENT', 'END:VCALENDAR',
  ];
  return lines.map(fold).join('\r\n') + '\r\n';
}

export function downloadIcs(event) {
  const blob = new Blob([icsText(event)], { type: 'text/calendar;charset=utf-8' });
  const a = document.createElement('a');
  a.href = URL.createObjectURL(blob);
  a.download = `${event.title.replace(/[^\w -]+/g, '').trim() || 'event'}.ics`;
  document.body.appendChild(a);
  a.click();
  a.remove();
  setTimeout(() => URL.revokeObjectURL(a.href), 1000);
}

export function googleCalendarUrl(event) {
  const p = new URLSearchParams({
    action: 'TEMPLATE',
    text: event.title,
    dates: `${stamp(event.starts_at)}/${stamp(event.ends_at)}`,
    location: roomLabel(event.room),
    details: event.description || '',
  });
  return `https://calendar.google.com/calendar/render?${p}`;
}
