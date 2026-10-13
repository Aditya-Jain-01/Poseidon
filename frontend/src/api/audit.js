/**
 * Audit & Gateway Ledger API — talks to /gateway/events, /audit/events, /runs/{run_id}/trajectory.
 */

import { api } from './client';

/**
 * Fetch durable cross-channel events from the backend ledger.
 * @param {object} [params]
 * @param {string} [params.channel]
 * @param {string} [params.runId]
 * @param {string} [params.direction]
 * @param {number} [params.limit=100]
 * @param {number} [params.offset=0]
 * @param {AbortSignal|null} [params.signal]
 * @returns {Promise<{ count: number, events: Array<object> }>}
 */
export async function fetchGatewayEvents({ channel, runId, direction, limit = 100, offset = 0, signal = null } = {}) {
  const query = new URLSearchParams();
  if (channel && channel !== 'all') query.set('channel', channel);
  if (runId) query.set('run_id', runId);
  if (direction) query.set('direction', direction);
  query.set('limit', String(limit));
  query.set('offset', String(offset));

  const qs = query.toString();
  return api(`/gateway/events${qs ? `?${qs}` : ''}`, { signal });
}

/**
 * Fetch execution trajectory for a specific run ID.
 * @param {string} runId
 * @param {AbortSignal|null} [signal]
 * @returns {Promise<{ run_id: string, count: number, steps: Array<object> }>}
 */
export async function fetchRunTrajectory(runId, signal = null) {
  return api(`/runs/${encodeURIComponent(runId)}/trajectory`, { signal });
}

/**
 * Delete all durable audit events for current owner.
 * @param {AbortSignal|null} [signal]
 * @returns {Promise<{ status: string, count: number }>}
 */
export async function deleteAuditEvents(signal = null) {
  return api('/audit/events', { method: 'DELETE', signal });
}
