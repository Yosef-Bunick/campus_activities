import { lazy, Suspense, useState } from 'react';
import AppBar from '@mui/material/AppBar';
import Toolbar from '@mui/material/Toolbar';
import Typography from '@mui/material/Typography';
import IconButton from '@mui/material/IconButton';
import Menu from '@mui/material/Menu';
import MenuItem from '@mui/material/MenuItem';
import AccountIcon from '@mui/icons-material/esm/AccountCircleOutlined';
import { useLocation } from 'wouter';
import ApiStatus from './ApiStatus';
import { useAuth } from '../contexts/AuthContext';

const MajorDialog = lazy(() => import('./MajorDialog'));

// Top bar with the profile menu. /hidden lives here, not in the tab bar (architecture §3).
export default function TopBar({ showProfile }) {
  const [, navigate] = useLocation();
  const [anchor, setAnchor] = useState(null);
  const { user, signOut } = useAuth();
  const [majorOpen, setMajorOpen] = useState(false);
  const go = (path) => { setAnchor(null); navigate(path); };
  return (
    <AppBar position="sticky" elevation={0} sx={{ pt: 'env(safe-area-inset-top)' }}>
      <Toolbar variant="dense" sx={{ gap: 1.5 }}>
        <Typography variant="h6" component="span" sx={{ flexGrow: 1, fontSize: '1.1rem' }}>
          Campus Events
        </Typography>
        <ApiStatus />
        {showProfile && (
          <>
            <IconButton color="inherit" edge="end" aria-label="Profile menu" onClick={(e) => setAnchor(e.currentTarget)}>
              <AccountIcon />
            </IconButton>
            <Menu anchorEl={anchor} open={Boolean(anchor)} onClose={() => setAnchor(null)}>
              {user && <MenuItem disabled>{user.display_name || user.email}</MenuItem>}
              <MenuItem onClick={() => { setAnchor(null); setMajorOpen(true); }}>Your major</MenuItem>
              <MenuItem onClick={() => go('/hidden')}>Hidden</MenuItem>
              <MenuItem onClick={async () => { setAnchor(null); await signOut(); navigate('/'); }}>Sign out</MenuItem>
            </Menu>
          </>
        )}
      </Toolbar>
      <Suspense fallback={null}>
        {majorOpen && <MajorDialog open onClose={() => setMajorOpen(false)} />}
      </Suspense>
    </AppBar>
  );
}
