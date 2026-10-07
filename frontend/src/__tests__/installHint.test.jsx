import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { act, cleanup, fireEvent, render, screen } from '@testing-library/react';
import InstallHint from '../components/InstallHint';

const IPHONE = 'Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 Version/17.0 Mobile/15E148 Safari/604.1';
const CHROME = 'Mozilla/5.0 (Linux; Android 14) AppleWebKit/537.36 Chrome/126.0 Mobile Safari/537.36';

// Fakes the browser bits the hint reads; vi.stubGlobal/spyOn are undone in afterEach.
function device({ ua, standalone = false }) {
  vi.spyOn(window.navigator, 'userAgent', 'get').mockReturnValue(ua);
  window.navigator.standalone = standalone;
  vi.stubGlobal('matchMedia', vi.fn(() => ({ matches: standalone, addEventListener() {}, removeEventListener() {} })));
}

// Newer Node ships its own half-working localStorage global, so give each test a plain in-memory one.
beforeEach(() => {
  const store = new Map();
  vi.stubGlobal('localStorage', {
    getItem: (k) => (store.has(k) ? store.get(k) : null),
    setItem: (k, v) => store.set(k, String(v)),
  });
});
afterEach(() => { cleanup(); vi.restoreAllMocks(); vi.unstubAllGlobals(); delete window.navigator.standalone; });

describe('install hint', () => {
  it('shows the Share instructions on iOS Safari when not installed', () => {
    device({ ua: IPHONE });
    render(<InstallHint />);
    expect(screen.getByText(/tap Share, then Add to Home Screen/)).toBeTruthy();
  });

  it('renders nothing when already installed', () => {
    device({ ua: IPHONE, standalone: true });
    const { container } = render(<InstallHint />);
    expect(container.innerHTML).toBe('');
  });

  it('hides on dismiss and remembers it', () => {
    device({ ua: IPHONE });
    render(<InstallHint />);
    fireEvent.click(screen.getByRole('button', { name: /close/i }));
    expect(screen.queryByText(/Add to Home Screen/)).toBeNull();
    expect(Number(localStorage.getItem('install-hint-dismissed'))).toBeGreaterThan(0);
    cleanup();
    render(<InstallHint />);
    expect(screen.queryByText(/Add to Home Screen/)).toBeNull();
  });

  it('offers Install from beforeinstallprompt and calls prompt()', () => {
    device({ ua: CHROME });
    const { container } = render(<InstallHint />);
    expect(container.innerHTML).toBe('');
    const evt = new Event('beforeinstallprompt', { cancelable: true });
    evt.prompt = vi.fn();
    act(() => { window.dispatchEvent(evt); });
    expect(evt.defaultPrevented).toBe(true);
    fireEvent.click(screen.getByRole('button', { name: 'Install' }));
    expect(evt.prompt).toHaveBeenCalledOnce();
    expect(screen.queryByText('Install Campus Events')).toBeNull();
  });
});
