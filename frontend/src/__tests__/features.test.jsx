import { afterEach, describe, expect, it, vi } from 'vitest';
import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { Router } from 'wouter';
import { memoryLocation } from 'wouter/memory-location';
import { googleCalendarUrl, icsText } from '../lib/calendarLinks';
import { AuthProvider } from '../contexts/AuthContext';
import { FilterProvider } from '../contexts/FilterContext';
import MapView from '../views/MapView';
import FavoritesView from '../views/FavoritesView';
import HiddenView from '../views/HiddenView';
import AlertsView from '../views/AlertsView';

const ROOM = { id: 1, name: '38', floor: 1, building: 'Test building', map_x: 0.68, map_y: 0.32 };
const EVENT = {
  id: 9, series_id: null, title: 'Study, group', description: 'Bring notes', type: 'friend_event', status: 'active',
  starts_at: '2026-10-27T19:00:00Z', ends_at: '2099-10-27T21:00:00Z', room: ROOM,
  creator: { id: 2, display_name: 'Ana' }, saved: null,
};

function api(routes) {
  vi.stubGlobal('fetch', vi.fn(async (url, init) => {
    const path = url.replace('http://localhost:8000', '').split('?')[0];
    const body = typeof routes[path] === 'function' ? routes[path](init) : routes[path];
    return new Response(JSON.stringify(body ?? { ok: true }), { status: 200 });
  }));
}

function renderPage(Page) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  const { hook } = memoryLocation({ path: '/map' });
  render(
    <QueryClientProvider client={qc}>
      <Router hook={hook}>
        <AuthProvider><FilterProvider><Page /></FilterProvider></AuthProvider>
      </Router>
    </QueryClientProvider>
  );
}

afterEach(() => { cleanup(); vi.unstubAllGlobals(); });

describe('add to calendar', () => {
  it('builds a valid .ics event in UTC with escaped text', () => {
    const ics = icsText(EVENT);
    expect(ics).toContain('DTSTART:20261027T190000Z');
    expect(ics).toContain('SUMMARY:Study\\, group');
    expect(ics).toContain('LOCATION:Test building · Room 38');
    expect(ics.split('\r\n')[0]).toBe('BEGIN:VCALENDAR');
  });

  it('builds a Google Calendar link', () => {
    const url = new URL(googleCalendarUrl(EVENT));
    expect(url.hostname).toBe('calendar.google.com');
    expect(url.searchParams.get('dates')).toBe('20261027T190000Z/20991027T210000Z');
  });
});

describe('map', () => {
  it('shows the campus map with a room pin counting its events, and opens the room', async () => {
    api({ '/auth/me': { user: { id: 1 }, permissions: [], limits: {}, csrf_token: 't' }, '/rooms': [ROOM], '/events': [EVENT] });
    renderPage(MapView);
    expect(screen.getByAltText('Campus map').getAttribute('src')).toBe('/maps/campus.webp');
    const pin = await screen.findByRole('button', { name: 'Test building · Room 38: 1 event' });
    fireEvent.click(pin);
    expect(await screen.findByText('Study, group')).toBeTruthy();
  });
});

describe('favorites', () => {
  it('lists saved events and followed people, and unsaves', async () => {
    const unsave = vi.fn();
    api({
      '/auth/me': { user: { id: 1 }, permissions: [], limits: {}, csrf_token: 't' },
      '/favorites': { saved: [{ ...EVENT, saved: 'event' }], from_people: [], people: [{ id: 2, display_name: 'Ana' }] },
      '/events/9/unsave': () => { unsave(); return { ok: true }; },
    });
    renderPage(FavoritesView);
    expect(await screen.findByText('Study, group')).toBeTruthy();
    expect(screen.getByText('Ana')).toBeTruthy();
    fireEvent.click(screen.getByRole('button', { name: 'Unsave' }));
    await waitFor(() => expect(unsave).toHaveBeenCalled());
  });
});

describe('hidden', () => {
  it('lists hidden people and series with Unhide', async () => {
    const calls = [];
    api({
      '/auth/me': { user: { id: 1 }, permissions: [], limits: {}, csrf_token: 't' },
      '/hidden': { people: [{ id: 2, display_name: 'Ana' }], events: [{ ...EVENT, hidden: 'series' }] },
      '/users/2/unhide': () => { calls.push('person'); return { ok: true }; },
    });
    renderPage(HiddenView);
    expect(await screen.findByText('Ana')).toBeTruthy();
    expect(screen.getByText('Study, group (all dates)')).toBeTruthy();
    fireEvent.click(screen.getAllByRole('button', { name: 'Unhide' })[0]);
    await waitFor(() => expect(calls).toEqual(['person']));
  });
});

describe('alerts', () => {
  it('shows unread alerts and marks them read', async () => {
    const read = vi.fn(() => ({ unread: 0 }));
    api({
      '/auth/me': { user: { id: 1 }, permissions: [], limits: {}, csrf_token: 't' },
      '/alerts': { unread: 1, alerts: [{ id: 5, message: 'Jam was cancelled', read: false, created_at: '2026-10-06T15:00:00Z' }] },
      '/alerts/read-all': read,
    });
    renderPage(AlertsView);
    expect(await screen.findByText('Jam was cancelled')).toBeTruthy();
    fireEvent.click(screen.getByRole('button', { name: 'Mark all read' }));
    await waitFor(() => expect(read).toHaveBeenCalled());
  });
});
