import { lazy, Suspense, useState } from 'react';
import Box from '@mui/material/Box';
import Button from '@mui/material/Button';
import Card from '@mui/material/Card';
import CardActionArea from '@mui/material/CardActionArea';
import Chip from '@mui/material/Chip';
import Link from '@mui/material/Link';
import Typography from '@mui/material/Typography';
import { useAuth } from '../contexts/AuthContext';
import { fmtTime } from '../lib/time';

// Dialogs download only when someone opens one.
const PersonSheet = lazy(() => import('./PersonSheet'));
const CancelDialog = lazy(() => import('./CancelDialog'));
const EventForm = lazy(() => import('./EventForm'));

export const TYPE_LABEL = { main_event: 'Campus', club_event: 'Club', friend_event: 'Friends' };
const TYPE_COLOR = { main_event: 'primary', club_event: 'secondary', friend_event: 'success' };

export function roomLabel(room) {
  if (!room) return '';
  return [room.building, `Room ${room.name}`].filter(Boolean).join(' · ');
}

export default function EventCard({ event }) {
  const { user, can } = useAuth();
  const [open, setOpen] = useState(false);
  const [dialog, setDialog] = useState(null); // 'person' | 'cancel' | 'edit'
  const cancelled = event.status === 'cancelled';
  const mine = user?.id === event.creator?.id;
  const over = new Date(event.ends_at) <= new Date();
  const canCancel = !cancelled && !over && (mine || can('event.cancel_any'));
  const canEdit = !cancelled && !over && (mine || can('event.edit_any'));

  return (
    <Card variant="outlined" sx={{ opacity: cancelled ? 0.6 : 1 }}>
      <CardActionArea onClick={() => setOpen((o) => !o)} sx={{ p: 1.5 }} aria-expanded={open}>
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
          {fmtTime(event.starts_at)} – {fmtTime(event.ends_at)} · {roomLabel(event.room)}
          {cancelled && ' · Cancelled'}
        </Typography>
      </CardActionArea>
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
          {(canEdit || canCancel) && (
            <Box sx={{ display: 'flex', gap: 1 }}>
              {canEdit && <Button size="small" variant="outlined" onClick={() => setDialog('edit')}>Edit</Button>}
              {canCancel && (
                <Button size="small" color="error" variant="outlined" onClick={() => setDialog('cancel')}>
                  {event.series_id ? 'Cancel…' : 'Cancel event'}
                </Button>
              )}
            </Box>
          )}
        </Box>
      )}
      <Suspense fallback={null}>
        {dialog === 'person' && <PersonSheet userId={event.creator.id} open onClose={() => setDialog(null)} />}
        {dialog === 'cancel' && <CancelDialog event={event} open onClose={() => setDialog(null)} />}
        {dialog === 'edit' && <EventForm event={event} open onClose={() => setDialog(null)} />}
      </Suspense>
    </Card>
  );
}
