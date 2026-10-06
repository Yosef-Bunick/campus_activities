import { useState } from 'react';
import Box from '@mui/material/Box';
import Button from '@mui/material/Button';
import Divider from '@mui/material/Divider';
import MenuItem from '@mui/material/MenuItem';
import TextField from '@mui/material/TextField';
import Typography from '@mui/material/Typography';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { apiGet, apiPost } from '../api';

const ROLES = ['student', 'security', 'student_gov', 'manager', 'owner'];

// "/" — one "Sign in with Microsoft" button. It goes live once the Entra app is
// registered and /auth/microsoft/login exists. On localhost with DEV_LOGIN=1 a
// developer "sign in as" form appears too (ADR-023); production never shows it.
export default function SignInView() {
  const qc = useQueryClient();
  const { data: config } = useQuery({ queryKey: ['auth-config'], queryFn: () => apiGet('/auth/config') });
  const [email, setEmail] = useState('');
  const [role, setRole] = useState('student');
  const [error, setError] = useState('');

  const devSignIn = async (e) => {
    e.preventDefault();
    setError('');
    try {
      await apiPost('/auth/dev-login', { email, role });
      await qc.invalidateQueries({ queryKey: ['me'] });
    } catch (err) {
      setError(err.message);
    }
  };

  return (
    <Box sx={{ p: 3, pt: 8, display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 2, textAlign: 'center' }}>
      <Typography variant="h4" component="h1">Campus Events</Typography>
      <Typography color="text.secondary">What's happening on campus right now.</Typography>
      <Button variant="contained" size="large" disabled fullWidth sx={{ maxWidth: 320 }}>
        Sign in with Microsoft
      </Button>
      <Typography variant="caption" color="text.secondary">
        Westchester Community College accounts only.
      </Typography>
      {config?.dev_login && (
        <Box component="form" onSubmit={devSignIn}
          sx={{ width: '100%', maxWidth: 320, display: 'flex', flexDirection: 'column', gap: 1.5, mt: 2 }}>
          <Divider>Local testing only</Divider>
          <TextField size="small" type="email" label="School email" value={email}
            onChange={(e) => setEmail(e.target.value)} required />
          <TextField size="small" select label="Test as role" value={role} onChange={(e) => setRole(e.target.value)}>
            {ROLES.map((r) => <MenuItem key={r} value={r}>{r}</MenuItem>)}
          </TextField>
          <Button type="submit" variant="outlined">Sign in (dev)</Button>
          {error && <Typography color="error" variant="body2">{error}</Typography>}
        </Box>
      )}
    </Box>
  );
}
