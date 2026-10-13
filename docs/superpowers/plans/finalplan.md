# Poseidon Local-First Agent Harness — Final Implementation Plan (Revision 7)

**Date:** 2026-10-03  
**Status:** Canonical implementation roadmap  
**Scope:** Entire Poseidon repository, with backend correctness completed before dependent frontend work  
**Supersedes:** Revision 5, Revision 6, and the 2026-10-02 audit remediation drafts  
**Execution engine:** LangGraph retained

> This document is for an AI coding agent and a student maintainer. Implement one milestone at a time, satisfy its checkpoint, and stop before beginning the next milestone. Do not create placeholder implementations or passing tests with empty bodies.

---

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

## 6. Dependency and Delivery Map

```text
M0 Reproducible foundation
  -> M1 Local owner + conversation identity
      -> M2 Durable graph + approvals
          -> M3 Unified tools + personal data
              -> M4 Memory correctness
                  -> M5 Agents + providers
                      -> M6 Frontend contracts
                          -> M7 Telegram + audit + core gate
                              -> M8 Optional channels/plugins/sub-agents
```

| Milestone | Main outcome | Hard gate |
|---|---|---|
| M0 | Reproducible runtime and isolated tests | Clean install; migrations repeat; tests cannot touch real data |
| M1 | Trusted local-owner and conversation boundary | Forged identity ignored; sessions isolated |
| M2 | Restart-safe graph and approvals | Interrupt/restart/resume; side effect once; all tool calls handled |
| M3 | One tool-policy/execution path | No bypass; transactional personal tools |
| M4 | Correct bounded memory | Concurrent retrieval isolated; lifecycle verified |
| M5 | Deterministic agents and secret-safe providers | Selected/mentioned agents resolve correctly; no secret exposure |
| M6 | Frontend reflects backend truth | Contract tests pass; approval/session behavior correct |
| M7 | Restart-safe Telegram and durable audit | Duplicate events do not duplicate runs or tools; offline core gate passes |
| M8 | Optional expansion | Each new adapter reuses core contracts |

Do not begin M8 until M0–M7 pass.

---

### Person 1 implementation status (2026-10-13)

M0-M2 code has been written, but checkpoint sign-off remains pending. At the user's direction, work used the existing venv and continued as code writing without installation. Regression execution was declined; clean-install and actual SQLite restart verification are outstanding. See the [Person 1 implementation record](finalplan-person-1.md#person-1-implementation-record-2026-10-13) for changes, handoff contracts, candidate-lock status, and the explicit legacy JSON crash-recovery boundary.

## 6.1 Sequential Assignments for Three People

Execute these assignments sequentially on the completed changes from the previous person. Each person owns all cross-stack changes explicitly required by their milestones.

| Order | Person | Milestones | Deliverable | Separate execution file |
|---|---|---|---|---|
| 1 | Person 1 | M0-M2 | Foundation, trusted identity/conversations, durable graph and approvals | [Person 1 plan](finalplan-person-1.md) |
| 2 | Person 2 | M3-M5 | Unified tools, personal data, memory, deterministic agents/providers | [Person 2 plan](finalplan-person-2.md) |
| 3 | Person 3 | M6-M7 | Frontend correctness, durable Telegram/audit, offline release gate | [Person 3 plan](finalplan-person-3.md) |

Each execution file includes shared architectural requirements, full original task details, checkpoints, learning checklist, editing areas, and handoff instructions. Person 1 owns M1 frontend compatibility edits; Person 2 owns M5.3 agent-selection propagation. Person 3 completes M6 frontend work.

Finish and review each milestone checkpoint before proceeding. At the end of each assignment, hand over reviewed changes, setup/migration instructions, contract changes, test results, and documented deviations. Person 3 verifies the entire core Definition of Done.

M8 remains optional expansion and is not assigned to these three people. Keep the canonical plan and assignment copies synchronized when requirements change.

---

# Milestone 0 — Reproducible Foundation

## Goal

Create a deterministic Python/SQLite/test foundation before changing runtime behavior.

## Why this comes first

The existing module globals and mixed storage make failures order-dependent. Later tests are not trustworthy until every store can be redirected to temporary paths.

## What the maintainer should learn

- Python imports and singleton initialization
- virtual environments and dependency locking
- pytest fixtures and dependency injection
- SQLite WAL, foreign keys, busy timeout, and migrations

## Task M0.1 — Pin and validate the runtime

**Primary files:**

- `backend/requirements.txt`
- new backend setup/lock file
- new `backend/app/startup_checks.py`
- `.env.example`

Steps:

- [ ] Move the supported runtime to Python 3.11 or newer.
- [ ] Create a fresh environment; do not reuse the Python 3.10 environment for version selection.
- [ ] Install the chosen LangGraph and checkpoint packages together.
- [ ] Prove `AsyncSqliteSaver`, `interrupt`, `Command`, and `ainvoke` compatibility with a focused test.
- [ ] Pin the exact resolved versions in a lock file. Do not use the speculative Revision 6 ranges.
- [ ] Add `langgraph-checkpoint-sqlite` and `aiosqlite`.
- [ ] Add `croniter` and `tiktoken` only when a task actually imports them.
- [ ] Add startup checks for Python version, SQLite FTS5, JSON functions, WAL, and optional `sqlite-vec`.
- [ ] Treat unavailable `sqlite-vec` as a declared degraded mode when Python cosine search is available; do not silently claim native vector search.

Verification:

```text
create clean Python 3.11 environment
install only from the lock
import app.main without creating production data
run startup capability tests
```

## Task M0.2 — Add canonical domain models

**Primary files:**

- new `backend/app/models.py`
- new `backend/app/orchestration/langchain_bridge.py`
- `backend/app/orchestration/state.py`

Steps:

- [ ] Implement the canonical models listed in Section 4.
- [ ] Keep models free of LangChain imports.
- [ ] Put LangChain conversion functions in the bridge.
- [ ] Preserve tool-call IDs and assistant tool-call lists during round trips.
- [ ] Define explicit validation for roles, decisions, channel identifiers, and non-empty IDs.
- [ ] Make all list/dict defaults use factories.

Tests:

- Poseidon message to/from LangChain round trip
- assistant message with multiple tool calls
- tool result preserves tool-call ID
- invalid empty actor/conversation IDs rejected
- trusted context fields cannot be serialized as model tool arguments

## Task M0.3 — Add database connections and migrations

**Primary files:**

- new `backend/app/db/connection.py`
- new `backend/app/db/migrations.py`
- new `backend/tests/conftest.py`

Connection policy:

- new connection per repository operation;
- `journal_mode=WAL`;
- `foreign_keys=ON`;
- `busy_timeout=5000`;
- `sqlite3.Row` row factory;
- explicit transactions for multi-statement writes;
- no shared cross-thread `sqlite3.Connection` singleton.

Steps:

- [ ] Add `schema_migrations(version, applied_at, checksum)`.
- [ ] Apply migrations monotonically inside a transaction.
- [ ] Refuse startup when the database schema is newer than the application.
- [ ] Move semantic/episodic DDL under migration ownership without changing behavior yet.
- [ ] Make store constructors receive a database path or connection factory.
- [ ] Create test fixtures for temporary database, agents, skills, LLM config, and JSON storage.
- [ ] Prevent imports from binding permanently to production paths before fixtures run.
- [ ] Hash production storage before and after the full test suite.

## M0 checkpoint

- [ ] Clean Python 3.11 install succeeds from the lock.
- [ ] Startup checks report actual SQLite capabilities.
- [ ] Migrations run three times with no schema drift.
- [ ] All tests use temporary storage.
- [ ] The real `memory-store/` hash is unchanged.
- [ ] The known Telegram routing failure remains documented if not yet fixed; no new failures exist.

---

# Milestone 1 — Local Owner and Conversation Boundary

## Goal

Establish trusted request identity and separate working conversations.

## Why this comes here

Approvals, memories, tools, and external deliveries cannot be scoped correctly without stable actor and conversation keys.

## What the maintainer should learn

- identification versus authentication
- transport payloads versus trusted context
- conversation/thread scoping
- local-first network boundaries

## Task M1.1 — Resolve the local owner server-side

**Primary files:** gateway adapters, `security/identity.py`, configuration, `main.py`

Behavior:

- Loopback web requests resolve to `ActorContext(owner_id="local_owner", is_operator=True)`.
- Legacy request `user_id` and `channel` fields may remain temporarily accepted for frontend compatibility but are ignored for authority.
- Telegram sender IDs are checked against the configured allowlist, then map to `local_owner`.
- Do not use an `X-Poseidon-User` header as authentication.
- Default bind remains `127.0.0.1`.
- Non-loopback binding requires `POSEIDON_API_TOKEN` and an explicit CORS allowlist.
- Reject wildcard CORS with credentials.
- Fail startup for unsafe non-loopback configuration.

Tests:

- forged body/query identity does not alter `ActorContext`;
- loopback local mode works without enterprise auth;
- non-loopback without token fails startup;
- allowed Telegram account maps to the owner;
- unlisted Telegram account is rejected.

## Task M1.2 — Propagate `ConversationKey`

**Primary files:** web/Telegram adapters, chat request model, memory engine, frontend chat API/context

Steps:

- [ ] Add `thread_id` to the chat API.
- [ ] Use the frontend session ID as web `thread_id`.
- [ ] Use verified chat/thread identifiers for Telegram.
- [ ] Store `ConversationKey` in `InboundEvent` and graph state.
- [ ] Change session memory from `dict[user_id]` to `dict[ConversationKey]` as an intermediate step.
- [ ] Ensure a frontend session switch does not share backend history.
- [ ] Bind approvals and audit events to the conversation key.

Backward compatibility:

- Requests without `thread_id` receive a stable `default` thread during one compatibility release.
- Emit a deprecation warning in development logs.

## Task M1.3 — Separate secret runtime config from public config

**Primary files:** `llm_providers.py`, settings endpoints, frontend settings models

Steps:

- [ ] Split internal resolved provider configuration from public response models.
- [ ] Remove `api_key` from all serialized provider/override dictionaries.
- [ ] Return `has_api_key` only.
- [ ] Store provider/model/base URL overrides without plaintext keys.
- [ ] Use environment variable/credential reference names for credentials.
- [ ] Clear affected cached clients when safe provider configuration changes.
- [ ] Add canary-secret response tests.

## M1 checkpoint

- [ ] Caller-supplied identity has no authority.
- [ ] Two browser sessions have different backend histories.
- [ ] External channel identities are verified before owner mapping.
- [ ] Unsafe public binding fails closed.
- [ ] No configured API key appears in any API response.

---

# Milestone 2 — Durable LangGraph Runs and Approvals

## Goal

Replace manual state parking with native durable graph interruption and correct multi-tool processing.

## Why this comes here

Durable runs require the identity, conversation, migration, and model foundations established earlier.

## What the maintainer should learn

- LangGraph state, reducers, checkpoints, and thread IDs
- native interrupts and resume commands
- OpenAI tool-call protocol
- compare-and-set transitions
- idempotent side effects

## Task M2.1 — Introduce graph lifecycle injection

**Primary files:** `orchestration/graph.py`, `main.py`

Steps:

- [ ] Remove the module-global production graph instance.
- [ ] Implement `build_graph(checkpointer, services) -> CompiledStateGraph`.
- [ ] Open `AsyncSqliteSaver` through FastAPI lifespan using its documented async context lifecycle.
- [ ] Run required saver setup before serving traffic.
- [ ] Store the compiled graph/services on `app.state` or an application container.
- [ ] Close the saver on shutdown.
- [ ] Require a checkpointer in production; tests inject a saver or deliberate fake.
- [ ] Use `run_id` as LangGraph `thread_id` on initial invocation and resume.

Do not test checkpointing merely by asserting an object exists. The test must close and reopen the saver.

## Task M2.2 — Implement durable approval records

Approval table fields:

```text
approval_id TEXT PRIMARY KEY
run_id TEXT NOT NULL
owner_id TEXT NOT NULL
conversation_key_json TEXT NOT NULL
tool_call_id TEXT NOT NULL
tool_name TEXT NOT NULL
canonical_arguments_json TEXT NOT NULL
arguments_hash TEXT NOT NULL
policy_version TEXT NOT NULL
status TEXT CHECK pending|approved|denied|expired|consumed
created_at TEXT NOT NULL
expires_at TEXT NOT NULL
resolved_at TEXT
consumed_at TEXT
UNIQUE(run_id, tool_call_id)
```

Also add a tool execution table with a unique `(run_id, tool_call_id)` key and stored terminal result.

Steps:

- [ ] Canonicalize tool arguments deterministically before hashing.
- [ ] Upsert the same approval on node replay rather than creating duplicates.
- [ ] Resolve with an atomic conditional update.
- [ ] Validate owner, run, tool-call ID, hash, expiry, and pending status.
- [ ] Atomically claim `approved -> consumed` before execution.
- [ ] On execution replay, return the stored result instead of running the handler again.
- [ ] Expire pending approvals lazily on read and through maintenance cleanup.

## Task M2.3 — Use native interrupt/resume

Correct flow:

```text
policy requires approval
 -> idempotently persist ApprovalRequest
 -> interrupt(public approval payload)
 -> graph checkpoint persists suspended state
 -> Command(resume=ApprovalDecision)
 -> revalidate and consume approval
 -> execute or emit denial ToolResult
 -> continue graph
```

Rules:

- `interrupt()` pauses inside the approval node; do not route to `END` to simulate suspension.
- Side effects must occur after the interrupt boundary.
- Denial emits a `ToolMessage` for the matching call ID so the model protocol remains complete.
- An orphaned approval whose checkpoint was not saved is non-resumable and must be marked expired/invalid during reconciliation.

## Task M2.4 — Correct multi-tool state

State additions:

- `pending_tool_calls`
- `current_tool_call`
- `memory_context`
- `policy_decision`
- explicit append/replace reducer definitions

Processing rules:

1. Preserve model-provided order.
2. Execute one call at a time.
3. Emit exactly one result for each call ID.
4. Stop at the first approval-required call.
5. After resume, finish that call and continue the remaining queue.
6. A denied call produces a denial result and the queue continues unless policy terminates the run.
7. Iteration and tool-call limits are checked before each transition.

## Task M2.5 — Remove global request telemetry

- [ ] Change `hydrate_context()` to return messages and immutable telemetry together.
- [ ] Store telemetry in graph state and `RunResult`.
- [ ] Remove `MemoryEngine._last_context` and `get_last_memory_context()`.
- [ ] Add concurrent request tests with interleaving.

## M2 checkpoint

- [ ] Run interrupts on an approval request.
- [ ] Process is reconstructed using the same temporary database.
- [ ] Run resumes using the same `thread_id`.
- [ ] Approved tool executes once.
- [ ] Replayed approval/execution does not execute again.
- [ ] Denial performs no side effect and produces a matching tool result.
- [ ] Three model tool calls produce three ordered results.
- [ ] Suspicious notes cannot return to the LLM before approval.
- [ ] Concurrent runs return their own memory telemetry.

---

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

# Milestone 8 — Optional Expansion

Do not implement this milestone as part of core hardening.

## M8.1 — Slack

- verify request signatures and timestamps;
- handle URL verification;
- map allowlisted Slack identity to `local_owner`;
- deduplicate event IDs;
- ignore bot/self messages;
- preserve workspace/channel/thread identity;
- use the same durable channel event service.

## M8.2 — WhatsApp

- verify provider webhook signatures;
- normalize contact/conversation IDs;
- deduplicate message IDs;
- use the same actor, conversation, approval, and delivery contracts.

## M8.3 — Real MCP transport

- manage configured server processes/connections;
- discover and validate schemas;
- namespace tool names;
- assign untrusted approval-required defaults;
- supervise lifecycle and timeouts;
- redact external errors;
- do not load server code into the Poseidon process.

## M8.4 — Sub-agent delegation

Add only after the core release gate is stable:

- explicit parent/child run linkage;
- depth and fan-out limits;
- per-agent tools and cost limits;
- no inherited approval authority;
- full audit trail;
- cancellation propagation.

---

## 7. First Three Pull Requests

### PR 1 — Foundation

Includes:

- Python 3.11 lock;
- startup checks;
- domain models and LangChain bridge;
- connection factory and migrations;
- isolated global test fixtures.

Must not change user-visible agent behavior.

### PR 2 — Identity and conversations

Includes:

- local-owner resolution;
- safe network binding/CORS;
- `ConversationKey` propagation;
- frontend `thread_id` compatibility;
- public provider configuration redaction.

### PR 3 — Durable runtime

Includes:

- `AsyncSqliteSaver` lifecycle;
- graph factory injection;
- durable approval repository;
- native interrupts/resume;
- tool execution idempotency;
- multi-tool queue;
- removal of `_last_context`.

Do not combine Slack, structured tool expansion, or UI redesign into these PRs.

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

## 9. Learning Checklist

Before implementing each milestone, the maintainer should be able to answer:

### M0

- [ ] What runs at Python import time?
- [ ] How do test fixtures redirect storage?
- [ ] What do WAL, foreign keys, and busy timeout do?

### M1

- [ ] Why is a request `user_id` not authentication?
- [ ] What uniquely identifies one conversation?
- [ ] Which data belongs in `ActorContext` versus model arguments?

### M2

- [ ] What does the LangGraph message reducer do?
- [ ] How are `thread_id`, checkpoints, interrupt, and resume related?
- [ ] Why must every tool-call ID receive a result?
- [ ] How does the execution key prevent duplicate side effects?

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

### M6

- [ ] Which state lives in the browser and which lives in the backend?
- [ ] When is optimistic UI safe?
- [ ] How does an approval remain associated with its original session?

### M7

- [ ] Why is Telegram delivery at-least-once?
- [ ] How do event deduplication and tool idempotency complement each other?
- [ ] What evidence proves the release gate did not alter user data?

---

## 10. Deferred Decisions and Revisit Criteria

### LangGraph removal

Revisit the native-runtime roadmap only when at least three are true:

- a tested feature is blocked by LangGraph behavior;
- the maintainer can explain the current graph and checkpoint lifecycle without generated summaries;
- restart-safe approvals and integration tests are complete;
- there are measured performance or operability problems attributable to LangGraph;
- Poseidon has multiple stable external integrations or real users;
- a native runtime prototype demonstrates a concrete benefit while passing the same release gate.

### Multi-user/SaaS mode

Not part of this roadmap. It would require a separate threat model covering authenticated accounts, authorization, tenant isolation, secret storage, remote deployment, rate limiting, and administrative recovery.

### Arbitrary local plugins

Not part of the core release. Adding them requires process/container isolation, capability grants, resource limits, update trust, and plugin provenance.

---

## 11. Final Rule for Implementation Agents

Do not jump to visible features such as Slack, WhatsApp, agent spawning, or UI polish while an earlier milestone checkpoint is failing.

The required order is:

```text
prove baseline
 -> establish trusted context
 -> make runs durable
 -> centralize tools and data
 -> correct memory
 -> stabilize agents
 -> repair frontend contracts
 -> harden Telegram and audit
 -> expand only after the core gate passes
```
