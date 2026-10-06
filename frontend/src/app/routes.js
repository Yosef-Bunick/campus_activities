// path → lazy page. Same idea as unified's ledger-ui/src/app/views.js: every
// page is its own chunk, so nobody downloads the map code until they open /map.
import { lazy } from 'react';

export const ROUTES = {
  '/':          lazy(() => import('../views/SignInView')),
  '/home':      lazy(() => import('../views/HomeView')),
  '/calendar':  lazy(() => import('../views/CalendarView')),
  '/map':       lazy(() => import('../views/MapView')),
  '/favorites': lazy(() => import('../views/FavoritesView')),
  '/hidden':    lazy(() => import('../views/HiddenView')),
  '/alerts':    lazy(() => import('../views/AlertsView')),
};
