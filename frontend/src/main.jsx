import { StrictMode } from 'react';
import { createRoot } from 'react-dom/client';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { ThemeProvider, createTheme } from '@mui/material/styles';
import CssBaseline from '@mui/material/CssBaseline';
import App from './App';
import { AuthProvider } from './contexts/AuthContext';

const queryClient = new QueryClient({ defaultOptions: { queries: { staleTime: 30000, refetchOnWindowFocus: false } } });
const theme = createTheme({ palette: { primary: { main: '#1976d2' } } });

createRoot(document.getElementById('root')).render(
  <StrictMode>
    <QueryClientProvider client={queryClient}>
      <ThemeProvider theme={theme}>
        <CssBaseline />
        <AuthProvider>
          <App />
        </AuthProvider>
      </ThemeProvider>
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
