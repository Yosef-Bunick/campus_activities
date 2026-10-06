import { useState } from 'react';
import Button from '@mui/material/Button';
import Dialog from '@mui/material/Dialog';
import DialogActions from '@mui/material/DialogActions';
import DialogContent from '@mui/material/DialogContent';
import DialogTitle from '@mui/material/DialogTitle';
import MenuItem from '@mui/material/MenuItem';
import TextField from '@mui/material/TextField';
import Typography from '@mui/material/Typography';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { apiPut } from '../api';
import { useAuth } from '../contexts/AuthContext';
import { useMajors } from '../hooks/useEvents';

// Pick your major: Recommended shows main events + events tagged for it (ADR-028).
export default function MajorDialog({ open, onClose }) {
  const qc = useQueryClient();
  const { user } = useAuth();
  const { data: majors = [] } = useMajors();
  const [major, setMajor] = useState(user?.major ?? '');
  const save = useMutation({
    mutationFn: () => apiPut('/auth/me/major', { major: major || null }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['me'] });
      qc.invalidateQueries({ queryKey: ['events'] });
      onClose();
    },
  });
  return (
    <Dialog open={open} onClose={onClose} fullWidth maxWidth="xs">
      <DialogTitle>Your major</DialogTitle>
      <DialogContent sx={{ pt: '8px !important' }}>
        <TextField select fullWidth label="Major" value={major} onChange={(e) => setMajor(e.target.value)}>
          <MenuItem value="">Not set</MenuItem>
          {majors.map((m) => <MenuItem key={m.key} value={m.key}>{m.label}</MenuItem>)}
        </TextField>
        <Typography variant="body2" color="text.secondary" sx={{ mt: 1.5 }}>
          Recommended shows campus-wide events plus events tagged for your major.
        </Typography>
        {save.error && <Typography color="error" variant="body2">{save.error.message}</Typography>}
      </DialogContent>
      <DialogActions>
        <Button onClick={onClose}>Cancel</Button>
        <Button variant="contained" disabled={save.isPending} onClick={() => save.mutate()}>Save</Button>
      </DialogActions>
    </Dialog>
  );
}
