# Poseidon — Guardrail Policy (Source of Truth)

> This document is loaded by `config.py` at startup. Do not loosen any rule here
> without an explicit, separate confirmation from the human operator. Every
> relaxation must be logged as a dated change at the bottom of this file.

## 1. Tool Approval Tiers — Fixed for v1

### Auto-run (read-only, no side effects)

- `crm_read`
- `calendar` — read/lookup only
- `notes_reminders` — read only
- `skill_manage` — read only
- `mcp_client` — only for calls on an explicit, human-reviewed allowlist of read-only MCP tools (see §4)

### Approval required, every time, no exceptions

- `crm_write`
- `calendar` — create / update / delete
- `notes_reminders` — create / update / delete
- `cronjob` — registering, editing, or deleting a scheduled run
- `delegate_task` — kept in this tier for v1, not auto-run, even though it inherits the parent's guardrails (see §6 for when this can change)
- `skill_manage` — write
- `mcp_client` — any call not on the read-only allowlist
- Any tool not explicitly listed above, including anything added later

**No auto-trust promotion.** The system must never move a tool from "approval required" to "auto-run" based on a pattern of past approvals, a config heuristic, or model judgment. The only way a tool's tier changes is a human editing this document and the corresponding config, on purpose.

## 2. Cronjob-Triggered Actions With No Live Chat Present

A cronjob can fire when the operator is not in an active conversation, so there's no chat turn to approve a write action in. Policy:

- A cronjob-triggered run may execute read-only tools freely (per §1).
- If a cronjob-triggered run wants to call a write/side-effecting tool, it must **not** execute it. Instead it queues the action and sends an explicit approval request through the gateway (a message asking the operator to confirm), the same as a live approval prompt.
- If the operator doesn't respond within a configured timeout (default: 12 hours), the action is discarded, not executed. **Silence is a "no," never a "yes."**
- Every queued/expired cronjob action is recorded in the trace log so the operator can see what didn't happen and why.

## 3. Messaging Channels — Outbound Message Policy

- **Default contact allowlist = operator only.** The agent may only send messages to the channel thread/contact that originated the conversation (i.e., replying to the operator) unless a contact is explicitly added to an allowlist the operator controls.
- Any outbound message to a contact not on that allowlist requires approval every time — no exceptions, and this cannot be promoted to auto-run (§1's "no auto-trust promotion" applies doubly here).
- **Rate limit outbound messages** — a hard cap on messages per hour (default: 20), configurable. Hitting the cap pauses further sends and notifies the operator.
- The agent must not forward message content (the operator's or a contact's) to an external tool or MCP server without that call already being subject to the normal approval tier for that tool.

## 4. MCP Client — Fail-Safe Classification

- No MCP tool is treated as read-only until it's on an explicit, human-reviewed allowlist approved by name.
- Anything not on that allowlist — including a tool that merely looks read-only — defaults to approval-required.
- When a new MCP server is connected, its available tools are listed back to the operator for classification before any of them are auto-run.

## 5. Web Access (When Added Later)

Not in scope for v1 — placeholder for a future addendum:

- Web fetch/search is read-only by default: no form submission, no login, no purchases, no arbitrary POST/PUT/DELETE requests without approval.
- Any irreversible or externally-visible action via the browser is approval-required, always, and is never eligible for auto-trust promotion.
- A domain allowlist/denylist should default to a small, explicit allowlist.
- Treat as "approval-required for everything" until a real design exists.

## 6. When Any of This Is Allowed to Loosen

Only after the operator has used the system and explicitly asks for a specific rule to change. At that point:

- Update this document with a dated entry describing exactly what changed and why.
- Scope the change as narrowly as possible — loosen one tool or one contact at a time, not a whole tier at once.

## 7. Rate and Kill-Switch Guardrails

In addition to the per-run `max_iterations` / `max_tool_calls`:

- **Max approval requests per hour** — default: 5. If the agent generates an unreasonable number, stop and surface a single alert instead of flooding the operator.
- **Pause/kill command** — one command, reachable from any connected channel, that immediately stops all tool execution across every channel and cronjob until the operator explicitly resumes. Built in Sprint 3.

## 8. Audit Trail

Every approval decision — granted, denied, or expired/timed-out — is written to the trace log with a timestamp and what was approved. Queryable via `/runs/{id}/trace`.

---

## Change Log

| Date | Change | Approved By |
|---|---|---|
| 2026-08-23 | Initial policy created from operator's pre-build addendum | Operator (pre-build Q&A) |
