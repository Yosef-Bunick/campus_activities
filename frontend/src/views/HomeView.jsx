import { lazy, Suspense, useMemo, useState } from 'react';
import Box from '@mui/material/Box';
import Fab from '@mui/material/Fab';
import Typography from '@mui/material/Typography';
import AddIcon from '@mui/icons-material/esm/Add';
import EventList from '../components/EventList';
import { TAB_BAR_HEIGHT } from '../components/BottomTabs';
import { useEvents } from '../hooks/useEvents';

const EventForm = lazy(() => import('../components/EventForm'));

export const HOME_WINDOW_HOURS = 4; // "the next few hours"

// Happening now + the next few hours, plus + New event (architecture §3).
export default function HomeView() {
  const [creating, setCreating] = useState(false);
  // Rounded to the minute so the 60 s poll reuses one cache key per minute.
  const params = useMemo(() => {
    const now = Math.floor(Date.now() / 60000) * 60000;
    return new URLSearchParams({
      start: new Date(now).toISOString(),
      end: new Date(now + HOME_WINDOW_HOURS * 3600000).toISOString(),
    });
  }, []);
  const query = useEvents(params);
  const now = new Date();
  const split = (pred) => ({ ...query, data: query.data?.filter(pred) });
  const happening = split((e) => new Date(e.starts_at) <= now);
  const soon = split((e) => new Date(e.starts_at) > now);

  return (
    <Box sx={{ p: 2, display: 'flex', flexDirection: 'column', gap: 1 }}>
      <Typography variant="h5" component="h1">Happening now</Typography>
      <EventList query={happening} grouped={false} empty="Nothing right now." />
      <Typography variant="h5" component="h1" sx={{ mt: 2 }}>Next {HOME_WINDOW_HOURS} hours</Typography>
      <EventList query={soon} grouped={false} empty="Nothing coming up yet. Start something!" />
      <Fab
        color="primary" variant="extended" onClick={() => setCreating(true)}
        sx={{ position: 'fixed', right: 16, bottom: `calc(${TAB_BAR_HEIGHT + 16}px + env(safe-area-inset-bottom))` }}
      >
        <AddIcon sx={{ mr: 1 }} /> New event
      </Fab>
      <Suspense fallback={null}>
        {creating && <EventForm open onClose={() => setCreating(false)} />}
      </Suspense>
    </Box>
  );
}
