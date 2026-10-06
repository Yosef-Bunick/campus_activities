// Fetch wrapper: sends the session cookie (credentials) and, on writes, the
// CSRF token (double-submit, copied from unified). The token comes from
// GET /auth/me because on a cross-site deploy the page can't read the API's cookie.
export const API_BASE = import.meta.env.VITE_API_BASE || 'http://localhost:8000';
const FETCH_TIMEOUT = 15000;

let csrfToken = '';
export function setCsrfToken(token) { csrfToken = token || ''; }

async function request(method, path, body) {
  const headers = {};
  if (body !== undefined) headers['Content-Type'] = 'application/json';
  if (method !== 'GET' && csrfToken) headers['X-CSRF-Token'] = csrfToken;
  const init = { method, headers, credentials: 'include', signal: AbortSignal.timeout(FETCH_TIMEOUT) };
  if (body !== undefined) init.body = JSON.stringify(body);
  const res = await fetch(`${API_BASE}${path}`, init);
  const data = await res.json().catch(() => null);
  if (!res.ok) {
    const err = new Error(data?.detail || `HTTP ${res.status}`);
    err.status = res.status;
    err.body = data;
    throw err;
  }
  return data;
}

export const apiGet = (path) => request('GET', path);
export const apiPost = (path, body) => request('POST', path, body);
export const apiPut = (path, body) => request('PUT', path, body);
export const apiPatch = (path, body) => request('PATCH', path, body);
