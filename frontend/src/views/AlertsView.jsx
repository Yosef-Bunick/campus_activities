import Box from '@mui/material/Box';
import Button from '@mui/material/Button';
import CircularProgress from '@mui/material/CircularProgress';
import List from '@mui/material/List';
import ListItemButton from '@mui/material/ListItemButton';
import ListItemText from '@mui/material/ListItemText';
import Typography from '@mui/material/Typography';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { apiGet, apiPost } from '../api';
import { fmtDay, fmtTime } from '../lib/time';

// Your notices ("your event was cancelled by…"), newest first. Tap to mark read.
export default function AlertsView() {
  const qc = useQueryClient();
  const { data, isPending, error } = useQuery({ queryKey: ['alerts'], queryFn: () => apiGet('/alerts'), refetchInterval: 60000 });
  const read = useMutation({
    mutationFn: (path) => apiPost(path),
    onSuccess: (res) => {
      qc.setQueryData(['alerts-unread'], res);
      qc.invalidateQueries({ queryKey: ['alerts'] });
    },
  });

  if (isPending) return <Box sx={{ display: 'flex', justifyContent: 'center', p: 3 }}><CircularProgress size={24} /></Box>;
  if (error) return <Typography color="error" sx={{ p: 2 }}>{error.message}</Typography>;
  return (
    <Box sx={{ p: 2, display: 'flex', flexDirection: 'column', gap: 1 }}>
      <Box sx={{ display: 'flex', alignItems: 'center' }}>
        <Typography variant="h5" component="h1" sx={{ flexGrow: 1 }}>Alerts</Typography>
        {data.unread > 0 && (
          <Button size="small" disabled={read.isPending} onClick={() => read.mutate('/alerts/read-all')}>Mark all read</Button>
        )}
      </Box>
      {data.alerts.length ? (
        <List disablePadding>
          {data.alerts.map((a) => (
            <ListItemButton
              key={a.id}
              divider
              onClick={() => !a.read && read.mutate(`/alerts/${a.id}/read`)}
              sx={{ alignItems: 'flex-start', bgcolor: a.read ? 'transparent' : 'action.hover' }}
            >
              <ListItemText
                primary={a.message}
                primaryTypographyProps={{ fontWeight: a.read ? 400 : 600 }}
                secondary={`${fmtDay(a.created_at)} ${fmtTime(a.created_at)}${a.read ? '' : ' · New'}`}
              />
            </ListItemButton>
          ))}
        </List>
      ) : <Typography color="text.secondary">No alerts yet.</Typography>}
    </Box>
  );
}
