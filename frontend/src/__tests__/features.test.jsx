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
import App from '../App';
import EventCard from '../components/EventCard';

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

  it('opens fitted to the screen and never zooms out past that', () => {
    api({ '/auth/me': { user: { id: 1 }, permissions: [], limits: {}, csrf_token: 't' }, '/rooms': [], '/events': [] });
    renderPage(MapView);
    const viewport = screen.getByTestId('map-viewport');
    const overflow = () => getComputedStyle(viewport).overflow;
    expect(overflow()).toBe('hidden'); // fitted: nothing to scroll
    fireEvent.click(screen.getByRole('button', { name: 'Zoom out' }));
    expect(overflow()).toBe('hidden');
    fireEvent.click(screen.getByRole('button', { name: 'Zoom in' }));
    expect(overflow()).toBe('auto'); // zoomed: scroll around the map
    fireEvent.click(screen.getByRole('button', { name: 'Zoom out' }));
    expect(overflow()).toBe('hidden');
  });
});

describe('favorites', () => {
  it('lists saved events and followed people, and unsaves', async () => {
    const unsave = vi.fn();
    api({
      '/auth/me': { user: { id: 1 }, permissions: [], limits: {}, csrf_token: 't' },
      '/favorites': {
        going: [{ ...EVENT, id: 10, title: 'Pickup game', going: true, going_count: 3 }],
        saved: [{ ...EVENT, saved: 'event' }], from_people: [], people: [{ id: 2, display_name: 'Ana' }], mine: [],
      },
      '/events/9/unsave': () => { unsave(); return { ok: true }; },
    });
    renderPage(FavoritesView);
    expect(await screen.findByText('Study, group')).toBeTruthy();
    expect(screen.getByText('Pickup game')).toBeTruthy(); // the Going section
    expect(screen.getByText('Events you post show up here.')).toBeTruthy();
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

describe('phase 2', () => {
  const SGA = { user: { id: 1 }, permissions: ['event.approve_overlap'], limits: {}, csrf_token: 't' };

  it('lets SGA approve a pending room request from Alerts', async () => {
    const approve = vi.fn(() => ({ updated: 1 }));
    api({
      '/auth/me': SGA,
      '/alerts': { unread: 1, alerts: [{ id: 7, kind: 'approval_needed', event_id: 3, event_status: 'pending_approval',
        message: 'Ana wants “Jam” in Room 108', read: false, created_at: '2026-10-06T15:00:00Z' }] },
      '/events/3/approve': approve,
    });
    renderPage(AlertsView);
    fireEvent.click(await screen.findByRole('button', { name: 'Approve' }));
    await waitFor(() => expect(approve).toHaveBeenCalled());
  });

  it('shows a pending event as waiting for approval', async () => {
    api({ '/auth/me': SGA });
    renderPage(() => <EventCard event={{ ...EVENT, status: 'pending_approval' }} />);
    expect(await screen.findByText(/Waiting for approval/)).toBeTruthy();
  });

  it('asks new users to agree to the terms first', async () => {
    const accept = vi.fn(() => ({ ok: true }));
    api({
      '/auth/me': { ...SGA, terms: { version: 1, items: ['Be kind.'] } },
      '/auth/me/accept-terms': accept,
      '/events': [], '/rooms': [], '/alerts/unread': { unread: 0 },
    });
    renderPage(App);
    expect(await screen.findByText('• Be kind.')).toBeTruthy();
    fireEvent.click(screen.getByRole('button', { name: 'I agree' }));
    await waitFor(() => expect(accept).toHaveBeenCalled());
  });
});

describe('places and majors', () => {
  const ME = { user: { id: 1 }, permissions: [], limits: {}, csrf_token: 't' };

  it('shows an online event with a safe Join online link', async () => {
    api({ '/auth/me': ME });
    renderPage(() => <EventCard event={{ ...EVENT, location_kind: 'online', room: null, online_url: 'https://zoom.us/j/1' }} />);
    expect(await screen.findByText(/Online/)).toBeTruthy();
    fireEvent.click(screen.getByRole('heading', { name: 'Study, group' }));
    const link = screen.getByRole('link', { name: 'Join online' });
    expect(link.getAttribute('href')).toBe('https://zoom.us/j/1');
    expect(link.getAttribute('rel')).toContain('noopener');
  });

  it('never links a non-http URL', async () => {
    api({ '/auth/me': ME });
    renderPage(() => <EventCard event={{ ...EVENT, location_kind: 'online', room: null, online_url: 'javascript:alert(1)' }} />);
    fireEvent.click(await screen.findByRole('heading', { name: 'Study, group' }));
    expect(screen.queryByRole('link', { name: 'Join online' })).toBeNull();
  });

  it('shows an off-campus place', async () => {
    api({ '/auth/me': ME });
    renderPage(() => <EventCard event={{ ...EVENT, location_kind: 'off_campus', room: null, location: 'Kensico Dam' }} />);
    expect(await screen.findByText(/Off campus · Kensico Dam/)).toBeTruthy();
  });

  it('asks for a major after the terms, and needs one picked', async () => {
    const put = vi.fn(() => ({ major: 'nursing' }));
    api({
      '/auth/me': { ...ME, needs_major: true },
      '/auth/majors': [{ key: 'nursing', label: 'Nursing' }],
      '/auth/me/major': put,
      '/events': [], '/rooms': [], '/alerts/unread': { unread: 0 },
    });
    renderPage(App);
    expect(await screen.findByText("What's your major?")).toBeTruthy();
    expect(screen.getByRole('button', { name: 'Continue' }).disabled).toBe(true);
    expect(screen.queryByRole('button', { name: 'Cancel' })).toBeNull();
  });
});
