import Box from '@mui/material/Box';
import Typography from '@mui/material/Typography';
import { fmtDay, groupByDay } from '../lib/time';
import EventCard from './EventCard';
import EventSkeleton from './EventSkeleton';

// Events grouped by New York day (or one flat list).
export default function EventList({ query, empty, grouped = true }) {
  const { data, isPending, error } = query;
  if (isPending) return <EventSkeleton />;
  if (error) return <Typography color="error" sx={{ p: 2 }}>{error.message}</Typography>;
  if (!data.length) return <Typography color="text.secondary" sx={{ py: 2 }}>{empty}</Typography>;
  const groups = grouped ? groupByDay(data) : [[null, data]];
  return (
    <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
      {groups.map(([day, events]) => (
        <Box key={day ?? 'all'} component="section" sx={{ display: 'flex', flexDirection: 'column', gap: 1 }}>
          {day && <Typography variant="overline" component="h2" color="text.secondary">{fmtDay(events[0].starts_at)}</Typography>}
          {events.map((e) => <EventCard key={e.id} event={e} />)}
        </Box>
      ))}
    </Box>
  );
}
