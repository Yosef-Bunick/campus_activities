import { lazy, Suspense, useMemo, useState } from 'react';
import Badge from '@mui/material/Badge';
import Box from '@mui/material/Box';
import Button from '@mui/material/Button';
import IconButton from '@mui/material/IconButton';
import ToggleButton from '@mui/material/ToggleButton';
import ToggleButtonGroup from '@mui/material/ToggleButtonGroup';
import Typography from '@mui/material/Typography';
import PrevIcon from '@mui/icons-material/esm/ChevronLeft';
import NextIcon from '@mui/icons-material/esm/ChevronRight';
import FilterIcon from '@mui/icons-material/esm/FilterList';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { useLocation, useSearch } from 'wouter';
import { apiGet } from '../api';
import EventCard from '../components/EventCard';
import EventList from '../components/EventList';
import PullToRefresh from '../components/PullToRefresh';
import { toApiParams, useFilter } from '../contexts/FilterContext';
import { useEvents } from '../hooks/useEvents';
import { addDays, fmtDay, nyDateKey, nyToDate, weekday } from '../lib/time';

const FilterSheet = lazy(() => import('../components/FilterSheet'));
const SPAN = { day: 1, week: 7, list: 30 };

// Every event by day / week / list, using the shared filter.
export default function CalendarView() {
  const { filter, active } = useFilter();
  const [view, setView] = useState('day');
  const [day, setDay] = useState(nyDateKey());
  const [filterOpen, setFilterOpen] = useState(false);
  // A shared link (/calendar?event=123) shows that event on top (ADR-034).
  const [, navigate] = useLocation();
  const sharedId = new URLSearchParams(useSearch()).get('event');
  const shared = useQuery({
    queryKey: ['event', sharedId], queryFn: () => apiGet(`/events/${sharedId}`),
    enabled: Boolean(sharedId), retry: false,
  });

  const first = view === 'week' ? addDays(day, -weekday(day)) : day; // weeks start Monday
  const last = addDays(first, SPAN[view]);
  const params = useMemo(() => {
    const p = toApiParams(filter);
    p.set('start', nyToDate(first).toISOString());
    p.set('end', nyToDate(last).toISOString());
    return p;
  }, [filter, first, last]);
  const query = useEvents(params);
  const qc = useQueryClient();
  const refresh = () => Promise.all([
    qc.refetchQueries({ queryKey: ['events'], type: 'active' }),
    sharedId && qc.refetchQueries({ queryKey: ['event', sharedId], type: 'active' }),
  ]);
  const title = view === 'day' ? fmtDay(nyToDate(first, '12:00'))
    : `${fmtDay(nyToDate(first, '12:00'))} – ${fmtDay(nyToDate(addDays(last, -1), '12:00'))}`;

  return (
    <PullToRefresh onRefresh={refresh}>
    <Box sx={{ p: 2, display: 'flex', flexDirection: 'column', gap: 1.5 }}>
      <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
        <Typography variant="h5" component="h1" sx={{ flexGrow: 1 }}>Calendar</Typography>
        <Badge color="secondary" variant="dot" invisible={!active}>
          <Button size="small" startIcon={<FilterIcon />} onClick={() => setFilterOpen(true)}>Filter</Button>
        </Badge>
      </Box>
      {sharedId && (
        <Box component="section" aria-label="Shared with you" sx={{ display: 'flex', flexDirection: 'column', gap: 1 }}>
          <Box sx={{ display: 'flex', alignItems: 'center' }}>
            <Typography variant="overline" color="text.secondary" sx={{ flexGrow: 1 }}>Shared with you</Typography>
            <Button size="small" onClick={() => navigate('/calendar', { replace: true })}>Close</Button>
          </Box>
          {shared.data && <EventCard event={shared.data} showDate />}
          {shared.error && <Typography color="text.secondary" variant="body2">That event isn't available any more.</Typography>}
        </Box>
      )}
      <ToggleButtonGroup exclusive size="small" value={view} onChange={(_, v) => v && setView(v)} fullWidth>
        <ToggleButton value="day">Day</ToggleButton>
        <ToggleButton value="week">Week</ToggleButton>
        <ToggleButton value="list">List</ToggleButton>
      </ToggleButtonGroup>
      <Box sx={{ display: 'flex', alignItems: 'center' }}>
        <IconButton aria-label="Previous" onClick={() => setDay(addDays(day, -SPAN[view]))}><PrevIcon /></IconButton>
        <Typography sx={{ flexGrow: 1, textAlign: 'center' }}>{title}</Typography>
        <IconButton aria-label="Next" onClick={() => setDay(addDays(day, SPAN[view]))}><NextIcon /></IconButton>
      </Box>
      {day !== nyDateKey() && <Button size="small" onClick={() => setDay(nyDateKey())}>Today</Button>}
      <EventList query={query} grouped={view !== 'day'} empty="No events." />
      <Suspense fallback={null}>
        {filterOpen && <FilterSheet open onClose={() => setFilterOpen(false)} />}
      </Suspense>
    </Box>
    </PullToRefresh>
  );
}
