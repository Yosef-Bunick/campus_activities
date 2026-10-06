import { useState } from 'react';
import Button from '@mui/material/Button';
import Dialog from '@mui/material/Dialog';
import DialogActions from '@mui/material/DialogActions';
import DialogContent from '@mui/material/DialogContent';
import DialogTitle from '@mui/material/DialogTitle';
import TextField from '@mui/material/TextField';
import Typography from '@mui/material/Typography';
import { useMutation } from '@tanstack/react-query';
import { apiPost } from '../api';
import { useAuth } from '../contexts/AuthContext';

// Delete my account: removes you, your events, and everything you saved,
// followed or hid. Type DELETE to confirm (same guard as unified).
export default function DeleteAccountDialog({ open, onClose }) {
  const { signOut } = useAuth();
  const [typed, setTyped] = useState('');
  const del = useMutation({
    mutationFn: () => apiPost('/auth/me/delete', { confirm: typed }),
    onSuccess: signOut,
  });
  return (
    <Dialog open={open} onClose={onClose} fullWidth maxWidth="xs">
      <DialogTitle>Delete my account</DialogTitle>
      <DialogContent sx={{ display: 'flex', flexDirection: 'column', gap: 1.5 }}>
        <Typography variant="body2">
          This deletes your account, your events, and everything you saved, followed or hid. It can't be undone.
        </Typography>
        <TextField size="small" label="Type DELETE to confirm" value={typed} onChange={(e) => setTyped(e.target.value)} />
        {del.error && <Typography color="error" variant="body2">{del.error.message}</Typography>}
      </DialogContent>
      <DialogActions>
        <Button onClick={onClose}>Cancel</Button>
        <Button color="error" variant="contained" disabled={typed !== 'DELETE' || del.isPending} onClick={() => del.mutate()}>
          Delete forever
        </Button>
      </DialogActions>
    </Dialog>
  );
}
