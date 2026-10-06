import Button from '@mui/material/Button';
import CircularProgress from '@mui/material/CircularProgress';
import Dialog from '@mui/material/Dialog';
import DialogActions from '@mui/material/DialogActions';
import DialogContent from '@mui/material/DialogContent';
import DialogTitle from '@mui/material/DialogTitle';
import List from '@mui/material/List';
import ListItem from '@mui/material/ListItem';
import ListItemText from '@mui/material/ListItemText';
import Typography from '@mui/material/Typography';
import useMediaQuery from '@mui/material/useMediaQuery';
import { useQuery } from '@tanstack/react-query';
import { apiGet } from '../api';
import { fmtDay, fmtTime } from '../lib/time';

// Moderation log (owner, manager, security): bans, role changes, cancels,
// approvals, reports and automatic flags, newest first.
export default function ModLogDialog({ open, onClose }) {
  const phone = useMediaQuery('(max-width:600px)');
  const { data, isPending, error } = useQuery({ queryKey: ['modlog'], queryFn: () => apiGet('/modlog') });
  return (
    <Dialog open={open} onClose={onClose} fullScreen={phone} fullWidth maxWidth="sm">
      <DialogTitle>Moderation log</DialogTitle>
      <DialogContent dividers>
        {isPending && <CircularProgress size={24} />}
        {error && <Typography color="error">{error.message}</Typography>}
        {data && !data.length && <Typography color="text.secondary">Nothing yet.</Typography>}
        {data?.length > 0 && (
          <List dense disablePadding>
            {data.map((e) => (
              <ListItem key={e.id} divider disableGutters>
                <ListItemText
                  primary={e.detail}
                  secondary={`${e.actor} · ${e.action.replace('_', ' ')} · ${fmtDay(e.created_at)} ${fmtTime(e.created_at)}`}
                />
              </ListItem>
            ))}
          </List>
        )}
      </DialogContent>
      <DialogActions><Button onClick={onClose}>Close</Button></DialogActions>
    </Dialog>
  );
}
