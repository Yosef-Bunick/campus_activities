import { afterEach, describe, expect, it, vi } from 'vitest';
import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider, useQuery } from '@tanstack/react-query';
import { Router } from 'wouter';
import { memoryLocation } from 'wouter/memory-location';
import { AuthProvider } from '../contexts/AuthContext';
import EventCard from '../components/EventCard';

const EVENT = {
  id: 9, series_id: null, title: 'Jam', description: '', type: 'friend_event', status: 'active',
  starts_at: '2099-10-27T19:00:00Z', ends_at: '2099-10-27T21:00:00Z', location_kind: 'campus',
  room: { id: 1, name: '38', building: 'TEC' }, creator: { id: 2, display_name: 'Ana' }, saved: null,
};

// A list backed by the ['events', …] cache, like the real pages.
function List() {
  const { data } = useQuery({ queryKey: ['events', 'x'], queryFn: () => [EVENT], staleTime: Infinity });
  return data ? data.map((e) => <EventCard key={e.id} event={e} />) : null;
}

function setup(saveResponse) {
  let release;
  const gate = new Promise((r) => { release = r; });
  vi.stubGlobal('fetch', vi.fn(async (url) => {
    if (url.endsWith('/auth/me')) return new Response(JSON.stringify({ user: { id: 1 }, permissions: [], limits: {}, csrf_token: 't' }));
    if (url.endsWith('/save')) { await gate; return saveResponse(); }
    return new Response('[]');
  }));
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  render(
    <QueryClientProvider client={qc}>
      <Router hook={memoryLocation({ path: '/home' }).hook}><AuthProvider><List /></AuthProvider></Router>
    </QueryClientProvider>
  );
  return release;
}

afterEach(() => { cleanup(); vi.unstubAllGlobals(); });

describe('instant taps', () => {
  it('fills the star before the server answers', async () => {
    const release = setup(() => new Response(JSON.stringify({ ok: true })));
    fireEvent.click(await screen.findByRole('button', { name: 'Save' }));
    expect(await screen.findByRole('button', { name: 'Unsave' })).toBeTruthy(); // server still waiting
    release();
  });

  it('puts the star back if the server refuses', async () => {
    const release = setup(() => new Response(JSON.stringify({ detail: 'nope' }), { status: 500 }));
    fireEvent.click(await screen.findByRole('button', { name: 'Save' }));
    expect(await screen.findByRole('button', { name: 'Unsave' })).toBeTruthy();
    release();
    await waitFor(() => expect(screen.getByRole('button', { name: 'Save' })).toBeTruthy());
  });
});
