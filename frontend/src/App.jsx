import { Suspense } from 'react';
import Box from '@mui/material/Box';
import CircularProgress from '@mui/material/CircularProgress';
import { Redirect, Route, Switch, useLocation } from 'wouter';
import { ROUTES } from './app/routes';
import TopBar from './components/TopBar';
import BottomTabs, { TAB_BAR_HEIGHT } from './components/BottomTabs';

function Loading() {
  return (
    <Box sx={{ display: 'flex', justifyContent: 'center', p: 4 }}>
      <CircularProgress size={28} aria-label="Loading page" />
    </Box>
  );
}

export default function App() {
  const [location] = useLocation();
  const signedInArea = location !== '/';
  return (
    <>
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
    </>
  );
}
