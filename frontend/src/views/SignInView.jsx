import Box from '@mui/material/Box';
import Button from '@mui/material/Button';
import Typography from '@mui/material/Typography';
import { Link } from 'wouter';

// "/" — one "Sign in with Microsoft" button (wired up in Milestone 1).
export default function SignInView() {
  return (
    <Box sx={{ p: 3, pt: 8, display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 2, textAlign: 'center' }}>
      <Typography variant="h4" component="h1">Campus Events</Typography>
      <Typography color="text.secondary">What's happening on campus right now.</Typography>
      <Button variant="contained" size="large" disabled fullWidth sx={{ maxWidth: 320 }}>
        Sign in with Microsoft
      </Button>
      <Typography variant="caption" color="text.secondary">
        Sign-in arrives in Milestone 1. <Link href="/home">Continue to the app</Link>
      </Typography>
    </Box>
  );
}
