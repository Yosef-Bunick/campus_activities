import { lazy, Suspense, useState } from 'react';
import Box from '@mui/material/Box';
import Button from '@mui/material/Button';
import Card from '@mui/material/Card';
import CardActionArea from '@mui/material/CardActionArea';
import Chip from '@mui/material/Chip';
import IconButton from '@mui/material/IconButton';
import Link from '@mui/material/Link';
import Menu from '@mui/material/Menu';
import MenuItem from '@mui/material/MenuItem';
import Typography from '@mui/material/Typography';
import StarIcon from '@mui/icons-material/esm/Star';
import StarBorderIcon from '@mui/icons-material/esm/StarBorder';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { apiPost } from '../api';
import { useAuth } from '../contexts/AuthContext';
import { downloadIcs, googleCalendarUrl } from '../lib/calendarLinks';
import { fmtTime } from '../lib/time';
import { TYPE_LABEL, roomLabel } from '../lib/labels';

// Dialogs download only when someone opens one.
const PersonSheet = lazy(() => import('./PersonSheet'));
const CancelDialog = lazy(() => import('./CancelDialog'));
const EventForm = lazy(() => import('./EventForm'));

const TYPE_COLOR = { main_event: 'primary', club_event: 'secondary', friend_event: 'success' };

export default function EventCard({ event, showDate = false }) {
  const qc = useQueryClient();
  const { user, can } = useAuth();
  const [open, setOpen] = useState(false);
  const [dialog, setDialog] = useState(null); // 'person' | 'cancel' | 'edit'
  const [menu, setMenu] = useState(null); // { anchor, kind: 'save' | 'calendar' }
  const cancelled = event.status === 'cancelled';
  const mine = user?.id === event.creator?.id;
  const over = new Date(event.ends_at) <= new Date();
  const canCancel = !cancelled && !over && (mine || can('event.cancel_any'));
  const canEdit = !cancelled && !over && (mine || can('event.edit_any'));

  const refresh = () => {
    qc.invalidateQueries({ queryKey: ['events'] });
    qc.invalidateQueries({ queryKey: ['favorites'] });
  };
  const save = useMutation({
    mutationFn: (scope) => (scope ? apiPost(`/events/${event.id}/save`, { scope }) : apiPost(`/events/${event.id}/unsave`)),
    onSuccess: refresh,
  });
  const onStar = (e) => {
    if (event.saved) save.mutate(null);
    else if (event.series_id) setMenu({ anchor: e.currentTarget, kind: 'save' });
    else save.mutate('this');
  };
  const close = () => setMenu(null);

  return (
    <Card variant="outlined" sx={{ opacity: cancelled ? 0.6 : 1, display: 'flex', flexDirection: 'column' }}>
      <Box sx={{ display: 'flex', alignItems: 'flex-start' }}>
        <CardActionArea onClick={() => setOpen((o) => !o)} sx={{ p: 1.5, flex: 1, minWidth: 0 }} aria-expanded={open}>
          <Box sx={{ display: 'flex', justifyContent: 'space-between', gap: 1, alignItems: 'baseline' }}>
            <Typography
              variant="subtitle1"
              component="h3"
              sx={{ fontWeight: 600, textDecoration: cancelled ? 'line-through' : 'none', minWidth: 0 }}
            >
              {event.title}
            </Typography>
            <Chip size="small" label={TYPE_LABEL[event.type]} color={TYPE_COLOR[event.type]} variant="outlined" />
          </Box>
          <Typography variant="body2" color="text.secondary">
            {showDate && `${new Date(event.starts_at).toLocaleDateString('en-US', { timeZone: 'America/New_York', weekday: 'short', month: 'short', day: 'numeric' })} · `}
            {fmtTime(event.starts_at)} – {fmtTime(event.ends_at)} · {roomLabel(event.room)}
            {cancelled && ' · Cancelled'}
          </Typography>
        </CardActionArea>
        <IconButton
          aria-label={event.saved ? 'Unsave' : 'Save'}
          aria-pressed={Boolean(event.saved)}
          onClick={onStar}
          disabled={save.isPending}
          sx={{ mt: 0.5, mr: 0.5 }}
        >
          {event.saved ? <StarIcon color="warning" /> : <StarBorderIcon />}
        </IconButton>
      </Box>
      {open && (
        <Box sx={{ px: 1.5, pb: 1.5, display: 'flex', flexDirection: 'column', gap: 1 }}>
          {event.description && <Typography variant="body2">{event.description}</Typography>}
          {cancelled && event.cancelled_reason && (
            <Typography variant="body2" color="error">{event.cancelled_reason}</Typography>
          )}
          {event.creator && (
            <Typography variant="body2" color="text.secondary">
              By{' '}
              <Link component="button" variant="body2" onClick={() => setDialog('person')}>
                {event.creator.display_name || 'someone'}
              </Link>
            </Typography>
          )}
          <Box sx={{ display: 'flex', gap: 1, flexWrap: 'wrap' }}>
            {!cancelled && !over && (
              <Button size="small" variant="outlined" onClick={(e) => setMenu({ anchor: e.currentTarget, kind: 'calendar' })}>
                Add to calendar
              </Button>
            )}
            {canEdit && <Button size="small" variant="outlined" onClick={() => setDialog('edit')}>Edit</Button>}
            {canCancel && (
              <Button size="small" color="error" variant="outlined" onClick={() => setDialog('cancel')}>
                {event.series_id ? 'Cancel…' : 'Cancel event'}
              </Button>
            )}
          </Box>
        </Box>
      )}
      <Menu anchorEl={menu?.anchor} open={Boolean(menu)} onClose={close}>
        {menu?.kind === 'save' && [
          <MenuItem key="this" onClick={() => { close(); save.mutate('this'); }}>Save this date</MenuItem>,
          <MenuItem key="series" onClick={() => { close(); save.mutate('series'); }}>Save all dates</MenuItem>,
        ]}
        {menu?.kind === 'calendar' && [
          <MenuItem key="ics" onClick={() => { close(); downloadIcs(event); }}>Apple / Outlook / other (.ics)</MenuItem>,
          <MenuItem key="google" component="a" href={googleCalendarUrl(event)} target="_blank" rel="noopener noreferrer" onClick={close}>
            Google Calendar
          </MenuItem>,
        ]}
      </Menu>
      <Suspense fallback={null}>
        {dialog === 'person' && <PersonSheet userId={event.creator.id} open onClose={() => setDialog(null)} />}
        {dialog === 'cancel' && <CancelDialog event={event} open onClose={() => setDialog(null)} />}
        {dialog === 'edit' && <EventForm event={event} open onClose={() => setDialog(null)} />}
      </Suspense>
    </Card>
  );
}
