import { createContext, useCallback, useContext, useEffect, useMemo, useState } from 'react';
import { useLocation, useSearch } from 'wouter';

// THE one shared filter (architecture §11). Calendar and Map both read it, and
// it's mirrored to the URL (?types=…&rooms=…&q=…) so links and tab switches keep it.
export const EVENT_TYPES = ['main_event', 'club_event', 'friend_event'];
export const FILTER_PAGES = ['/calendar', '/map'];
const EMPTY = { types: EVENT_TYPES, rooms: [], q: '' };

function fromSearch(search) {
  const p = new URLSearchParams(search);
  const types = (p.get('types') || '').split(',').filter((t) => EVENT_TYPES.includes(t));
  return {
    types: types.length ? types : EVENT_TYPES,
    rooms: (p.get('rooms') || '').split(',').filter(Boolean).map(Number),
    q: p.get('q') || '',
  };
}

export function toSearch(f) {
  const p = new URLSearchParams();
  if (f.types.length !== EVENT_TYPES.length) p.set('types', f.types.join(','));
  if (f.rooms.length) p.set('rooms', f.rooms.join(','));
  if (f.q) p.set('q', f.q);
  const s = p.toString();
  return s ? `?${s}` : '';
}

/** Query params for GET /events. */
export function toApiParams(f) {
  const p = new URLSearchParams();
  f.types.forEach((t) => p.append('types', t));
  f.rooms.forEach((r) => p.append('room_ids', r));
  if (f.q) p.set('search', f.q);
  return p;
}

const FilterContext = createContext(null);

export function FilterProvider({ children }) {
  const [location, navigate] = useLocation();
  const search = useSearch();
  const [filter, setFilterState] = useState(() => fromSearch(search));
  const onFilterPage = FILTER_PAGES.includes(location);

  // URL → state (back/forward, pasted links) on filter pages.
  useEffect(() => {
    if (onFilterPage && search) setFilterState(fromSearch(search));
  }, [onFilterPage, search]);

  // State → URL when arriving on a filter page without a query (tab switch).
  useEffect(() => {
    const want = toSearch(filter);
    if (onFilterPage && want && !search) navigate(`${location}${want}`, { replace: true });
  }, [onFilterPage, location, search, filter, navigate]);

  const setFilter = useCallback((patch) => {
    setFilterState((prev) => {
      const next = { ...prev, ...patch };
      if (onFilterPage) navigate(`${location}${toSearch(next)}`, { replace: true });
      return next;
    });
  }, [onFilterPage, location, navigate]);

  const active = filter.types.length !== EVENT_TYPES.length || filter.rooms.length > 0 || Boolean(filter.q);
  const value = useMemo(
    () => ({ filter, setFilter, reset: () => setFilter(EMPTY), active }),
    [filter, setFilter, active],
  );
  return <FilterContext.Provider value={value}>{children}</FilterContext.Provider>;
}

export function useFilter() {
  return useContext(FilterContext);
}
