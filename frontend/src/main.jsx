import { StrictMode, useMemo } from 'react';
import { createRoot } from 'react-dom/client';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { ThemeProvider, createTheme } from '@mui/material/styles';
import CssBaseline from '@mui/material/CssBaseline';
import useMediaQuery from '@mui/material/useMediaQuery';
import App from './App';
import { AuthProvider } from './contexts/AuthContext';

const queryClient = new QueryClient({ defaultOptions: { queries: { staleTime: 30000, refetchOnWindowFocus: false } } });

// Light/dark follows the phone/laptop setting, live. noSsr: right mode on the
// first render, so no light flash.
function Themed({ children }) {
  const dark = useMediaQuery('(prefers-color-scheme: dark)', { noSsr: true });
  const theme = useMemo(() => createTheme({
    palette: dark ? { mode: 'dark', primary: { main: '#90caf9' } } : { primary: { main: '#1976d2' } },
  }), [dark]);
  return <ThemeProvider theme={theme}>{children}</ThemeProvider>;
}

createRoot(document.getElementById('root')).render(
  <StrictMode>
    <QueryClientProvider client={queryClient}>
      <Themed>
        <CssBaseline />
        <AuthProvider>
          <App />
        </AuthProvider>
      </Themed>
    </QueryClientProvider>
  </StrictMode>
);

// Error reports (ADR-030): only when VITE_SENTRY_DSN is set, and loaded with a
// dynamic import so Sentry never counts against the first-load budget.
const sentryDsn = import.meta.env.VITE_SENTRY_DSN;
if (sentryDsn) {
  import('@sentry/react').then((Sentry) => Sentry.init({
    dsn: sentryDsn,
    tracesSampleRate: 0.1,
    sendDefaultPii: false,
    environment: import.meta.env.VITE_SENTRY_ENVIRONMENT || 'production',
  }));
}

// Stale chunk after a deploy (old index.html asks for an old hash): reload
// instead of showing a blank page. Copied from unified's main.jsx (F3).
window.addEventListener('vite:preloadError', () => {
  window.location.reload();
});
