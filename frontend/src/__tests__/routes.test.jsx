import { describe, expect, it } from 'vitest';
import { ROUTES } from '../app/routes';

describe('routes', () => {
  it('has all 7 pages, each lazy-loaded', () => {
    expect(Object.keys(ROUTES)).toEqual([
      '/', '/home', '/calendar', '/map', '/favorites', '/hidden', '/alerts',
    ]);
    for (const Page of Object.values(ROUTES)) {
      expect(Page.$$typeof).toBe(Symbol.for('react.lazy'));
    }
  });
});
