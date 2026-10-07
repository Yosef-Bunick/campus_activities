import { useState } from 'react';
import Button from '@mui/material/Button';
import Dialog from '@mui/material/Dialog';
import DialogActions from '@mui/material/DialogActions';
import DialogContent from '@mui/material/DialogContent';
import DialogTitle from '@mui/material/DialogTitle';
import FormControlLabel from '@mui/material/FormControlLabel';
import Radio from '@mui/material/Radio';
import RadioGroup from '@mui/material/RadioGroup';
import TextField from '@mui/material/TextField';
import Typography from '@mui/material/Typography';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { apiPost } from '../api';
import { useAuth } from '../contexts/AuthContext';
import { fmtDay } from '../lib/time';
import { optimistic, sameEventOrSeries } from '../lib/optimistic';

// One-off event: "Cancel event". Part of a series: only this date / this and
// future / whole series (architecture §7). Past dates are never changed.
export default function CancelDialog({ event, open, onClose }) {
  const qc = useQueryClient();
  const { user } = useAuth();
  const [scope, setScope] = useState('this');
  const [reason, setReason] = useState('');
  const cancel = useMutation({
    mutationFn: () => apiPost(`/events/${event.id}/cancel`, { scope, reason }),
    // Crossed out at once (ADR-033); the dialog closes without waiting.
    ...optimistic(qc, (e) => sameEventOrSeries(event, scope)(e), (e) => ({ ...e, status: 'cancelled' })),
  });
  const someoneElses = user?.id !== event.creator?.id;

  return (
    <Dialog open={open} onClose={onClose} fullWidth maxWidth="xs">
      <DialogTitle>{event.series_id ? 'Cancel recurring event' : 'Cancel event'}</DialogTitle>
      <DialogContent sx={{ display: 'flex', flexDirection: 'column', gap: 1.5 }}>
        <Typography variant="body2">“{event.title}” · {fmtDay(event.starts_at)}</Typography>
        {event.series_id && (
          <RadioGroup value={scope} onChange={(e) => setScope(e.target.value)}>
            <FormControlLabel value="this" control={<Radio />} label="Only this date" />
            <FormControlLabel value="future" control={<Radio />} label="This and all future dates" />
            <FormControlLabel value="series" control={<Radio />} label="The whole series" />
          </RadioGroup>
        )}
        {someoneElses && (
          <TextField
            label="Reason (sent to the creator)"
            size="small"
            value={reason}
            onChange={(e) => setReason(e.target.value)}
            inputProps={{ maxLength: 300 }}
          />
        )}
        {cancel.error && <Typography color="error" variant="body2">{cancel.error.message}</Typography>}
      </DialogContent>
      <DialogActions>
        <Button onClick={onClose}>Keep it</Button>
        <Button color="error" variant="contained" disabled={cancel.isPending} onClick={() => { cancel.mutate(); onClose(); }}>
          Confirm
        </Button>
      </DialogActions>
    </Dialog>
  );
}
