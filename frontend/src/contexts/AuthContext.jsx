import { createContext, useContext, useEffect } from 'react';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { apiGet, apiPost, setCsrfToken, setOnUnauthorized } from '../api';

// Current user + their permission list, from GET /auth/me. The frontend uses
// permissions only to show or hide buttons; the server enforces everything.
const AuthContext = createContext(null);

async function fetchMe() {
  try {
    const me = await apiGet('/auth/me');
    setCsrfToken(me.csrf_token);
    return me;
  } catch (err) {
    if (err.status === 401) return null; // signed out is a normal state, not an error
    throw err;
  }
}

export function AuthProvider({ children }) {
  const qc = useQueryClient();
  const { data, isPending } = useQuery({ queryKey: ['me'], queryFn: fetchMe, retry: false });
  const me = data ?? null;
  useEffect(() => {
    setOnUnauthorized(() => qc.invalidateQueries({ queryKey: ['me'] }));
    return () => setOnUnauthorized(null);
  }, [qc]);
  const value = {
    loading: isPending,
    user: me?.user ?? null,
    permissions: me?.permissions ?? [],
    limits: me?.limits ?? null,
    terms: me?.terms ?? null, // non-null = must agree before using the app
    needsMajor: Boolean(me?.needs_major), // asked right after the terms (ADR-032)
    refresh: () => qc.invalidateQueries({ queryKey: ['me'] }),
    can: (perm) => Boolean(me?.permissions.includes(perm)),
    signOut: async () => {
      await apiPost('/auth/logout').catch(() => {});
      setCsrfToken('');
      // Offline copies of the API belong to this person: drop them (ADR-031).
      if (typeof caches !== 'undefined') caches.delete('api').catch(() => {});
      // Not qc.clear(): that drops the 'me' query this provider is subscribed
      // to, so the app would never see the sign-out. Null it, drop the rest.
      qc.setQueryData(['me'], null);
      qc.removeQueries({ predicate: (q) => q.queryKey[0] !== 'me' });
    },
  };
  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  return useContext(AuthContext);
}
