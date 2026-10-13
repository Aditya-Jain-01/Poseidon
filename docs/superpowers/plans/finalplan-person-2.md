# Person 2 - Tools, Personal Data, Memory, and Agents

**Source:** [Canonical final plan](finalplan.md), Revision 7  
**Assignment:** M3-M5  
**Execution:** Sequential: Person 1 -> Person 2 -> Person 3

## Your outcome

Centralize tool policy/execution, migrate existing personal data transactionally, correct memory retrieval/lifecycle, stabilize agent routing and provider configuration, and add the structured tools specified in M5.

## Execution instructions

1. Read the shared requirements below and inspect current code/tests. The source baseline is historical; re-check it against the current checkout.
2. Begin from Person 1's completed, reviewed changes and handoff. Do not reimplement their completed milestones.
3. Implement M3 through M5 in order. Complete each milestone and its checkpoint before proceeding. Stop at each checkpoint for review as required by the master plan.
4. Own every task in these milestones, including the small frontend or backend changes explicitly named by the task; assignments are by milestone, not programming language.
5. Preserve unrelated user changes and use isolated temporary storage for all tests.
6. Finish with the handoff checklist below. Do not implement another person's milestones or optional M8.

## Primary editing areas

- backend/app/tools/ and security/ policy/execution guard integration
- backend/app/memory/ and agents/summarizer_agent.py
- backend/app/soul.py, orchestration/router.py, agent repository integration
- backend/app/llm_providers.py and provider/settings persistence
- backend/app/gateway/ memory and agent endpoints
- Frontend chat API/context for M5.3 selected-agent propagation
- New ordered migrations, focused tests, and necessary main.py/graph.py service wiring

## Suggested pull requests

PR 4: M3 tools and personal data. PR 5: M4 memory correctness. PR 6: M5 agents, providers, and structured tools.

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

# Milestone 3 — Unified Tool Policy and Personal Data

## Goal

Make one service authoritative for every model-requested tool invocation and replace concurrency-unsafe personal JSON stores.

## Why this comes here

The service relies on durable run/approval state and trusted execution context.

## What the maintainer should learn

- JSON Schema validation
- capabilities and least privilege
- taint-aware policy
- SQLite transactions
- timeout versus process isolation

## Task M3.1 — Make the registry authoritative

Each tool definition must contain:

```text
name
description
schema
base_tier
has_side_effects
timeout_seconds
trusted_provenance: built_in | mcp | external
allowed_agents
handler
```

Steps:

- [ ] Validate the registry at startup.
- [ ] Reject schemas containing `approved`, `_operator_approved`, `owner_id`, taint, or role fields.
- [ ] Make empty `allowed_tools` mean no tools.
- [ ] Require an explicit `"*"` only for reviewed built-in agents that truly need it; prefer enumerated tools.
- [ ] Deny unknown tools.
- [ ] Default MCP/external tools to side-effecting, untrusted, and approval-required until reviewed.

## Task M3.2 — Implement `ToolPolicyService`

Evaluation order:

1. tool exists;
2. requested agent has permission;
3. arguments validate against schema;
4. run limits permit another call;
5. tool base tier and side-effect metadata;
6. taint and provenance;
7. approval or denial;
8. structured reasons and audit metadata.

Return `allow`, `guard`, `require_approval`, or `deny`.

Reuse the existing taint and risk-analysis functions as inputs/explanations. Remove static routing as an independent authority.

## Task M3.3 — Implement one `ToolExecutionService`

```text
ToolCall + ToolExecutionContext
 -> registry lookup
 -> schema validation
 -> policy
 -> durable approval when required
 -> execution claim/idempotency
 -> ExecutionGuard
 -> output size/type normalization
 -> DLP/redaction
 -> audit event
 -> ToolResult
```

No graph node, approval endpoint, Telegram adapter, or MCP adapter may invoke a handler directly.

## Task M3.4 — Correct the execution boundary

- [ ] Rename `SandboxGuard` to `ExecutionGuard`.
- [ ] Document that it executes trusted code inside Poseidon's process.
- [ ] Continue path and shell-name validation as defense in depth.
- [ ] Execute blocking handlers in a bounded executor.
- [ ] Document that timed-out threads may continue and therefore require idempotency.
- [ ] Do not load arbitrary Python plugin code in the core release.
- [ ] Mark real MCP transport, process supervision, and server discovery as **NOT IMPLEMENTED** until M8.

## Task M3.5 — Migrate personal tools to SQLite

Tables must cover existing behavior before adding new features:

- notes;
- reminders;
- calendar events;
- CRM contacts.

Every row contains `owner_id`. Every query and mutation includes it.

Migration procedure:

1. compute source-file checksum;
2. create timestamped backup;
3. import inside one transaction;
4. verify counts and required fields;
5. record checksum/import marker;
6. roll back on mismatch;
7. keep source files read-only for one successful release;
8. never delete source files automatically.

Do not create a second calendar implementation later. M5 may extend this same repository with richer behavior.

## M3 checkpoint

- [ ] All tool calls pass through the execution service.
- [ ] Model arguments cannot override owner or approval.
- [ ] Tainted side effects require approval.
- [ ] Unknown and unauthorized tools fail closed.
- [ ] Concurrent personal-data writes retain every committed record.
- [ ] Existing JSON data imports once and backups remain.
- [ ] UI/docs no longer claim adversarial sandbox isolation.

---

# Milestone 4 — Memory Correctness and Lifecycle

## Goal

Preserve Poseidon's working memory system while making retrieval deterministic, bounded, and lifecycle-aware.

## Why this comes here

Memory needs final conversation identity, migrations, taint metadata, and audit behavior.

## What the maintainer should learn

- working, episodic, semantic, and procedural memory roles
- FTS5/BM25
- cosine similarity and vector indexing
- Reciprocal Rank Fusion
- derived-data lifecycle

## Task M4.1 — Create one retrieval interface

Implement:

```python
retrieve_memory(
    query: str,
    context: RetrievalContext,
    limits: RetrievalLimits,
) -> list[MemoryHit]
```

`MemoryHit` includes:

- ID and memory tier;
- text;
- owner and conversation scope;
- source/run provenance;
- lexical rank;
- vector rank;
- fused score;
- taint status;
- embedding version;
- lifecycle status.

## Task M4.2 — Correct vector selection and ranking

The current global KNN then owner-filter behavior is not correctness-safe.

For the local-first data size:

- [ ] fetch vectors belonging to the requested owner;
- [ ] rank them with deterministic Python cosine similarity;
- [ ] retrieve FTS candidates separately;
- [ ] fuse result ranks using RRF;
- [ ] deduplicate by source identity;
- [ ] optimize with a filterable/partitioned vector index only after profiling proves a need.

Do not over-fetch globally and claim that post-filtering is pre-filtering.

## Task M4.3 — Add memory lifecycle

- [ ] Require owner ID in semantic update/forget predicates.
- [ ] Remove forgotten facts from retrieval and derived exports.
- [ ] Store embedding model name, version, and dimension.
- [ ] Mark incompatible records `reembed_required`.
- [ ] Re-embed changed content.
- [ ] Remove or rewrite an empty stale Markdown mirror.
- [ ] Make procedural skills either built-in/operator-owned or owner-scoped.
- [ ] Sanitize any identifier used in an export path.

## Task M4.4 — Bound prompt assembly

- [ ] Apply maximum hit count and token/character budgets per tier.
- [ ] Define deterministic priority: persona, required skill, semantic facts, episodic recall, session history, current input.
- [ ] Deduplicate repeated content.
- [ ] Truncate oldest/lowest-ranked content first.
- [ ] Return a telemetry explanation of selected and omitted memory.
- [ ] Propagate taint from external/retrieved content into graph state.

## Task M4.5 — Make consolidation supervised

- [ ] Allow only one active consolidation job per owner.
- [ ] Persist job status or supervise it through the application lifespan.
- [ ] Mark events consolidated only after all fact/skill writes commit.
- [ ] Leave failed events retryable.
- [ ] Prevent the same event batch from generating duplicate facts/skills.
- [ ] Report model/parsing/filter failures rather than silently marking success.

## M4 checkpoint

- [ ] Different conversations have different working histories.
- [ ] Owner-filtered vector retrieval cannot be displaced by other-owner distractors.
- [ ] RRF ranking is deterministic with test embeddings.
- [ ] Fact update changes retrieval.
- [ ] Forgotten facts disappear everywhere.
- [ ] Model/dimension changes trigger re-embedding state.
- [ ] Prompt size remains within configured budget.
- [ ] Concurrent consolidation starts one job and failures retry safely.

---

# Milestone 5 — Agents, Routing, and Provider Configuration

## Goal

Make agent selection, permissions, persistence, and provider resolution deterministic.

## Why this comes here

Agents depend on the final tool permission model and canonical chat contract.

## What the maintainer should learn

- soul/persona composition
- routing precedence
- agent repository patterns
- provider/client caching
- secret/reference separation

## Task M5.1 — Stabilize agent definitions

- [ ] Treat existing soul files as read-only seed definitions.
- [ ] Add a versioned SQLite agent repository for mutable definitions.
- [ ] Import seeds idempotently without overwriting user changes.
- [ ] Validate IDs, model presets, routing signals, and tool allowlists.
- [ ] Inject the repository into routing and tool selection.
- [ ] Remove module-global cache ordering as a correctness dependency.
- [ ] Preserve the current limit of two custom agents unless product requirements explicitly change it.

## Task M5.2 — Define deterministic routing

Precedence:

1. explicit API `agent_id` selected by the owner;
2. valid `/agent <id>` directive;
3. valid leading `@agent` mention;
4. deterministic configured routing signals;
5. default Poseidon agent.

Rules:

- An unknown explicit agent returns `unknown_agent` with available IDs.
- Do not silently fall back when the user explicitly selected an agent.
- Non-explicit unmatched text may use the default agent.
- Validate agent tool permissions after routing.

## Task M5.3 — Connect frontend selection to chat

- [ ] Send `activeAgentId` and frontend session/thread ID with chat requests.
- [ ] Store the returned `active_agent` on the turn.
- [ ] Display a mismatch as an error rather than silently changing the UI selection.
- [ ] Ensure approval resume stays with the original agent and conversation.

## Task M5.4 — Make provider configuration secret-safe

- [ ] Separate internal resolved configuration from public settings views.
- [ ] Keep credentials in environment variables for the core release.
- [ ] Persist only preset, model, base URL, and credential reference.
- [ ] Remove or migrate any plaintext keys already written to `llm_config.json`.
- [ ] Do not log resolved keys or include them in exceptions.
- [ ] Invalidate cached clients when the endpoint/credential reference changes.

## Task M5.5 — Extend structured tools without duplication

After existing tool migration passes:

- [ ] add structured tasks with source-message idempotency;
- [ ] add named lists and ambiguity results;
- [ ] extend the existing calendar repository with timezone/DST-aware storage;
- [ ] store timestamps in UTC plus original timezone metadata;
- [ ] require approvals for destructive or externally visible mutations.

Do not replace `calendar.py` with a parallel module and a second data migration.

## M5 checkpoint

- [ ] UI-selected agent receives the turn.
- [ ] Valid explicit mention routes after restart.
- [ ] Unknown explicit mention reports an error.
- [ ] Agent with no tools receives no schemas.
- [ ] Agent permissions cannot be bypassed during approval resume.
- [ ] Existing failing Telegram routing test is replaced/fixed with deterministic fixtures.
- [ ] Full backend suite passes.
- [ ] No provider key appears in API responses, logs, or persisted override JSON.

---

## Learning checklist for your assignment

### M3

- [ ] Where is the single policy decision made?
- [ ] What is the difference between a timeout guard and a sandbox?
- [ ] Why does atomic file replacement not prevent lost updates?

### M4

- [ ] What belongs in each memory tier?
- [ ] How do BM25, cosine similarity, and RRF differ?
- [ ] Why are embeddings derived/versioned data?

### M5

- [ ] What is the routing precedence?
- [ ] How are tool permissions attached to an agent?
- [ ] Why must public provider configuration exclude credentials?

## Completion and handoff

M3, M4, and M5 checkpoints pass, including the full backend suite. Hand over tool-policy/execution contracts, import/backup records, memory APIs/capability telemetry, agent/routing behavior, public provider settings, selected-agent chat behavior, and test commands/results. Keep M0-M2 checkpoints passing.

- [ ] Verify every assigned task and milestone checkpoint; record actual results.
- [ ] Record commit/PR references, setup commands, migrations, contract changes, and documented deviations.
- [ ] Record focused tests and broader checks with pass/fail results and explicitly deferred issues.
- [ ] Confirm tests did not change real `memory-store/` files and preserve existing user work.
- [ ] Hand the reviewed repository and notes to Person 3.
