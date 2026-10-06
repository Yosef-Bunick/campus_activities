import { afterEach, describe, expect, it, vi } from 'vitest';
import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { Router } from 'wouter';
import { memoryLocation } from 'wouter/memory-location';
import App from '../App';
import { AuthProvider } from '../contexts/AuthContext';

const ME = {
  user: { id: 1, display_name: 'Ana', role: 'student', email: 'ana@my.sunywcc.edu' },
  permissions: ['event.view'],
  limits: { max_days_ahead: 90 },
  csrf_token: 'tok',
};

// Fake API: /health is up, no events; /auth/me returns `me` or 401 when signed out.
function mockApi(me) {
  vi.stubGlobal('fetch', vi.fn(async (url) => {
    if (url.endsWith('/auth/me')) {
      return me
        ? new Response(JSON.stringify(me), { status: 200 })
        : new Response(JSON.stringify({ detail: 'Not signed in' }), { status: 401 });
    }
    const body = url.includes('/events') || url.includes('/rooms') ? []
      : url.endsWith('/auth/config') ? { microsoft: false, dev_login: false }
      : { status: 'ok' };
    return new Response(JSON.stringify(body), { status: 200 });
  }));
}

function renderAt(path, me) {
  mockApi(me);
  const loc = memoryLocation({ path, record: true });
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  render(
    <QueryClientProvider client={qc}>
      <Router hook={loc.hook}>
        <AuthProvider><App /></AuthProvider>
      </Router>
    </QueryClientProvider>
  );
  return loc;
}

afterEach(() => { cleanup(); vi.unstubAllGlobals(); });

describe('App shell (signed in)', () => {
  it('shows the 5-tab bar and the lazy page on /calendar', async () => {
    renderAt('/calendar', ME);
    expect(await screen.findByRole('heading', { name: 'Calendar' })).toBeTruthy();
    for (const label of ['Home', 'Calendar', 'Map', 'Favorites', 'Alerts']) {
      expect(screen.getByRole('button', { name: label })).toBeTruthy();
    }
  });

  it('reports API health from /health', async () => {
    renderAt('/home', ME);
    expect(await screen.findByRole('status', { name: 'API ok' })).toBeTruthy();
    expect(fetch).toHaveBeenCalledWith('http://localhost:8000/health', expect.anything());
  });

  it('sends signed-in users from / to /home', async () => {
    const loc = renderAt('/', ME);
    expect(await screen.findByRole('heading', { name: "What's on" })).toBeTruthy();
    expect(loc.history.at(-1)).toBe('/home');
  });
});

describe('Home chips', () => {
  it('asks the API for the chosen window and for Recommended', async () => {
    renderAt('/home', ME);
    fireEvent.click(await screen.findByRole('button', { name: 'Now' }));
    await waitFor(() => expect(fetch.mock.calls.some(([u]) => u.includes('happening_now=true'))).toBe(true));
    fireEvent.click(screen.getByRole('button', { name: 'Recommended' }));
    await waitFor(() => expect(fetch.mock.calls.some(([u]) => u.includes('recommended=true'))).toBe(true));
    expect(screen.getByRole('button', { name: 'Set your major for more' })).toBeTruthy();
  });
});

describe('Sign out', () => {
  it('returns to the sign-in page', async () => {
    const loc = renderAt('/home', ME);
    fireEvent.click(await screen.findByRole('button', { name: 'Profile menu' }));
    fireEvent.click(await screen.findByRole('menuitem', { name: 'Sign out' }));
    expect(await screen.findByRole('button', { name: 'Sign in with Microsoft' })).toBeTruthy();
    expect(loc.history.at(-1)).toBe('/');
    const logout = fetch.mock.calls.find(([url]) => url.endsWith('/auth/logout'));
    expect(logout[1].headers['X-CSRF-Token']).toBe('tok');
  });
});

describe('App shell (signed out)', () => {
  it('sends signed-out users to the sign-in page, with no tab bar', async () => {
    const loc = renderAt('/map', null);
    expect(await screen.findByRole('button', { name: 'Sign in with Microsoft' })).toBeTruthy();
    await waitFor(() => expect(loc.history.at(-1)).toBe('/'));
    expect(screen.queryByRole('button', { name: 'Calendar' })).toBeNull();
  });
});
