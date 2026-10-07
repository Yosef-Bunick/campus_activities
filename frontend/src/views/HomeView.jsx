import { lazy, Suspense, useMemo, useState } from 'react';
import Box from '@mui/material/Box';
import Button from '@mui/material/Button';
import Chip from '@mui/material/Chip';
import Fab from '@mui/material/Fab';
import Typography from '@mui/material/Typography';
import AddIcon from '@mui/icons-material/esm/Add';
import { useQueryClient } from '@tanstack/react-query';
import EventList from '../components/EventList';
import PullToRefresh from '../components/PullToRefresh';
import { TAB_BAR_HEIGHT } from '../components/BottomTabs';
import { useAuth } from '../contexts/AuthContext';
import { useEvents } from '../hooks/useEvents';
import { addDays, nyDateKey, nyToDate, weekday } from '../lib/time';

const EventForm = lazy(() => import('../components/EventForm'));
const MajorDialog = lazy(() => import('../components/MajorDialog'));

export const HOME_WINDOW_HOURS = 4; // "the next few hours"

// Time chips. `end` is computed from "now" (rounded to the minute so the 60 s
// poll reuses one cache key per minute).
const WINDOWS = {
  now: { label: 'Now', end: () => null },
  soon: { label: `Next ${HOME_WINDOW_HOURS}h`, end: (now) => new Date(now + HOME_WINDOW_HOURS * 3600000) },
  today: { label: 'Today', end: () => nyToDate(addDays(nyDateKey(), 1)) },
  week: { label: 'This week', end: () => nyToDate(addDays(nyDateKey(), 7 - weekday(nyDateKey()))) },
};

// Home: what's on now and soon, by time chip, optionally just Recommended
// (main events + events for your major, ADR-028), plus + New event.
export default function HomeView() {
  const { user } = useAuth();
  const [win, setWin] = useState('soon');
  const [recommended, setRecommended] = useState(false);
  const [dialog, setDialog] = useState(null); // 'create' | 'major'

  const params = useMemo(() => {
    const now = Math.floor(Date.now() / 60000) * 60000;
    const p = new URLSearchParams();
    if (win === 'now') p.set('happening_now', 'true');
    else {
      p.set('start', new Date(now).toISOString());
      p.set('end', WINDOWS[win].end(now).toISOString());
    }
    if (recommended) p.set('recommended', 'true');
    return p;
  }, [win, recommended]);
  const query = useEvents(params);
  const qc = useQueryClient();
  const refresh = () => qc.refetchQueries({ queryKey: ['events'], type: 'active' });

  return (
    <PullToRefresh onRefresh={refresh}>
    <Box sx={{ p: 2, display: 'flex', flexDirection: 'column', gap: 1.5 }}>
      <Typography variant="h5" component="h1">What's on</Typography>
      <Box sx={{ display: 'flex', gap: 1, overflowX: 'auto', pb: 0.5 }} role="group" aria-label="When">
        {Object.entries(WINDOWS).map(([key, w]) => (
          <Chip key={key} label={w.label} color={win === key ? 'primary' : 'default'}
            variant={win === key ? 'filled' : 'outlined'} onClick={() => setWin(key)} aria-pressed={win === key} />
        ))}
      </Box>
      <Box sx={{ display: 'flex', gap: 1, alignItems: 'center', flexWrap: 'wrap' }}>
        <Chip label="Recommended" color={recommended ? 'secondary' : 'default'} variant={recommended ? 'filled' : 'outlined'}
          onClick={() => setRecommended((r) => !r)} aria-pressed={recommended} />
        {recommended && !user?.major && (
          <Button size="small" onClick={() => setDialog('major')}>Set your major for more</Button>
        )}
      </Box>
      <EventList
        query={query}
        grouped={win === 'today' || win === 'week'}
        empty={win === 'now' ? 'Nothing happening right now.' : 'Nothing coming up yet. Start something!'}
      />
      <Fab
        color="primary" variant="extended" onClick={() => setDialog('create')}
        sx={{ position: 'fixed', right: 16, bottom: `calc(${TAB_BAR_HEIGHT + 16}px + env(safe-area-inset-bottom))` }}
      >
        <AddIcon sx={{ mr: 1 }} /> New event
      </Fab>
      <Suspense fallback={null}>
        {dialog === 'create' && <EventForm open onClose={() => setDialog(null)} />}
        {dialog === 'major' && <MajorDialog open onClose={() => setDialog(null)} />}
      </Suspense>
    </Box>
    </PullToRefresh>
  );
}
