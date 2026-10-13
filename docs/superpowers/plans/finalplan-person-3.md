# Person 3 - Frontend, Telegram, Audit, and Release Gate

**Source:** [Canonical final plan](finalplan.md), Revision 7  
**Assignment:** M6-M7  
**Execution:** Sequential: Person 1 -> Person 2 -> Person 3

## Your outcome

Complete frontend contracts and truthful state handling, make Telegram restart-safe, persist bounded redacted audit events, and deliver the offline core release gate and accurate README.

## Execution instructions

1. Read the shared requirements below and inspect current code/tests. The source baseline is historical; re-check it against the current checkout.
2. Begin from Person 2's completed, reviewed changes and handoff. Do not reimplement their completed milestones.
3. Implement M6 through M7 in order. Complete each milestone and its checkpoint before proceeding. Stop at each checkpoint for review as required by the master plan.
4. Own every task in these milestones, including the small frontend or backend changes explicitly named by the task; assignments are by milestone, not programming language.
5. Preserve unrelated user changes and use isolated temporary storage for all tests.
6. Finish with the handoff checklist below. Do not implement another person's milestones or optional M8.

## Primary editing areas

- frontend/src/, package.json, lockfile, and test configuration
- backend/app/gateway/telegram_adapter.py and durable channel/audit services
- backend/app/orchestration/trajectory.py and audit/usage integration
- backend/app/main.py for supervised worker startup/shutdown
- New ordered migrations for Telegram delivery, audit, and retention
- backend/scripts/run_gate.py, backend/tests/ integration scenarios, README.md

## Suggested pull requests

PR 7: M6 frontend contracts/tests. PR 8: M7 Telegram/audit. PR 9: offline release gate and final documentation after all integration scenarios pass.

## Shared requirements from the canonical plan

These sections are copied from Revision 7 and apply to this assignment. Original task IDs and acceptance criteria are preserved. Update the master and affected assignment files together if requirements change.

## 1. Objective

Convert the existing Poseidon prototype into a reliable local-first, single-owner personal-agent harness without replacing LangGraph.

The finished core must provide:

- isolated conversations across browser sessions and external channel threads;
- durable LangGraph checkpoints and human approvals;
- correct processing of every LLM tool call;
- one authoritative tool-policy and execution path;
- transaction-safe local personal data;
- deterministic memory retrieval and lifecycle handling;
- deterministic agent selection and secret-safe provider configuration;
- restart-safe Telegram ingestion;
- frontend views that represent real backend state;
- an offline release gate that cannot mutate the owner's real data.

Slack, WhatsApp, recursive sub-agents, arbitrary local plugins, and a native LangGraph replacement are optional expansion work. They are not part of the core hardening definition of done.

---

## 2. Verified Baseline

The implementation agent must begin from these verified facts and re-check them before changing code:

- FastAPI is the application entry point in `backend/app/main.py`.
- The graph in `backend/app/orchestration/graph.py` is compiled once at import time without a checkpointer.
- The graph is invoked asynchronously through `graph.ainvoke()`.
- Only the first LLM tool call is copied into `current_tool_call`.
- `ApprovalStore` and `TrajectoryStore` are process-memory dictionaries.
- `MemoryEngine._last_context` is shared mutable request state.
- Session memory is keyed only by `user_id`.
- Semantic facts use SQLite FTS5 and are injected into the agent prompt.
- Episodic events use SQLite and attempt `sqlite-vec` KNN retrieval.
- Procedural memory uses global `*.SKILL.md` files.
- Notes, reminders, calendar, and CRM use shared JSON files.
- Agent definitions use `*.soul.md` files and a module-global cache.
- The frontend stores chat sessions in browser `localStorage`.
- The frontend does not send its session ID or selected agent ID to `/chat`.
- The Gateway page is built from browser chat history, not a durable backend gateway ledger.
- The Settings page overstates the current in-process execution guard as a sandbox.
- Python is currently 3.10.11.
- Installed versions observed during the audit include LangGraph 1.2.11 and `langchain-core` 1.6.0.
- A read-only isolated audit run completed with **119 passing backend tests and one failing test**.
- The failing test is `test_telegram_explicit_agent_selection_and_local_provider`; `@octavious` routes to `poseidon` because the referenced agent is not deterministically present.
- Frontend lint completes without errors but reports many unused-state and React hook/effect warnings.

### Working code that must not be rewritten without a concrete need

- OpenAI-compatible inference in `agents/qa_agent.py`.
- Provider resolution and health checking in `llm_providers.py`.
- FTS5 semantic persistence and search.
- Episodic event persistence.
- Soul-file parsing and existing agent CRUD behavior.
- Procedural-skill parsing and trigger matching.
- Telegram event normalization and basic allowlisting.
- Existing DLP, taint, note-guard, and risk-analysis utilities as reusable inputs.
- Browser chat rendering, history, theme, and inspector layout.

Refactor these only where a milestone explicitly requires a boundary or correctness change.

---

## 3. Locked Architectural Decisions

### 3.1 Product and identity model

Poseidon is a **local-first, single-owner system** for the core milestone.

- The internal owner ID is `local_owner`.
- Loopback web requests resolve to `local_owner` on the server.
- Telegram, Slack, and WhatsApp identities must be verified by their adapter and mapped to `local_owner`.
- Request bodies, query parameters, model arguments, and arbitrary headers cannot choose the trusted owner.
- Keep an owner/user column in persistent tables for future evolution, but do not build organizations, OAuth, roles, or SaaS multi-tenancy now.
- Operator-only endpoints are protected by local-loopback trust in local mode and by an API token when bound beyond loopback.

### 3.2 Conversation identity

All conversation-scoped state uses:

```python
ConversationKey(
    owner_id: str,
    channel: str,
    channel_account_id: str,
    thread_id: str,
)
```

Examples:

```text
local_owner / web / local_browser / session-abc
local_owner / telegram / telegram_12345 / chat_12345
local_owner / slack / workspace_T1:user_U1 / channel_C1:thread_123
```

Different frontend sessions must never share working-memory history merely because they share the same owner.

### 3.3 Framework boundary

- LangGraph remains the execution engine.
- Use `AsyncSqliteSaver`; never use synchronous `SqliteSaver` on the `ainvoke` path.
- Poseidon owns domain, policy, memory, tool, agent, approval, and audit models.
- LangChain message conversion stays inside `orchestration/` and the LLM boundary adapter.
- Do not implement a native agent runtime in this roadmap.

### 3.4 Persistence

- SQLite is the application source of truth.
- One local SQLite database is acceptable for application and LangGraph checkpoint tables, using separate connections and table ownership.
- Schema creation is controlled by ordered migrations, not module constructors.
- Markdown soul/skill files may remain built-in seeds and readable exports.
- Existing JSON data must be imported transactionally and retained as backups.

### 3.5 Tool security

- Model-visible tool arguments contain business inputs only.
- `owner_id`, approval flags, taint flags, roles, and permission overrides are never model-visible.
- `ToolExecutionContext` carries trusted runtime data out of band.
- Empty agent tool allowlist means no tools.
- Every tool invocation passes through one execution service.
- The current `SandboxGuard` is an execution timeout/validation guard, not adversarial isolation.
- Arbitrary downloaded Python plugins are not supported in the core release.

### 3.6 Secrets

- Provider keys remain in environment variables for the core release.
- Persisted configuration stores provider/model data and credential references, never plaintext provider keys.
- Public API responses expose only `has_api_key`.

### 3.7 Delivery semantics

- External channels use **at-least-once delivery with idempotent processing**.
- Do not claim global exactly-once delivery.
- Individual side-effecting tool calls must be idempotent within a run using a unique execution key.

---

## 4. Target Architecture

```text
React client
    -> typed API client
    -> FastAPI gateway
         -> resolve ActorContext + ConversationKey
         -> application services
              -> agent repository
              -> memory retrieval service
              -> approval repository
              -> tool policy service
              -> audit service
         -> LangGraph compiled with AsyncSqliteSaver
              -> ordered tool-call queue
              -> native interrupt/resume
              -> one ToolExecutionService
                   -> schema validation
                   -> agent permission
                   -> taint-aware policy
                   -> approval interrupt
                   -> ExecutionGuard
                   -> DLP/redaction
                   -> audit event
         -> SQLite repositories
```

### Canonical models

Create pure Poseidon models without LangChain imports:

- `ActorContext`
- `ConversationKey`
- `InboundEvent`
- `Message`
- `ToolCall`
- `ToolResult`
- `ToolExecutionContext`
- `PolicyDecision`
- `ApprovalRequest`
- `ApprovalDecision`
- `AgentDefinition`
- `MemoryHit`
- `RunResult`

Use adapters for conversion to and from LangChain messages.

---

## 5. Agent Implementation Protocol

Every coding agent executing this plan must follow these rules:

1. Read the current implementation and its tests before editing.
2. Preserve unrelated user changes and the dirty frontend worktree.
3. Add a regression test that fails against the current defective behavior or a controlled test double.
4. Do not deliberately damage tracked code merely to make a test fail.
5. Implement the smallest complete vertical behavior for the current task.
6. Do not add `pass`, placeholder responses, fake success values, or tests with empty bodies.
7. Do not swallow exceptions unless the expected degraded behavior is specified and observable.
8. Run focused tests after each task.
9. Run the milestone checkpoint before moving forward.
10. Confirm real `memory-store/` files were not modified by tests.
11. Record any necessary deviation in this plan before implementing the deviation.

A task is complete only when this flow exists and is tested:

```text
input
 -> validation
 -> trusted context
 -> processing
 -> dependency interaction
 -> persistence/side effect
 -> output
 -> restart/retry behavior where relevant
 -> observable verification
```

---

---

## Assigned milestones - complete task details

# Milestone 6 — Frontend Contract and Truthfulness

## Goal

Make the React interface accurately represent backend state and failure outcomes.

## Why this comes here

The UI should integrate against stable backend contracts, not temporary endpoints that will be replaced.

## What the maintainer should learn

- React context ownership
- derived versus duplicated state
- browser persistence
- optimistic versus confirmed actions
- API contract and component testing

## Task M6.1 — Type and centralize API contracts

- [ ] Define documented request/response shapes for chat, approval, agents, memory, audit, and health.
- [ ] Add `thread_id` and `agent_id` to chat calls.
- [ ] Add request cancellation/timeouts where appropriate.
- [ ] Preserve backend error status and structured error details.
- [ ] Keep legacy fields only for the announced compatibility window.

## Task M6.2 — Correct chat and approval state

- [ ] Bind a pending approval to its originating session and run.
- [ ] Disable only the relevant approval while submitting.
- [ ] Show `pending`, `approved`, `denied`, `expired`, and `failed` states.
- [ ] Do not mark an approval decided before the server confirms it.
- [ ] On failure, keep retry/deny controls available when still valid.
- [ ] Prevent switching sessions from appending the resumed response to the wrong conversation.
- [ ] Reconcile browser state with returned run/agent/thread IDs.

## Task M6.3 — Make Gateway a real ledger

- [ ] Back Gateway with durable channel/audit events rather than `localStorage` messages.
- [ ] Display verified channel, direction, event ID, run ID, delivery state, and timestamps.
- [ ] Show Telegram only when configured; remove the incorrect “planned” label for implemented functionality.
- [ ] Keep Discord absent unless it is actually implemented.
- [ ] Allow navigating from a gateway event to its run/trajectory.

## Task M6.4 — Make Settings accurate

- [ ] Remove unused provider form state if `.env` remains authoritative.
- [ ] Display real capability status returned by the backend.
- [ ] Rename “Sandbox” descriptions to “In-process execution guard.”
- [ ] Do not claim strict filesystem/network isolation.
- [ ] Display whether sqlite-vec is active or fallback retrieval is in use.
- [ ] Display memory/consolidation errors rather than only logging them to the browser console.

## Task M6.5 — Define quick-action behavior

Current `/memory`, `/status`, `/skills`, and `/clear` buttons are normal LLM prompts.

Choose and implement these explicit behaviors:

- `/clear`: create/clear the current browser conversation without an LLM call;
- memory/status/skills: call the corresponding API and render a structured result, or relabel them as prompt suggestions;
- unknown slash commands: remain ordinary text or show a deterministic command error.

Do not present an LLM prompt as a guaranteed system command.

## Task M6.6 — Add frontend tests and remove warnings

- [ ] Add Vitest and React Testing Library.
- [ ] Test ChatContext session isolation and request payloads.
- [ ] Test selected agent propagation.
- [ ] Test approval success/failure/expiry.
- [ ] Test Gateway API rendering.
- [ ] Test Settings capability text.
- [ ] Resolve unused variables and dead state.
- [ ] Resolve effect dependency, state-in-effect, and render-purity warnings without changing behavior accidentally.

## M6 checkpoint

- [ ] Frontend session ID reaches `ConversationKey`.
- [ ] Selected agent reaches the backend.
- [ ] Failed approval does not look successful.
- [ ] Gateway shows a real backend Telegram event.
- [ ] Settings statements match real security boundaries.
- [ ] Frontend lint has no actionable warnings.
- [ ] Frontend tests pass offline.
- [ ] Existing chat, history, theme, export, and inspector behavior still works.

---

# Milestone 7 — Telegram Durability, Audit, and Core Release Gate

## Goal

Make the existing external channel restart-safe and establish a durable release gate.

## Why this comes here

Telegram and audit events must reuse the stable actor, run, policy, and frontend contracts.

## What the maintainer should learn

- at-least-once delivery
- idempotent consumers
- task supervision and graceful shutdown
- audit event design
- release gating

## Task M7.1 — Persist Telegram delivery state

Add a `telegram_updates` table:

```text
update_id INTEGER PRIMARY KEY
status TEXT CHECK received|processing|completed|failed
run_id TEXT NOT NULL UNIQUE
attempt_count INTEGER NOT NULL
payload_hash TEXT NOT NULL
last_error TEXT
received_at TEXT NOT NULL
updated_at TEXT NOT NULL
completed_at TEXT
```

Behavior:

- [ ] Verify allowlist before accepting work.
- [ ] Insert receipt before dispatch.
- [ ] Persist polling offset only after durable receipt.
- [ ] Use deterministic `run_id` from Telegram update identity.
- [ ] Dispatch through a bounded queue.
- [ ] Claim work atomically.
- [ ] Mark terminal success/failure.
- [ ] Retry unfinished updates after restart.
- [ ] Rely on tool execution keys to prevent repeated side effects.
- [ ] Await poller and worker cancellation during application shutdown.
- [ ] Require a webhook secret whenever webhook mode is enabled.

## Task M7.2 — Persist bounded audit events and usage

Record:

- run/conversation/agent/model identifiers;
- routing decision;
- policy decision and reasons;
- approval lifecycle;
- tool start and terminal result;
- iteration/tool counts;
- token/cost data when supplied by the provider;
- channel delivery state;
- redacted errors;
- final run status.

Rules:

- DLP/redact before persistence.
- Do not persist provider credentials.
- Bound event payload sizes.
- Configure retention by age and maximum event count.
- Allow owner-initiated deletion.

## Task M7.3 — Create the offline release gate

Create `backend/scripts/run_gate.py` using `sys.executable -m pytest` and paths resolved from the script location.

The gate must:

- create an isolated temporary directory;
- override every database/storage/config path;
- set network-dependent models/providers to deterministic fakes;
- run migrations;
- run focused integration suites;
- run the complete backend suite;
- run frontend lint and frontend tests;
- compare real `memory-store/` hashes before and after;
- return non-zero on any failure;
- never contain placeholder test bodies.

Required integration scenarios:

- migration idempotency;
- forged identity ignored;
- conversation isolation;
- secret redaction;
- unsafe bind rejection;
- multi-tool ordering;
- suspicious-note interrupt;
- approval expiry, denial, replay, argument substitution, and restart;
- tool execution idempotency;
- taint escalation;
- concurrent personal-data writes;
- memory update/forget/re-embed;
- agent selection and permission enforcement;
- Telegram duplicate/restart handling;
- frontend approval failure and session binding;
- graceful shutdown.

## M7 checkpoint — Core release candidate

- [ ] Backend gate passes from a clean environment.
- [ ] Frontend lint/tests pass.
- [ ] Real user data hashes remain unchanged.
- [ ] Restart and duplicate-delivery scenarios pass.
- [ ] Durable audit records are queryable after restart.
- [ ] README accurately describes implemented capabilities and limitations.
- [ ] No critical behavior depends on process-memory dictionaries.

---

## Learning checklist for your assignment

### M6

- [ ] Which state lives in the browser and which lives in the backend?
- [ ] When is optimistic UI safe?
- [ ] How does an approval remain associated with its original session?

### M7

- [ ] Why is Telegram delivery at-least-once?
- [ ] How do event deduplication and tool idempotency complement each other?
- [ ] What evidence proves the release gate did not alter user data?

## Completion and handoff

M6 and M7 checkpoints pass. Run the offline core gate from a clean environment, verify unchanged real memory-store hashes, and review every master Definition of Done item. Hand over frontend lint/test/build results, restart/duplicate-delivery/shutdown evidence, queryable audit records, and updated documentation. Core work ends here; do not start M8.

- [ ] Verify every assigned task and milestone checkpoint; record actual results.
- [ ] Record commit/PR references, setup commands, migrations, contract changes, and documented deviations.
- [ ] Record focused tests and broader checks with pass/fail results and explicitly deferred issues.
- [ ] Confirm tests did not change real `memory-store/` files and preserve existing user work.
- [ ] Deliver the core release candidate with the master Definition of Done verified.

---

## 8. Definition of Done

### Core runtime

- [ ] Python 3.11+ dependency installation is deterministic.
- [ ] Database migrations are versioned and idempotent.
- [ ] Tests cannot mutate real local data.
- [ ] Poseidon domain types do not depend on LangChain.
- [ ] Async LangGraph checkpointing survives restart.
- [ ] Every model tool call receives one result.
- [ ] Approvals are expiring, argument-bound, restart-safe, and replay-safe.
- [ ] Side-effect execution is idempotent per run/tool-call ID.

### Local-first identity and security

- [ ] Trusted owner identity is server-derived.
- [ ] Browser/channel conversation threads are isolated.
- [ ] Unsafe non-loopback binding fails closed.
- [ ] API keys never appear in responses, logs, audit events, or override JSON.
- [ ] One policy/execution path governs all tools.
- [ ] Taint affects actual execution policy.
- [ ] Empty agent tool list means no tools.
- [ ] In-process execution is not described as adversarial isolation.

### Data and memory

- [ ] Personal tools use transactional SQLite repositories.
- [ ] Existing JSON data is imported safely and backed up.
- [ ] Memory retrieval is owner-filtered before ranking.
- [ ] Prompt assembly is bounded and deterministic.
- [ ] Memory mutations enforce ownership.
- [ ] Embedding model/dimension lifecycle is tracked.
- [ ] Consolidation is supervised, retryable, and deduplicated.

### Agents and frontend

- [ ] Selected and explicitly mentioned agents route deterministically.
- [ ] Unknown explicit agents return a clear error.
- [ ] Provider configuration is secret-safe.
- [ ] Frontend session and approval state stays bound to the originating run.
- [ ] Gateway displays durable backend events.
- [ ] Settings describes actual capabilities.
- [ ] Frontend lint and tests pass.

### Channels and operations

- [ ] Telegram delivery is durable and idempotently processed.
- [ ] Poller/workers shut down cleanly.
- [ ] Audit data survives restart and is redacted/bounded.
- [ ] Offline release gate passes without network access.
- [ ] Real `memory-store/` contents remain unchanged during the gate.

---
