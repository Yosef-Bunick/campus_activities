import { useEffect, useRef, useState } from 'react';

export const PULL_THRESHOLD = 70; // px of (resisted) pull needed to refresh
const RESISTANCE = 0.5; // the indicator moves half as far as the finger
const MIN_SPIN_MS = 400; // so a fast refresh doesn't just flash

// Pull-to-refresh on touch screens: drag down from the very top, release past
// the threshold → onRefresh() (a promise). Returns a ref for the element to
// listen on, the current pull distance and whether a refresh is running.
export function usePullToRefresh(onRefresh, threshold = PULL_THRESHOLD) {
  const ref = useRef(null);
  const [pull, setPull] = useState(0);
  const [refreshing, setRefreshing] = useState(false);
  // Listeners are bound once; they read the latest values through refs.
  const live = useRef({});
  live.current = { onRefresh, threshold, refreshing };

  useEffect(() => {
    const el = ref.current;
    if (!el) return undefined;
    const body = document.body;
    let startY = null;
    let dist = 0;
    let saved = null; // body's overscroll-behavior-y before we touched it

    const lockBounce = () => {
      // iOS rubber-band would fight our own pull, so hold it while pulling.
      if (saved === null) { saved = body.style.overscrollBehaviorY; body.style.overscrollBehaviorY = 'contain'; }
    };
    const unlockBounce = () => {
      if (saved !== null) { body.style.overscrollBehaviorY = saved; saved = null; }
    };
    const reset = () => { startY = null; dist = 0; setPull(0); unlockBounce(); };

    const onStart = (e) => {
      if (live.current.refreshing || window.scrollY !== 0 || e.touches.length !== 1) return;
      startY = e.touches[0].clientY;
    };
    const onMove = (e) => {
      if (startY === null) return;
      if (window.scrollY > 0) { reset(); return; } // the page scrolled instead
      const dy = e.touches[0].clientY - startY;
      // Upward drags are ordinary scrolling; leave them alone.
      dist = Math.max(0, dy * RESISTANCE);
      if (dist > 0) lockBounce();
      setPull(dist);
    };
    const onEnd = async () => {
      if (startY === null) return;
      const { onRefresh: refresh, threshold: limit } = live.current;
      const go = dist >= limit;
      reset();
      if (!go) return;
      setRefreshing(true);
      const wait = new Promise((r) => setTimeout(r, MIN_SPIN_MS));
      try {
        await Promise.all([Promise.resolve(refresh?.()).catch(() => {}), wait]);
      } finally {
        setRefreshing(false);
      }
    };

    const passive = { passive: true }; // never block normal scrolling
    el.addEventListener('touchstart', onStart, passive);
    el.addEventListener('touchmove', onMove, passive);
    el.addEventListener('touchend', onEnd, passive);
    el.addEventListener('touchcancel', reset, passive);
    return () => {
      el.removeEventListener('touchstart', onStart);
      el.removeEventListener('touchmove', onMove);
      el.removeEventListener('touchend', onEnd);
      el.removeEventListener('touchcancel', reset);
      unlockBounce();
    };
  }, []);

  return { ref, pull, refreshing };
}
