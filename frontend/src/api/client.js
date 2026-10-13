/**
 * Lightweight fetch wrapper for the Poseidon backend API.
 * Uses the Vite proxy in dev (same origin) or VITE_API_URL in production.
 */

const BASE_URL = import.meta.env.VITE_API_URL || '';

/**
 * Structured API error that preserves HTTP status and backend payload.
 */
export class ApiError extends Error {
  constructor(message, status, data = null) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
    this.data = data;
  }
}

export async function api(path, options = {}) {
  const { method = 'GET', body, signal, timeout = 60000 } = options;

  const config = {
    method,
    headers: { 'Content-Type': 'application/json' },
  };

  if (body) {
    config.body = JSON.stringify(body);
  }

  // Handle AbortSignal and timeout
  if (signal) {
    config.signal = signal;
  } else if (typeof AbortSignal !== 'undefined' && AbortSignal.timeout) {
    config.signal = AbortSignal.timeout(timeout);
  }

  const res = await fetch(`${BASE_URL}${path}`, config);

  if (!res.ok) {
    let errorDetail;
    let errorData = null;
    try {
      errorData = await res.json();
      if (typeof errorData.detail === 'string') {
        errorDetail = errorData.detail;
      } else if (errorData.error) {
        errorDetail = errorData.error;
      } else if (errorData.detail) {
        errorDetail = JSON.stringify(errorData.detail);
      } else {
        errorDetail = `HTTP ${res.status}`;
      }
    } catch {
      errorDetail = res.statusText || `HTTP ${res.status}`;
    }
    throw new ApiError(errorDetail, res.status, errorData);
  }

  return res.json();
}
