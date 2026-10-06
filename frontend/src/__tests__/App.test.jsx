import { afterEach, describe, expect, it, vi } from 'vitest';
import { cleanup, render, screen } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { Router } from 'wouter';
import { memoryLocation } from 'wouter/memory-location';
import App from '../App';

function renderAt(path) {
  vi.stubGlobal('fetch', vi.fn(async () => new Response(JSON.stringify({ status: 'ok' }), { status: 200 })));
  const { hook } = memoryLocation({ path });
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={qc}>
      <Router hook={hook}><App /></Router>
    </QueryClientProvider>
  );
}

afterEach(() => { cleanup(); vi.unstubAllGlobals(); });

describe('App shell', () => {
  it('shows the 5-tab bar and the lazy page on /calendar', async () => {
    renderAt('/calendar');
    for (const label of ['Home', 'Calendar', 'Map', 'Favorites', 'Alerts']) {
      expect(screen.getByRole('button', { name: label })).toBeTruthy();
    }
    expect(await screen.findByRole('heading', { name: 'Calendar' })).toBeTruthy();
  });

  it('reports API health from /health', async () => {
    renderAt('/home');
    expect(await screen.findByRole('status', { name: 'API ok' })).toBeTruthy();
    expect(fetch).toHaveBeenCalledWith('http://localhost:8000/health', expect.anything());
  });

  it('hides the tab bar on the sign-in page', async () => {
    renderAt('/');
    expect(await screen.findByRole('button', { name: 'Sign in with Microsoft' })).toBeTruthy();
    expect(screen.queryByRole('button', { name: 'Calendar' })).toBeNull();
  });
});
