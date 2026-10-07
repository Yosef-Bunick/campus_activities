import { useState } from 'react';
import Box from '@mui/material/Box';
import Button from '@mui/material/Button';
import Dialog from '@mui/material/Dialog';
import DialogActions from '@mui/material/DialogActions';
import DialogContent from '@mui/material/DialogContent';
import DialogTitle from '@mui/material/DialogTitle';
import MenuItem from '@mui/material/MenuItem';
import TextField from '@mui/material/TextField';
import ToggleButton from '@mui/material/ToggleButton';
import ToggleButtonGroup from '@mui/material/ToggleButtonGroup';
import Typography from '@mui/material/Typography';
import useMediaQuery from '@mui/material/useMediaQuery';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { apiPatch, apiPost } from '../api';
import { useAuth } from '../contexts/AuthContext';
import { useMajors, useRooms } from '../hooks/useEvents';
import { addDays, fmtDay, nyDateKey, nyTimeKey, nyToDate, weekday } from '../lib/time';
import { TYPE_LABEL, WHERE_LABEL, roomLabel, safeUrl } from '../lib/labels';

const TYPE_PERM = { friend_event: 'event.create.friend', club_event: 'event.create.club', main_event: 'event.create.main' };
const DAYS = ['M', 'T', 'W', 'T', 'F', 'S', 'S'];

// Create (with optional repeat) or edit one occurrence. The server checks every
// rule; if some dates conflict it lists them and the user can skip them.
export default function EventForm({ event, open, onClose }) {
  const qc = useQueryClient();
  const { can, limits } = useAuth();
  const { data: rooms = [] } = useRooms();
  const { data: majors = [] } = useMajors();
  const phone = useMediaQuery('(max-width:600px)');
  const today = nyDateKey();
  const lastDay = addDays(today, limits?.max_days_ahead ?? 90);
  const editing = Boolean(event);

  const [f, setF] = useState(() => ({
    title: event?.title ?? '',
    description: event?.description ?? '',
    majors: event?.majors ?? [],
    type: event?.type ?? 'friend_event',
    where: event?.location_kind ?? 'campus',
    room_id: event?.room?.id ?? '',
    location: event?.location ?? '',
    online_url: event?.online_url ?? '',
    date: event ? nyDateKey(event.starts_at) : today,
    start: event ? nyTimeKey(event.starts_at) : '',
    end: event ? nyTimeKey(event.ends_at) : '',
    freq: '',
    weekdays: [],
    until: '',
  }));
  const set = (k) => (e) => setF((p) => ({ ...p, [k]: e.target.value }));
  const [conflicts, setConflicts] = useState(null);

  const payload = (skip = []) => {
    const startsAt = nyToDate(f.date, f.start);
    let endsAt = nyToDate(f.date, f.end);
    if (endsAt <= startsAt) endsAt = nyToDate(addDays(f.date, 1), f.end); // ends after midnight
    const base = {
      title: f.title, description: f.description, majors: f.majors,
      location_kind: f.where,
      room_id: f.where === 'campus' ? Number(f.room_id) : null,
      location: f.where === 'off_campus' ? f.location : '',
      online_url: f.where === 'online' ? f.online_url.trim() : '',
      starts_at: startsAt.toISOString(), ends_at: endsAt.toISOString(),
    };
    if (editing) return base;
    return {
      ...base, type: f.type, skip_dates: skip,
      repeat: f.freq ? { freq: f.freq, until: f.until, weekdays: f.freq === 'daily' ? [] : f.weekdays } : null,
    };
  };

  const save = useMutation({
    mutationFn: (skip) => (editing ? apiPatch(`/events/${event.id}`, payload()) : apiPost('/events', payload(skip))),
    onSuccess: (res) => {
      qc.invalidateQueries({ queryKey: ['events'] });
      const waiting = Array.isArray(res) && res.filter((e) => e.status === 'pending_approval').length;
      if (waiting) {
        window.alert(`The room already has events at that time, so ${waiting === res.length ? 'this was' : `${waiting} date${waiting > 1 ? 's were' : ' was'}`} sent to Student Government for approval. You'll get an alert when they decide.`);
      }
      onClose();
    },
    onError: (err) => setConflicts(err.status === 409 ? err.body.conflicts : null),
  });

  const pickFreq = (freq) => setF((p) => ({
    ...p, freq, until: p.until || (freq ? addDays(p.date, 28) : ''),
    weekdays: p.weekdays.length ? p.weekdays : [weekday(p.date)],
  }));
  const placeOk = f.where === 'campus' ? Boolean(f.room_id)
    : f.where === 'off_campus' ? Boolean(f.location.trim()) : Boolean(safeUrl(f.online_url.trim()));
  const ready = f.title.trim() && placeOk && f.date && f.start && f.end && (!f.freq || f.until);

  return (
    <Dialog open={open} onClose={onClose} fullScreen={phone} fullWidth maxWidth="sm">
      <DialogTitle>{editing ? 'Edit event' : 'New event'}</DialogTitle>
      <DialogContent sx={{ display: 'flex', flexDirection: 'column', gap: 2, pt: '8px !important' }}>
        <TextField label="What's happening?" value={f.title} onChange={set('title')} inputProps={{ maxLength: 120 }} required />
        {!editing && (
          <TextField select label="Type" value={f.type} onChange={set('type')}>
            {Object.keys(TYPE_PERM).filter((t) => can(TYPE_PERM[t])).map((t) => (
              <MenuItem key={t} value={t}>{TYPE_LABEL[t]}</MenuItem>
            ))}
          </TextField>
        )}
        <ToggleButtonGroup exclusive fullWidth size="small" value={f.where} aria-label="Where"
          onChange={(_, v) => v && setF((p) => ({ ...p, where: v }))}>
          {Object.entries(WHERE_LABEL).map(([k, label]) => <ToggleButton key={k} value={k}>{label}</ToggleButton>)}
        </ToggleButtonGroup>
        {f.where === 'campus' && (
          <TextField select label="Room" value={f.room_id} onChange={set('room_id')} required>
            {rooms.map((r) => <MenuItem key={r.id} value={r.id}>{roomLabel(r)}</MenuItem>)}
          </TextField>
        )}
        {f.where === 'off_campus' && (
          <TextField label="Where off campus?" value={f.location} onChange={set('location')} required
            placeholder="e.g. Kensico Dam Plaza, Valhalla" inputProps={{ maxLength: 200 }} />
        )}
        {f.where === 'online' && (
          <TextField label="Link" value={f.online_url} onChange={set('online_url')} required type="url"
            placeholder="https://zoom.us/j/…" inputProps={{ maxLength: 500 }}
            error={Boolean(f.online_url) && !safeUrl(f.online_url.trim())}
            helperText="Zoom, Teams, Meet, Discord… must start with https://" />
        )}
        <TextField label="Date" type="date" value={f.date} onChange={set('date')}
          inputProps={{ min: today, max: lastDay }} InputLabelProps={{ shrink: true }} />
        <Box sx={{ display: 'flex', gap: 1 }}>
          <TextField label="Starts" type="time" value={f.start} onChange={set('start')} InputLabelProps={{ shrink: true }} fullWidth />
          <TextField label="Ends" type="time" value={f.end} onChange={set('end')} InputLabelProps={{ shrink: true }} fullWidth />
        </Box>
        {!editing && (
          <>
            <TextField select label="Repeat" value={f.freq} onChange={(e) => pickFreq(e.target.value)}>
              <MenuItem value="">Doesn't repeat</MenuItem>
              <MenuItem value="daily">Every day</MenuItem>
              <MenuItem value="weekly">Every week</MenuItem>
              <MenuItem value="biweekly">Every 2 weeks</MenuItem>
            </TextField>
            {(f.freq === 'weekly' || f.freq === 'biweekly') && (
              <ToggleButtonGroup
                value={f.weekdays}
                onChange={(_, v) => v.length && setF((p) => ({ ...p, weekdays: v }))}
                size="small"
                aria-label="Repeat on"
              >
                {DAYS.map((d, i) => <ToggleButton key={i} value={i} sx={{ flex: 1 }}>{d}</ToggleButton>)}
              </ToggleButtonGroup>
            )}
            {f.freq && (
              <TextField label="Repeat until" type="date" value={f.until} onChange={set('until')}
                inputProps={{ min: f.date, max: lastDay }} InputLabelProps={{ shrink: true }}
                helperText={`Your role can schedule up to ${limits?.max_days_ahead ?? 90} days ahead`} />
            )}
          </>
        )}
        <TextField
          select label="Relevant to majors (optional)" value={f.majors}
          SelectProps={{ multiple: true }}
          onChange={(e) => setF((p) => ({ ...p, majors: e.target.value.slice(0, 3) }))}
          helperText="Shows up as Recommended for those majors. Up to 3."
        >
          {majors.map((m) => <MenuItem key={m.key} value={m.key}>{m.label}</MenuItem>)}
        </TextField>
        <TextField label="Details (optional)" value={f.description} onChange={set('description')} multiline minRows={2} inputProps={{ maxLength: 2000 }} />
        {conflicts && (
          <Box role="alert" sx={{ bgcolor: 'warning.light', p: 1.5, borderRadius: 1 }}>
            <Typography variant="body2" sx={{ fontWeight: 600 }}>These dates don't work:</Typography>
            {conflicts.map((c) => (
              <Typography key={c.date} variant="body2">{fmtDay(c.starts_at)}: {c.reason}</Typography>
            ))}
          </Box>
        )}
        {save.error && !conflicts && <Typography color="error" variant="body2">{save.error.message}</Typography>}
      </DialogContent>
      <DialogActions>
        <Button onClick={onClose}>Close</Button>
        {conflicts && !editing && f.freq && (
          <Button disabled={save.isPending} onClick={() => save.mutate(conflicts.map((c) => c.date))}>
            Skip {conflicts.length} date{conflicts.length > 1 ? 's' : ''}
          </Button>
        )}
        <Button variant="contained" disabled={!ready || save.isPending} onClick={() => { setConflicts(null); save.mutate([]); }}>
          {editing ? 'Save' : 'Post'}
        </Button>
      </DialogActions>
    </Dialog>
  );
}
