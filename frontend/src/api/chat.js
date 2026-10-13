/**
 * Chat API — talks to POST /chat and POST /chat/approve on the Poseidon backend.
 */

import { api } from './client';

/**
 * Send a message to the agent and get a reply.
 * @param {string} text — the user's message
 * @param {string} [userId='local_user'] — defaults to 'local_user'
 * @param {AbortSignal|null} [signal=null]
 * @param {string} [threadId='default'] — session/thread ID
 * @param {string|null} [agentId=null] — selected agent ID
 * @returns {Promise<{
 *   reply: string,
 *   run_id: string,
 *   active_agent: string,
 *   thread_id: string,
 *   conversation_key: object,
 *   approval_request: object|null,
 *   memory_context: object|null,
 *   trajectory: Array<object>|null
 * }>}
 */
export async function sendChatMessage(text, userId = 'local_user', signal = null, threadId = 'default', agentId = null) {
  return api('/chat', {
    method: 'POST',
    body: {
      text,
      user_id: userId,
      thread_id: threadId,
      ...(agentId ? { agent_id: agentId } : {}),
    },
    signal,
  });
}

/**
 * Submit human-in-the-loop approval decision.
 * @param {string} approvalId - The pending approval ID
 * @param {'approved' | 'denied'} decision - The resolution decision
 * @param {AbortSignal|null} [signal=null]
 * @returns {Promise<{
 *   reply: string,
 *   run_id: string,
 *   active_agent?: string,
 *   approval_request?: object|null
 * }>}
 */
export async function sendApprovalDecision(approvalId, decision, signal = null) {
  return api('/chat/approve', {
    method: 'POST',
    body: { approval_id: approvalId, decision },
    signal,
  });
}
