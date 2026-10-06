import Button from '@mui/material/Button';
import Dialog from '@mui/material/Dialog';
import DialogActions from '@mui/material/DialogActions';
import DialogContent from '@mui/material/DialogContent';
import DialogTitle from '@mui/material/DialogTitle';
import Typography from '@mui/material/Typography';
import { useMutation } from '@tanstack/react-query';
import { apiPost } from '../api';
import { useAuth } from '../contexts/AuthContext';

// The short terms / privacy note at first sign-in (text lives in backend core/terms.py).
export default function TermsDialog() {
  const { terms, refresh, signOut } = useAuth();
  const accept = useMutation({
    mutationFn: () => apiPost('/auth/me/accept-terms', { version: terms.version }),
    onSuccess: refresh,
  });
  return (
    <Dialog open disableEscapeKeyDown fullWidth maxWidth="sm" aria-labelledby="terms-title">
      <DialogTitle id="terms-title">Before you start</DialogTitle>
      <DialogContent sx={{ display: 'flex', flexDirection: 'column', gap: 1.5 }}>
        {terms.items.map((t) => <Typography key={t} variant="body2">• {t}</Typography>)}
        {accept.error && <Typography color="error" variant="body2">{accept.error.message}</Typography>}
      </DialogContent>
      <DialogActions>
        <Button color="inherit" onClick={signOut}>No thanks</Button>
        <Button variant="contained" disabled={accept.isPending} onClick={() => accept.mutate()}>I agree</Button>
      </DialogActions>
    </Dialog>
  );
}
