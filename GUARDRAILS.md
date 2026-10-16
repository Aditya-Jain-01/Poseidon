# Poseidon — Guardrail Policy

> This is the operator-reviewed policy contract. Runtime enforcement lives in
> `backend/app/tools/registry.py`, `backend/app/tools/policy.py`, and
> `backend/app/security/guardrails.py`; loading this document does not enforce it.
> Do not loosen any rule here
> without an explicit, separate confirmation from the human operator. Every
> relaxation must be logged as a dated change at the bottom of this file.

## 1. Tool Approval Tiers

### Auto-run (read-only, no side effects)

- `crm_read`
- `calendar_read`
- `notes_reminders_read`
- `skill_manage_read`

### Guarded auto-run

- `notes_reminders_create` — benign content only; suspicious content requires approval and adversarial content is rejected (see the 2026-09-07 change below)

### Approval required, every time, no exceptions

- `crm_write`
- `calendar_create`
- `notes_reminders_delete`
- `skill_manage_write`
- Any tool not explicitly listed above, including anything added later

`cronjob`, `delegate_task`, and MCP tools are not active built-in tools. When
introduced, they require approval by default; unreviewed MCP handlers remain
disabled until an isolation design is implemented.

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
- **Rate limit outbound messages** — a hard cap on attempted Telegram sends per rolling hour (default: 20), configurable. Failed sends and retries count. Hitting the cap blocks further sends and records one operator-visible audit alert per UTC hour.
- The agent must not forward message content (the operator's or a contact's) to an external tool or MCP server without that call already being subject to the normal approval tier for that tool.

## 4. MCP Client — Fail-Safe Classification

- No MCP tool is treated as read-only until it's on an explicit, human-reviewed allowlist approved by name. No such allowlist or auto-run MCP execution is active today.
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

## 7. Rate and Pause Guardrails

In addition to the per-run `max_iterations` / `max_tool_calls`:

- **Max approval requests per rolling hour** — default: 5. Once reached, reject new approval requests and record one operator-visible audit alert per UTC hour. A resumed/replayed request does not consume another slot.
- **Pause command** — `/pause` and `/resume` in web chat or Telegram, or the authenticated `/security/guardrails/pause` and `/security/guardrails/resume` API routes. `/status` reports the state in either chat. Pause persists across restarts and prevents new tool execution and approval grants. An in-flight synchronous handler cannot be stopped safely; inspect its outcome before retrying.

## 8. Audit Trail

Every approval decision — granted, denied, or expired/timed-out — is written to the trace log with a timestamp and what was approved. Queryable via `/runs/{id}/trace`.

---

## Change Log

| Date | Change | Approved By |
|---|---|---|
| 2026-08-23 | Initial policy created from operator's pre-build addendum | Operator (pre-build Q&A) |
| 2026-09-07 | `notes_reminders_create` promoted from `approval_required` to `guarded_auto`. Clean, benign text auto-runs with no human approval. Content matching credential references, external URLs, or injection patterns triggers step-up approval via the existing ApprovalCard gate. Blatant adversarial payloads (jailbreaks, shell commands, prompt delimiters) are hard-rejected with no approval offered. `notes_reminders_delete` remains strictly `approval_required`. Change is scoped exclusively to this one tool. NoteGuard validator and `SuspiciousNoteError` sentinel implemented in `backend/app/security/note_guard.py`. | Operator |
