export const TYPE_LABEL = { main_event: 'Campus', club_event: 'Club', friend_event: 'Friends' };

export const WHERE_LABEL = { campus: 'On campus', off_campus: 'Off campus', online: 'Online' };

export function roomLabel(room) {
  if (!room) return '';
  return [room.building, `Room ${room.name}`].filter(Boolean).join(' · ');
}

/** Where an event is, in words: a room, an off-campus place, or "Online" (ADR-032). */
export function placeLabel(event) {
  if (event.location_kind === 'online') return 'Online';
  if (event.location_kind === 'off_campus') return `Off campus · ${event.location}`;
  return roomLabel(event.room);
}

/** Only ever link to http(s) URLs (the server checks too). */
export function safeUrl(url) {
  try {
    const u = new URL(url);
    return u.protocol === 'https:' || u.protocol === 'http:' ? u.href : null;
  } catch {
    return null;
  }
}
