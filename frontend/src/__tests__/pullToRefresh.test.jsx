import { afterEach, describe, expect, it, vi } from 'vitest';
import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react';
import PullToRefresh from '../components/PullToRefresh';

const touch = (y) => ({ touches: [{ clientY: y }] });

function setup(onRefresh) {
  render(<PullToRefresh onRefresh={onRefresh}><p>Page</p></PullToRefresh>);
  return screen.getByText('Page').parentElement; // the wrapper the gesture listens on
}

// Drag from y=100 down by `by` px of finger movement, then let go.
function pull(el, by) {
  fireEvent.touchStart(el, touch(100));
  fireEvent.touchMove(el, touch(100 + by));
  fireEvent.touchEnd(el, { touches: [] });
}

afterEach(() => { cleanup(); window.scrollY = 0; });

describe('pull to refresh', () => {
  it('refreshes after a long enough pull from the top', async () => {
    const onRefresh = vi.fn(async () => {});
    pull(setup(onRefresh), 200); // 200 × 0.5 resistance = 100 px, past the 70 px threshold
    expect(onRefresh).toHaveBeenCalledTimes(1);
    expect(screen.getByRole('status', { name: 'Refreshing' })).toBeTruthy();
    await waitFor(() => expect(screen.queryByRole('status', { name: 'Refreshing' })).toBeNull(), { timeout: 2000 });
  });

  it('snaps back on a short pull', () => {
    const onRefresh = vi.fn();
    pull(setup(onRefresh), 60); // 30 px: not enough
    expect(onRefresh).not.toHaveBeenCalled();
  });

  it('does nothing when the page is scrolled down', () => {
    const onRefresh = vi.fn();
    window.scrollY = 300;
    pull(setup(onRefresh), 200);
    expect(onRefresh).not.toHaveBeenCalled();
  });
});
