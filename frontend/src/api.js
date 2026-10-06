// Fetch wrapper. Credentials are included now so the Milestone 1 session
// cookie works without changes; CSRF is added with sign-in.
export const API_BASE = import.meta.env.VITE_API_BASE || 'http://localhost:8000';
const FETCH_TIMEOUT = 15000;

export async function apiGet(path) {
  const res = await fetch(`${API_BASE}${path}`, {
    credentials: 'include',
    signal: AbortSignal.timeout(FETCH_TIMEOUT),
  });
  const body = await res.json().catch(() => null);
  if (!res.ok) {
    const err = new Error(body?.detail || `HTTP ${res.status}`);
    err.status = res.status;
    err.body = body;
    throw err;
  }
  return body;
}
