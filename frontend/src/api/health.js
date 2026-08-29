import { api } from './client';

/**
 * Checks the health status of the Poseidon backend.
 * @returns {Promise<{ status: string, model: string }>}
 */
export async function checkHealth() {
  return api('/health');
}
