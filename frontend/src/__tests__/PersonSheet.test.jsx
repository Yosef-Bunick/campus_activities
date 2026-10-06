import { afterEach, describe, expect, it, vi } from 'vitest';
import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import PersonSheet from '../components/PersonSheet';
import { setCsrfToken } from '../api';

function person(actions, extra = {}) {
  return {
    id: 7, display_name: 'Ben', role: 'student', is_banned: false,
    actions: { favorite: true, hide: true, ban: false, change_role: false, ...actions },
    assignable_roles: [],
    ...extra,
  };
}

function renderSheet(p) {
  const fetchMock = vi.fn(async () => new Response(JSON.stringify(p), { status: 200 }));
  vi.stubGlobal('fetch', fetchMock);
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  render(
    <QueryClientProvider client={qc}>
      <PersonSheet userId={7} open onClose={() => {}} />
    </QueryClientProvider>
  );
  return fetchMock;
}

afterEach(() => { cleanup(); vi.unstubAllGlobals(); setCsrfToken(''); });

describe('PersonSheet', () => {
  it('shows only Favorite and Hide to a student', async () => {
    renderSheet(person({}));
    expect(await screen.findByText('Ben')).toBeTruthy();
    expect(screen.getByRole('button', { name: 'Favorite' })).toBeTruthy();
    expect(screen.queryByRole('button', { name: 'Ban' })).toBeNull();
    expect(screen.queryByRole('button', { name: 'Change role' })).toBeNull();
  });

  it('lets a manager ban, sending the CSRF token', async () => {
    setCsrfToken('tok');
    vi.stubGlobal('confirm', () => true);
    const fetchMock = renderSheet(person({ ban: true, change_role: true }, { assignable_roles: ['student_gov', 'security', 'student'] }));
    fireEvent.click(await screen.findByRole('button', { name: 'Ban' }));
    await waitFor(() => {
      const call = fetchMock.mock.calls.find(([url]) => url.endsWith('/users/7/ban'));
      expect(call[1].method).toBe('POST');
      expect(call[1].headers['X-CSRF-Token']).toBe('tok');
    });
  });
});
