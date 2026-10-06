import Box from '@mui/material/Box';
import Typography from '@mui/material/Typography';
import { useHealth } from '../hooks/useHealth';

// Tiny dot in the top bar: proves the frontend can reach the API's /health.
export default function ApiStatus() {
  const { data, isPending, isError } = useHealth();
  const ok = data?.status === 'ok';
  const label = isPending ? 'API…' : ok ? 'API ok' : 'API down';
  const color = isPending ? 'grey.400' : ok && !isError ? 'success.light' : 'error.light';
  return (
    <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.75 }} role="status" aria-label={label}>
      <Box sx={{ width: 8, height: 8, borderRadius: '50%', bgcolor: color }} />
      <Typography variant="caption">{label}</Typography>
    </Box>
  );
}
