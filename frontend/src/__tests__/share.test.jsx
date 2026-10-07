import { afterEach, describe, expect, it, vi } from 'vitest';
import { cleanup, render, screen } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { Router } from 'wouter';
import { memoryLocation } from 'wouter/memory-location';
import { AuthProvider } from '../contexts/AuthContext';
import { FilterProvider } from '../contexts/FilterContext';
import { relativeLabel } from '../lib/time';
import { eventLink, shareEvent } from '../lib/share';
import CalendarView from '../views/CalendarView';

const EVENT = {
  id: 42, series_id: null, title: 'Jam', description: '', type: 'friend_event', status: 'active',
  starts_at: '2099-10-27T19:00:00Z', ends_at: '2099-10-27T21:00:00Z', location_kind: 'campus',
  room: { id: 1, name: '38', building: 'TEC' }, creator: { id: 2, display_name: 'Ana' }, saved: null,
};

afterEach(() => { cleanup(); vi.unstubAllGlobals(); vi.restoreAllMocks(); });

describe('live time labels', () => {
  const at = (min) => new Date(Date.UTC(2026, 9, 6, 15, 0) + min * 60000).toISOString();
  const now = Date.UTC(2026, 9, 6, 15, 0);
  it('says how long is left while it runs, and how soon it starts', () => {
    expect(relativeLabel({ starts_at: at(-30), ends_at: at(40) }, now)).toBe('Now · ends in 40 min');
    expect(relativeLabel({ starts_at: at(25), ends_at: at(85) }, now)).toBe('In 25 min');
    expect(relativeLabel({ starts_at: at(130), ends_at: at(190) }, now)).toBe('In 2 h 10 min');
    expect(relativeLabel({ starts_at: at(60 * 24), ends_at: at(60 * 25) }, now)).toBeNull(); // far off: the date says enough
    expect(relativeLabel({ starts_at: at(-90), ends_at: at(-30) }, now)).toBeNull(); // over
  });
});

describe('share', () => {
  it('uses the phone share sheet when there is one', async () => {
    const share = vi.fn(async () => {});
    vi.stubGlobal('navigator', { ...navigator, share });
    expect(await shareEvent(EVENT)).toBe('shared');
    expect(share.mock.calls[0][0].url).toBe(eventLink(EVENT));
    expect(eventLink(EVENT)).toMatch(/\/calendar\?event=42$/);
  });

  it('copies the link where there is no share sheet', async () => {
    const writeText = vi.fn(async () => {});
    vi.stubGlobal('navigator', { ...navigator, share: undefined, clipboard: { writeText } });
    expect(await shareEvent(EVENT)).toBe('copied');
    expect(writeText).toHaveBeenCalledWith(eventLink(EVENT));
  });

  it('opens a shared event on top of the calendar', async () => {
    vi.stubGlobal('fetch', vi.fn(async (url) => {
      const path = url.replace('http://localhost:8000', '').split('?')[0];
      const body = path === '/auth/me' ? { user: { id: 1 }, permissions: [], limits: {}, csrf_token: 't' }
        : path === '/events/42' ? EVENT : [];
      return new Response(JSON.stringify(body));
    }));
    const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
    render(
      <QueryClientProvider client={qc}>
        <Router hook={memoryLocation({ path: '/calendar', searchPath: 'event=42' }).hook}
          searchHook={() => 'event=42'}>
          <AuthProvider><FilterProvider><CalendarView /></FilterProvider></AuthProvider>
        </Router>
      </QueryClientProvider>
    );
    expect(await screen.findByText('Shared with you')).toBeTruthy();
    expect(await screen.findByRole('heading', { name: 'Jam' })).toBeTruthy();
  });
});
