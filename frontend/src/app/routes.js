// path → lazy page. Same idea as unified's ledger-ui/src/app/views.js: every
// page is its own chunk, so the first screen downloads almost nothing.
import { lazy } from 'react';

const LOADERS = {
  '/':          () => import('../views/SignInView'),
  '/home':      () => import('../views/HomeView'),
  '/calendar':  () => import('../views/CalendarView'),
  '/map':       () => import('../views/MapView'),
  '/favorites': () => import('../views/FavoritesView'),
  '/hidden':    () => import('../views/HiddenView'),
  '/alerts':    () => import('../views/AlertsView'),
};

export const ROUTES = Object.fromEntries(Object.entries(LOADERS).map(([path, load]) => [path, lazy(load)]));

/** Start downloading a page's code early (repeat calls are free: the browser caches the module). */
export function preload(path) {
  LOADERS[path]?.().catch(() => {});
}

/** Once the first screen is up and the phone is idle, fetch the other tabs so switching is instant (ADR-033). */
export function preloadTabsWhenIdle(paths) {
  const run = () => paths.forEach(preload);
  if (typeof window === 'undefined') return;
  if ('requestIdleCallback' in window) window.requestIdleCallback(run, { timeout: 4000 });
  else setTimeout(run, 2000);
}
