import { afterEach, describe, expect, it, vi } from 'vitest';
import { act, cleanup, screen } from '@testing-library/react';
import { useTheme } from '@mui/material/styles';

// Stand-ins so main.jsx renders only the theme, not the whole app.
vi.mock('../App', () => ({
  default: function ShowMode() {
    const t = useTheme();
    return <p>{t.palette.mode} {t.palette.primary.main}</p>;
  },
}));
vi.mock('../contexts/AuthContext', () => ({ AuthProvider: ({ children }) => children }));

// matchMedia that answers `dark` for the dark-scheme query.
function fakeMatchMedia(dark) {
  vi.stubGlobal('matchMedia', (q) => ({
    matches: dark && q.includes('dark'),
    media: q,
    addEventListener() {}, removeEventListener() {}, addListener() {}, removeListener() {},
  }));
}

async function renderMain() {
  vi.resetModules();
  document.body.innerHTML = '<div id="root"></div>';
  await act(async () => { await import('../main.jsx'); });
}

describe('theme follows prefers-color-scheme', () => {
  afterEach(() => { cleanup(); vi.unstubAllGlobals(); document.body.innerHTML = ''; });

  it('is dark when the system is dark', async () => {
    fakeMatchMedia(true);
    await renderMain();
    expect(await screen.findByText('dark #90caf9')).toBeTruthy();
  });

  it('is light when the system is light', async () => {
    fakeMatchMedia(false);
    await renderMain();
    expect(await screen.findByText('light #1976d2')).toBeTruthy();
  });
});
