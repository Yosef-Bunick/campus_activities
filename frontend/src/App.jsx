import { lazy, Suspense, useEffect } from 'react';
import Box from '@mui/material/Box';
import Skeleton from '@mui/material/Skeleton';
import EventSkeleton from './components/EventSkeleton';
import { Redirect, Route, Switch, useLocation } from 'wouter';
import { ROUTES } from './app/routes';
import TopBar from './components/TopBar';
import BottomTabs, { TAB_BAR_HEIGHT } from './components/BottomTabs';
import { useAuth } from './contexts/AuthContext';
import { FilterProvider } from './contexts/FilterContext';

const TermsDialog = lazy(() => import('./components/TermsDialog'));
const MajorDialog = lazy(() => import('./components/MajorDialog'));
const InstallHint = lazy(() => import('./components/InstallHint'));

// While a page's code downloads: its title area + skeleton cards, not a spinner.
function Loading() {
  return (
    <Box sx={{ p: 2, display: 'flex', flexDirection: 'column', gap: 1.5 }} aria-label="Loading page">
      <Skeleton variant="text" width={160} height={36} />
      <EventSkeleton />
    </Box>
  );
}

// A link opened while signed out (e.g. a shared event) is remembered through
// sign-in, including the Microsoft round trip (ADR-034).
const AFTER_SIGNIN = 'after-signin';
const remember = (path) => { try { sessionStorage.setItem(AFTER_SIGNIN, path); } catch { /* private mode */ } };
function takeRemembered() {
  try {
    const path = sessionStorage.getItem(AFTER_SIGNIN);
    sessionStorage.removeItem(AFTER_SIGNIN);
    return path;
  } catch { return null; }
}

export default function App() {
  const [location, navigate] = useLocation();
  const { user, loading, terms, needsMajor } = useAuth();
  useEffect(() => {
    if (!user) return;
    const back = takeRemembered();
    if (back) navigate(back, { replace: true });
  }, [user, navigate]);
  if (loading) return <Loading />;
  // Signed-out people only get the sign-in page; signed-in people skip it.
  if (!user && location !== '/') {
    remember(location + window.location.search);
    return <Redirect to="/" replace />;
  }
  if (user && location === '/') return <Redirect to="/home" replace />;
  const signedInArea = Boolean(user);
  return (
    <FilterProvider>
      <TopBar showProfile={signedInArea} />
      <Box
        component="main"
        sx={{
          maxWidth: 720,
          mx: 'auto',
          pb: signedInArea ? `calc(${TAB_BAR_HEIGHT}px + env(safe-area-inset-bottom))` : 0,
        }}
      >
        {/* "Install the app" (iPhone: Share → Add to Home Screen; Android/desktop: Install). */}
        {signedInArea && <Suspense fallback={null}><InstallHint /></Suspense>}
        {/* One <Suspense> for every lazy page, as in unified. */}
        <Suspense fallback={<Loading />}>
          <Switch>
            {Object.entries(ROUTES).map(([path, Page]) => (
              <Route key={path} path={path} component={Page} />
            ))}
            <Route><Redirect to="/" replace /></Route>
          </Switch>
        </Suspense>
      </Box>
      {signedInArea && <BottomTabs />}
      {/* First sign-in (or new terms): agree before using the app. */}
      {user && terms && <Suspense fallback={null}><TermsDialog /></Suspense>}
      {/* Then their major (for Recommended). Also asked if it's removed from majors.txt. */}
      {user && !terms && needsMajor && <Suspense fallback={null}><MajorDialog open required /></Suspense>}
    </FilterProvider>
  );
}
