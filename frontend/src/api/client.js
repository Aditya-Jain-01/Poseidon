/**
 * Lightweight fetch wrapper for the Poseidon backend API.
 * Uses the Vite proxy in dev (same origin) or VITE_API_URL in production.
 */

const BASE_URL = import.meta.env.VITE_API_URL || '';

export async function api(path, options = {}) {
  const { method = 'GET', body, signal } = options;

  const config = {
    method,
    headers: { 'Content-Type': 'application/json' },
  };

  if (body) {
    config.body = JSON.stringify(body);
  }

  if (signal) {
    config.signal = signal;
  }

  const res = await fetch(`${BASE_URL}${path}`, config);

  if (!res.ok) {
    let errorDetail;
    try {
      const errorBody = await res.json();
      errorDetail = errorBody.detail || errorBody.error || `HTTP ${res.status}`;
    } catch {
      errorDetail = res.statusText || `HTTP ${res.status}`;
    }
    throw new Error(errorDetail);
  }

  return res.json();
}
