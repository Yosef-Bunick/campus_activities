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
import { APP_NAME } from '../brand';

// Dialogs download only when opened.
const DIALOGS = {
  major: lazy(() => import('./MajorDialog')),
  modlog: lazy(() => import('./ModLogDialog')),
  delete: lazy(() => import('./DeleteAccountDialog')),
};

// Top bar with the profile menu. /hidden lives here, not in the tab bar (architecture §3).
export default function TopBar({ showProfile }) {
  const [, navigate] = useLocation();
  const [anchor, setAnchor] = useState(null);
  const { user, signOut, can } = useAuth();
  const [dialog, setDialog] = useState(null);
  const go = (path) => { setAnchor(null); navigate(path); };
  const open = (name) => { setAnchor(null); setDialog(name); };
  const Dialog = dialog && DIALOGS[dialog];
  return (
    <AppBar position="sticky" elevation={0} sx={{ pt: 'env(safe-area-inset-top)' }}>
      <Toolbar variant="dense" sx={{ gap: 1.5 }}>
        <Typography variant="h6" component="span" sx={{ flexGrow: 1, fontSize: '1.1rem' }}>
          {APP_NAME}
        </Typography>
        <ApiStatus />
        {showProfile && (
          <>
            <IconButton color="inherit" edge="end" aria-label="Profile menu" onClick={(e) => setAnchor(e.currentTarget)}>
              <AccountIcon />
            </IconButton>
            <Menu anchorEl={anchor} open={Boolean(anchor)} onClose={() => setAnchor(null)}>
              {user && <MenuItem disabled>{user.display_name || user.email}</MenuItem>}
              <MenuItem onClick={() => open('major')}>Your major</MenuItem>
              <MenuItem onClick={() => go('/hidden')}>Hidden</MenuItem>
              {can('modlog.view') && <MenuItem onClick={() => open('modlog')}>Moderation log</MenuItem>}
              <MenuItem onClick={async () => { setAnchor(null); await signOut(); navigate('/'); }}>Sign out</MenuItem>
              <MenuItem onClick={() => open('delete')} sx={{ color: 'error.main' }}>Delete my account</MenuItem>
            </Menu>
          </>
        )}
      </Toolbar>
      <Suspense fallback={null}>
        {Dialog && <Dialog open onClose={() => setDialog(null)} />}
      </Suspense>
    </AppBar>
  );
}
