// "Install this app" hint. Rendered in normal flow at the top of the page (under the app bar),
// so it never covers the bottom tabs or the floating "New event" button.
import { useEffect, useState } from 'react';
import Alert from '@mui/material/Alert';
import Button from '@mui/material/Button';
import IconButton from '@mui/material/IconButton';
import CloseIcon from '@mui/icons-material/esm/Close';
import IosShareIcon from '@mui/icons-material/esm/IosShare';
import { APP_NAME } from '../brand';

const KEY = 'install-hint-dismissed';
const SNOOZE_MS = 30 * 24 * 60 * 60 * 1000;

// Private mode can make localStorage throw, so every access is guarded.
function snoozed() {
  try {
    const v = localStorage.getItem(KEY);
    if (v === 'installed') return true;
    return v != null && Date.now() - Number(v) < SNOOZE_MS;
  } catch { return false; }
}
function remember(value) {
  try { localStorage.setItem(KEY, value); } catch { /* not persisted; hidden for this visit only */ }
}

function installed() {
  return window.navigator.standalone === true
    || (typeof window.matchMedia === 'function' && window.matchMedia('(display-mode: standalone)').matches);
}

// iPadOS reports itself as a Mac, so touch points tell them apart.
function isIos() {
  const n = window.navigator;
  return /iPhone|iPad|iPod/.test(n.userAgent) || (n.platform === 'MacIntel' && n.maxTouchPoints > 1);
}

export default function InstallHint() {
  const ok = typeof window !== 'undefined' && typeof navigator !== 'undefined';
  const [hidden, setHidden] = useState(() => !ok || installed() || snoozed());
  const [deferred, setDeferred] = useState(null);

  useEffect(() => {
    if (!ok) return undefined;
    // Chrome/Edge/Samsung: hold the prompt so it opens from our button, not on its own.
    const onPrompt = (e) => { e.preventDefault(); setDeferred(e); };
    const onInstalled = () => { remember('installed'); setHidden(true); };
    window.addEventListener('beforeinstallprompt', onPrompt);
    window.addEventListener('appinstalled', onInstalled);
    return () => {
      window.removeEventListener('beforeinstallprompt', onPrompt);
      window.removeEventListener('appinstalled', onInstalled);
    };
  }, [ok]);

  if (hidden) return null;
  const dismiss = () => { remember(String(Date.now())); setHidden(true); };

  if (deferred) {
    const install = () => { deferred.prompt(); setDeferred(null); setHidden(true); };
    return (
      // Alert drops its own X when given an action, so the X goes in alongside Install.
      <Alert severity="info" sx={{ m: 1 }} action={<>
        <Button color="inherit" size="small" onClick={install}>Install</Button>
        <IconButton color="inherit" size="small" aria-label="Close" onClick={dismiss}><CloseIcon fontSize="small" /></IconButton>
      </>}>
        Install {APP_NAME}
      </Alert>
    );
  }
  // iOS never offers an install prompt itself, so tell people where it is.
  if (isIos()) {
    return (
      <Alert severity="info" icon={<IosShareIcon fontSize="small" />} onClose={dismiss} sx={{ m: 1 }}>
        Install {APP_NAME}: tap Share, then Add to Home Screen
      </Alert>
    );
  }
  return null;
}
