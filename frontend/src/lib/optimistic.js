// Instant taps: change every cached event list right away, then sync with the
// server. If the server says no, everything snaps back (ADR-033).

const now = () => Date.now();

function applyTo(list, match, change) {
  if (!Array.isArray(list)) return list;
  const out = [];
  for (const e of list) {
    if (!match(e)) out.push(e);
    else {
      const next = change(e);
      if (next) out.push(next); // null = drop it from the list
    }
  }
  return out;
}

/**
 * TanStack Query mutation options that update ['events', …] and ['favorites']
 * before the request finishes. `match(event)` picks the events to touch;
 * `change(event)` returns the new event, or null to remove it.
 * `favChange` optionally overrides what happens on the Favorites page.
 */
export function optimistic(qc, match, change, favChange = change) {
  return {
    onMutate: async (...args) => {
      await Promise.all([
        qc.cancelQueries({ queryKey: ['events'] }),
        qc.cancelQueries({ queryKey: ['favorites'] }),
      ]);
      const snapshot = [
        ...qc.getQueriesData({ queryKey: ['events'] }),
        ...qc.getQueriesData({ queryKey: ['favorites'] }),
      ];
      const m = (e) => match(e, ...args);
      qc.setQueriesData({ queryKey: ['events'] }, (list) => applyTo(list, m, (e) => change(e, ...args)));
      qc.setQueriesData({ queryKey: ['favorites'] }, (fav) => fav && {
        ...fav,
        saved: applyTo(fav.saved, m, (e) => favChange(e, ...args)),
        from_people: applyTo(fav.from_people, m, (e) => change(e, ...args)),
      });
      return { snapshot };
    },
    onError: (_err, _vars, ctx) => ctx?.snapshot.forEach(([key, data]) => qc.setQueryData(key, data)),
    onSettled: () => ['events', 'favorites', 'hidden'].forEach((k) => qc.invalidateQueries({ queryKey: [k] })),
  };
}

/** Does `e` belong to the same event (scope "this") or series (scope "series"/"future")? */
export function sameEventOrSeries(target, scope = 'this') {
  return (e) => {
    if (scope === 'this' || !target.series_id) return e.id === target.id;
    if (e.series_id !== target.series_id) return false;
    return scope === 'series' ? new Date(e.ends_at).getTime() > now()
      : new Date(e.starts_at) >= new Date(target.starts_at); // "future"
  };
}
