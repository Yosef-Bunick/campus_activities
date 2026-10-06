import { useState } from 'react';
import Box from '@mui/material/Box';
import Button from '@mui/material/Button';
import TextField from '@mui/material/TextField';
import Typography from '@mui/material/Typography';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { apiPatch } from '../api';

// Managers/owner: how many events may overlap in this room before the next one
// needs approval (empty = the default from permissions.py). For the cafeteria, the quad…
export default function RoomLimit({ room, onSaved }) {
  const qc = useQueryClient();
  const [value, setValue] = useState(room.max_overlapping ?? '');
  const save = useMutation({
    mutationFn: () => apiPatch(`/rooms/${room.id}`, { max_overlapping: value === '' ? null : Number(value) }),
    onSuccess: (updated) => { qc.invalidateQueries({ queryKey: ['rooms'] }); onSaved?.(updated); },
  });
  return (
    <Box sx={{ display: 'flex', gap: 1, alignItems: 'center', mt: 1 }}>
      <TextField
        size="small" type="number" label="Max overlapping events" value={value}
        onChange={(e) => setValue(e.target.value)} placeholder="Default (2)"
        inputProps={{ min: 1, max: 50 }} sx={{ flex: 1 }}
      />
      <Button variant="outlined" disabled={save.isPending} onClick={() => save.mutate()}>Save</Button>
      {save.error && <Typography color="error" variant="caption">{save.error.message}</Typography>}
    </Box>
  );
}
