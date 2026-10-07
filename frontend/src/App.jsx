import { lazy, Suspense } from 'react';
import Box from '@mui/material/Box';
import CircularProgress from '@mui/material/CircularProgress';
import { Redirect, Route, Switch, useLocation } from 'wouter';
import { ROUTES } from './app/routes';
import TopBar from './components/TopBar';
import BottomTabs, { TAB_BAR_HEIGHT } from './components/BottomTabs';
import { useAuth } from './contexts/AuthContext';
import { FilterProvider } from './contexts/FilterContext';

const TermsDialog = lazy(() => import('./components/TermsDialog'));
const MajorDialog = lazy(() => import('./components/MajorDialog'));

function Loading() {
  return (
    <Box sx={{ display: 'flex', justifyContent: 'center', p: 4 }}>
      <CircularProgress size={28} aria-label="Loading page" />
    </Box>
  );
}

export default function App() {
  const [location] = useLocation();
  const { user, loading, terms, needsMajor } = useAuth();
  if (loading) return <Loading />;
  // Signed-out people only get the sign-in page; signed-in people skip it.
  if (!user && location !== '/') return <Redirect to="/" replace />;
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
