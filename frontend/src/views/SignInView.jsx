import { useState } from 'react';
import Box from '@mui/material/Box';
import Button from '@mui/material/Button';
import Divider from '@mui/material/Divider';
import MenuItem from '@mui/material/MenuItem';
import TextField from '@mui/material/TextField';
import Typography from '@mui/material/Typography';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { useSearch } from 'wouter';
import { API_BASE, apiGet, apiPost } from '../api';
import { APP_NAME } from '../brand';

const ROLES = ['student', 'security', 'student_gov', 'manager', 'owner'];

// "/" — one "Sign in with Microsoft" button: a plain link to the API, which
// redirects to Microsoft and back (ADR-029). It's enabled once the API reports
// the Entra keys are set. On localhost with DEV_LOGIN=1 a developer
// "sign in as" form appears too (ADR-023); production never shows it.
export default function SignInView() {
  const qc = useQueryClient();
  const { data: config } = useQuery({ queryKey: ['auth-config'], queryFn: () => apiGet('/auth/config') });
  const [email, setEmail] = useState('');
  const [role, setRole] = useState('student');
  const [error, setError] = useState('');
  const signinError = new URLSearchParams(useSearch()).get('signin_error');

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
      <Typography variant="h4" component="h1">{APP_NAME}</Typography>
      <Typography color="text.secondary">What's happening on campus right now.</Typography>
      <Button
        variant="contained" size="large" fullWidth sx={{ maxWidth: 320 }}
        disabled={!config?.microsoft}
        href={`${API_BASE}/auth/microsoft/login`}
      >
        Sign in with Microsoft
      </Button>
      {signinError && <Typography color="error" role="alert" sx={{ maxWidth: 320 }}>{signinError}</Typography>}
      {config && !config.microsoft && (
        <Typography variant="caption" color="text.secondary">Microsoft sign-in isn't set up yet.</Typography>
      )}
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
