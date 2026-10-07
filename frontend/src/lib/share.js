// Share an event (ADR-034): the phone's own share sheet (iPhone, Android,
// Samsung, and Safari/Edge on laptops); elsewhere, copy the link.
import { placeLabel } from './labels';
import { fmtDay, fmtTime } from './time';

export const eventLink = (event) => `${window.location.origin}/calendar?event=${event.id}`;

/** Returns 'shared', 'copied', or null if the person closed the share sheet. */
export async function shareEvent(event) {
  const url = eventLink(event);
  const text = `${event.title} · ${fmtDay(event.starts_at)} ${fmtTime(event.starts_at)} · ${placeLabel(event)}`;
  if (navigator.share) {
    try {
      await navigator.share({ title: event.title, text, url });
      return 'shared';
    } catch (err) {
      if (err?.name === 'AbortError') return null; // they closed the sheet
    }
  }
  await navigator.clipboard?.writeText(url);
  return 'copied';
}
