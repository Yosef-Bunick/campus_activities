import { lazy, Suspense, useState } from 'react';
import Box from '@mui/material/Box';
import Chip from '@mui/material/Chip';
import Typography from '@mui/material/Typography';
import { useQuery } from '@tanstack/react-query';
import { apiGet } from '../api';
import EventList from '../components/EventList';

const PersonSheet = lazy(() => import('../components/PersonSheet'));

// ★ Saved events (one date or a whole series) + everything from people you ♥ favorite.
export default function FavoritesView() {
  const query = useQuery({ queryKey: ['favorites'], queryFn: () => apiGet('/favorites'), refetchInterval: 60000 });
  const [person, setPerson] = useState(null);
  const part = (key) => ({ ...query, data: query.data?.[key] });

  return (
    <Box sx={{ p: 2, display: 'flex', flexDirection: 'column', gap: 1 }}>
      <Typography variant="h5" component="h1">Saved</Typography>
      <EventList query={part('saved')} empty="Tap ☆ on any event to save it here." />

      <Typography variant="h5" component="h1" sx={{ mt: 2 }}>From people you follow</Typography>
      {query.data?.people.length > 0 && (
        <Box sx={{ display: 'flex', gap: 1, flexWrap: 'wrap' }}>
          {query.data.people.map((p) => (
            <Chip key={p.id} label={p.display_name || 'Someone'} onClick={() => setPerson(p.id)} />
          ))}
        </Box>
      )}
      <EventList query={part('from_people')} empty="Tap a person's name on an event, then Favorite, to see all their events here." />
      <Suspense fallback={null}>
        {person && <PersonSheet userId={person} open onClose={() => setPerson(null)} />}
      </Suspense>
    </Box>
  );
}
