import { useSyncExternalStore } from 'react';
import Box from '@mui/material/Box';
import Typography from '@mui/material/Typography';
import { useHealth } from '../hooks/useHealth';

const subscribe = (cb) => {
  window.addEventListener('online', cb);
  window.addEventListener('offline', cb);
  return () => { window.removeEventListener('online', cb); window.removeEventListener('offline', cb); };
};
const isOnline = () => navigator.onLine;

// Tiny dot in the top bar: can we reach the API? With no signal it says
// "Offline" and the app shows the last events it loaded (ADR-031).
export default function ApiStatus() {
  const online = useSyncExternalStore(subscribe, isOnline, () => true);
  const { data, isPending, isError } = useHealth();
  const ok = data?.status === 'ok';
  const label = !online ? 'Offline · saved copy' : isPending ? 'API…' : ok ? 'API ok' : 'API down';
  const color = !online ? 'warning.light' : isPending ? 'grey.400' : ok && !isError ? 'success.light' : 'error.light';
  return (
    <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.75 }} role="status" aria-label={label}>
      <Box sx={{ width: 8, height: 8, borderRadius: '50%', bgcolor: color }} />
      <Typography variant="caption">{label}</Typography>
    </Box>
  );
}
