import Box from '@mui/material/Box';
import Button from '@mui/material/Button';
import CircularProgress from '@mui/material/CircularProgress';
import List from '@mui/material/List';
import ListItem from '@mui/material/ListItem';
import ListItemText from '@mui/material/ListItemText';
import Typography from '@mui/material/Typography';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { apiGet, apiPost } from '../api';
import { roomLabel } from '../lib/labels';
import { fmtDay, fmtTime } from '../lib/time';

// People and events you've hidden, each with Unhide (architecture §3).
export default function HiddenView() {
  const qc = useQueryClient();
  const { data, isPending, error } = useQuery({ queryKey: ['hidden'], queryFn: () => apiGet('/hidden') });
  const unhide = useMutation({
    mutationFn: (path) => apiPost(path),
    onSuccess: () => ['hidden', 'events', 'favorites'].forEach((k) => qc.invalidateQueries({ queryKey: [k] })),
  });
  const button = (path) => (
    <Button size="small" disabled={unhide.isPending} onClick={() => unhide.mutate(path)}>Unhide</Button>
  );

  if (isPending) return <Box sx={{ display: 'flex', justifyContent: 'center', p: 3 }}><CircularProgress size={24} /></Box>;
  if (error) return <Typography color="error" sx={{ p: 2 }}>{error.message}</Typography>;
  return (
    <Box sx={{ p: 2, display: 'flex', flexDirection: 'column', gap: 1 }}>
      <Typography variant="h5" component="h1">Hidden</Typography>
      <Typography variant="overline" component="h2" color="text.secondary">People</Typography>
      {data.people.length ? (
        <List dense disablePadding>
          {data.people.map((p) => (
            <ListItem key={p.id} divider secondaryAction={button(`/users/${p.id}/unhide`)}>
              <ListItemText primary={p.display_name || 'Someone'} />
            </ListItem>
          ))}
        </List>
      ) : <Typography color="text.secondary" variant="body2">Nobody hidden.</Typography>}

      <Typography variant="overline" component="h2" color="text.secondary" sx={{ mt: 2 }}>Events</Typography>
      {data.events.length ? (
        <List dense disablePadding>
          {data.events.map((e) => (
            <ListItem key={`${e.hidden}-${e.id}`} divider secondaryAction={button(`/events/${e.id}/unhide`)}>
              <ListItemText
                primary={e.hidden === 'series' ? `${e.title} (all dates)` : e.title}
                secondary={`${fmtDay(e.starts_at)} ${fmtTime(e.starts_at)} · ${roomLabel(e.room)}`}
              />
            </ListItem>
          ))}
        </List>
      ) : <Typography color="text.secondary" variant="body2">No hidden events.</Typography>}
    </Box>
  );
}
