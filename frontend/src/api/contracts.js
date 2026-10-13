/**
 * Centralized API Contract Definitions for Poseidon Client.
 *
 * Request and response shapes documented per Milestone 6 requirements.
 */

/**
 * @typedef {Object} ChatRequest
 * @property {string} text - User message text.
 * @property {string} [user_id='local_user'] - Trusted owner alias.
 * @property {string} [channel='web'] - Ingress channel.
 * @property {string} [thread_id] - Session/thread identifier.
 * @property {string} [agent_id] - Selected target agent identifier.
 */

/**
 * @typedef {Object} ChatResponse
 * @property {string} reply - Assistant message content.
 * @property {string} run_id - Unique run execution ID.
 * @property {string} active_agent - Resolved agent ID that produced the turn.
 * @property {string} thread_id - Active conversation thread ID.
 * @property {Object} conversation_key - Canonical four-part conversation key.
 * @property {Object|null} [approval_request] - Pending approval gate details if interrupted.
 * @property {Object|null} [memory_context] - Telemetry of hydrated memory hits.
 * @property {Array<Object>|null} [trajectory] - Recorded trajectory steps for the run.
 */

/**
 * @typedef {Object} ApprovalDecisionRequest
 * @property {string} approval_id - Unique ID of the parked approval.
 * @property {'approved'|'denied'} decision - Human-in-the-loop decision.
 */

/**
 * @typedef {Object} AuditEvent
 * @property {string} event_id - Globally unique audit event ID.
 * @property {string} run_id - Originating run identifier.
 * @property {string} owner_id - Verified owner identifier.
 * @property {string} channel - Channel source ('web' | 'telegram').
 * @property {'inbound'|'outbound'|'internal'} direction - Flow direction.
 * @property {string|null} agent_id - Agent ID associated with event.
 * @property {string|null} model_name - Model identifier if applicable.
 * @property {string} event_type - Event classification.
 * @property {string} status - Event status ('received' | 'processing' | 'completed' | 'failed' | 'awaiting_approval').
 * @property {Object} payload - Redacted, bounded event payload.
 * @property {string} created_at - ISO8601 UTC timestamp.
 */

/**
 * @typedef {Object} HealthResponse
 * @property {string} status - 'ok' or error status.
 * @property {string} model - Primary active model.
 * @property {string} provider - Resolved provider preset.
 * @property {boolean} configured - Whether an API key / connection is present.
 * @property {string} mode - 'local-first'.
 * @property {boolean} telegram_polling - Whether Telegram long polling runner is enabled.
 * @property {Object} capabilities - Real runtime capabilities (WAL, FTS5, vector_mode).
 */

export const CONTRACT_VERSIONS = {
  chat: 'v1',
  approval: 'v1',
  audit: 'v1',
  agents: 'v1',
  memory: 'v1',
  health: 'v1',
};
