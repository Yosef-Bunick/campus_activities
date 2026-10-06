import Box from '@mui/material/Box';
import Button from '@mui/material/Button';
import Checkbox from '@mui/material/Checkbox';
import Drawer from '@mui/material/Drawer';
import FormControlLabel from '@mui/material/FormControlLabel';
import MenuItem from '@mui/material/MenuItem';
import TextField from '@mui/material/TextField';
import Typography from '@mui/material/Typography';
import { EVENT_TYPES, useFilter } from '../contexts/FilterContext';
import { useRooms } from '../hooks/useEvents';
import { TYPE_LABEL, roomLabel } from '../lib/labels';

// The shared filter as a bottom sheet (phones). Same filter drives Calendar and Map.
export default function FilterSheet({ open, onClose }) {
  const { filter, setFilter, reset } = useFilter();
  const { data: rooms = [] } = useRooms();
  const toggleType = (t) => {
    const types = filter.types.includes(t) ? filter.types.filter((x) => x !== t) : [...filter.types, t];
    if (types.length) setFilter({ types });
  };
  return (
    <Drawer anchor="bottom" open={open} onClose={onClose} PaperProps={{ sx: { borderTopLeftRadius: 16, borderTopRightRadius: 16 } }}>
      <Box sx={{ p: 2, pb: 'calc(16px + env(safe-area-inset-bottom))', display: 'flex', flexDirection: 'column', gap: 1.5 }}>
        <Typography variant="h6" component="h2">Filter</Typography>
        <TextField size="small" label="Search" value={filter.q} onChange={(e) => setFilter({ q: e.target.value })} />
        <Box>
          {EVENT_TYPES.map((t) => (
            <FormControlLabel key={t} label={TYPE_LABEL[t]}
              control={<Checkbox checked={filter.types.includes(t)} onChange={() => toggleType(t)} />} />
          ))}
        </Box>
        <TextField
          select size="small" label="Rooms"
          SelectProps={{ multiple: true }}
          value={filter.rooms}
          onChange={(e) => setFilter({ rooms: e.target.value })}
        >
          {rooms.map((r) => <MenuItem key={r.id} value={r.id}>{roomLabel(r)}</MenuItem>)}
        </TextField>
        <Box sx={{ display: 'flex', gap: 1 }}>
          <Button onClick={reset}>Clear</Button>
          <Button variant="contained" onClick={onClose} sx={{ ml: 'auto' }}>Done</Button>
        </Box>
      </Box>
    </Drawer>
  );
}
