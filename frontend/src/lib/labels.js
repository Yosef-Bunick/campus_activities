export const TYPE_LABEL = { main_event: 'Campus', club_event: 'Club', friend_event: 'Friends' };

export function roomLabel(room) {
  if (!room) return '';
  return [room.building, `Room ${room.name}`].filter(Boolean).join(' · ');
}
