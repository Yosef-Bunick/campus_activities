import { useState } from 'react';
import Box from '@mui/material/Box';
import Button from '@mui/material/Button';
import Drawer from '@mui/material/Drawer';
import MenuItem from '@mui/material/MenuItem';
import TextField from '@mui/material/TextField';
import Typography from '@mui/material/Typography';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { apiGet, apiPost, apiPut } from '../api';

const ROLE_LABELS = {
  owner: 'Owner',
  manager: 'Manager',
  student_gov: 'Student Government',
  security: 'Security',
  student: 'Student',
};

// Bottom sheet opened by tapping a person's name. The server decides which
// buttons this viewer gets (`actions`); the server also re-checks every action.
// Open it lazily: const PersonSheet = lazy(() => import('../components/PersonSheet'))
export default function PersonSheet({ userId, open, onClose }) {
  const qc = useQueryClient();
  const key = ['person', userId];
  const { data: person, error } = useQuery({
    queryKey: key,
    queryFn: () => apiGet(`/users/${userId}`),
    enabled: open && userId != null,
  });
  const [role, setRole] = useState('');
  const refresh = () => qc.invalidateQueries({ queryKey: key });
  const ban = useMutation({
    mutationFn: () => apiPost(`/users/${userId}/${person.is_banned ? 'unban' : 'ban'}`),
    onSuccess: refresh,
  });
  const fav = useMutation({
    mutationFn: () => apiPost(`/users/${userId}/${person.is_favorite ? 'unfavorite' : 'favorite'}`),
    onSuccess: () => { refresh(); qc.invalidateQueries({ queryKey: ['favorites'] }); },
  });
  const hide = useMutation({
    mutationFn: () => apiPost(`/users/${userId}/${person.is_hidden ? 'unhide' : 'hide'}`),
    onSuccess: () => {
      refresh();
      ['events', 'favorites', 'hidden'].forEach((k) => qc.invalidateQueries({ queryKey: [k] }));
    },
  });
  const changeRole = useMutation({
    mutationFn: (newRole) => apiPut(`/users/${userId}/role`, { role: newRole }),
    onSuccess: refresh,
  });
  const actionError = ban.error || changeRole.error || fav.error || hide.error;

  return (
    <Drawer anchor="bottom" open={open} onClose={onClose} PaperProps={{ sx: { borderTopLeftRadius: 16, borderTopRightRadius: 16 } }}>
      <Box sx={{ p: 2, pb: 'calc(16px + env(safe-area-inset-bottom))', display: 'flex', flexDirection: 'column', gap: 1.5 }}>
        {error && <Typography color="error">{error.message}</Typography>}
        {person && (
          <>
            <Box>
              <Typography variant="h6" component="h2">{person.display_name || 'Unnamed'}</Typography>
              <Typography variant="body2" color="text.secondary">
                {ROLE_LABELS[person.role] || person.role}{person.is_banned ? ' · Banned' : ''}
              </Typography>
            </Box>
            <Box sx={{ display: 'flex', gap: 1 }}>
              {person.actions.favorite && (
                <Button variant={person.is_favorite ? 'contained' : 'outlined'} fullWidth disabled={fav.isPending} onClick={() => fav.mutate()}>
                  {person.is_favorite ? 'Favorited' : 'Favorite'}
                </Button>
              )}
              {person.actions.hide && (
                <Button variant={person.is_hidden ? 'contained' : 'outlined'} color="inherit" fullWidth
                  disabled={hide.isPending} onClick={() => hide.mutate()}>
                  {person.is_hidden ? 'Hidden' : 'Hide'}
                </Button>
              )}
            </Box>
            {person.actions.change_role && (
              <Box sx={{ display: 'flex', gap: 1 }}>
                <TextField
                  select
                  size="small"
                  label="Role"
                  value={role || person.role}
                  onChange={(e) => setRole(e.target.value)}
                  sx={{ flexGrow: 1 }}
                >
                  {person.assignable_roles.map((r) => (
                    <MenuItem key={r} value={r}>{ROLE_LABELS[r]}</MenuItem>
                  ))}
                </TextField>
                <Button
                  variant="contained"
                  disabled={!role || role === person.role || changeRole.isPending}
                  onClick={() => changeRole.mutate(role)}
                >
                  Change role
                </Button>
              </Box>
            )}
            {person.actions.ban && (
              <Button variant="outlined" color="error" disabled={ban.isPending} onClick={() => (person.is_banned || window.confirm(`Ban ${person.display_name}? This signs them out everywhere.`)) && ban.mutate()}>
                {person.is_banned ? 'Unban' : 'Ban'}
              </Button>
            )}
            {actionError && <Typography color="error" variant="body2">{actionError.message}</Typography>}
          </>
        )}
      </Box>
    </Drawer>
  );
}
