/**
 * Chat API — talks to POST /chat on the Poseidon backend.
 */

import { api } from './client';

/**
 * Send a message to the agent and get a reply.
 * @param {string} text — the user's message
 * @param {string} userId — defaults to 'local_user'
 * @returns {Promise<{ reply: string, run_id: string }>}
 */
export async function sendChatMessage(text, userId = 'local_user') {
  return api('/chat', {
    method: 'POST',
    body: { text, user_id: userId },
  });
}
