# Person 1 - Foundation, Identity, and Durable Runtime

**Source:** [Canonical final plan](finalplan.md), Revision 7  
**Assignment:** M0-M2  
**Execution:** Sequential: Person 1 -> Person 2 -> Person 3

## Person 1 implementation record (2026-10-13)

**Status: code written; M0-M2 checkpoint sign-off pending.**

The user requested implementation using the existing venv and then explicitly directed code writing without dependency installation. The implementation therefore uses the supplied Python 3.14 environment. No milestone is marked verified merely because its code exists.

Written changes:

- M0: canonical domain models, LangChain bridge, ordered/checksummed migrations, connection policy, actual SQLite capability probes, import-safe store construction, Python metadata, and isolated test fixtures with real-store hash protection.
- M1: server-derived `local_owner`, loopback/token authorization for operator APIs, safe bind/CORS validation, verified Telegram owner mapping, conversation keys, frontend session propagation, and public/provider override credential redaction.
- M2: injected graph lifecycle with `AsyncSqliteSaver`, native interrupt/resume, durable expiring argument-bound approvals, ordered multi-tool queues, durable execution claims/results, and immutable request-local memory telemetry. Completed conversation turns and episodic writes are committed atomically and deduplicated by run ID.

Verification record:

- Python source syntax parsing completed successfully. Git whitespace checks completed without content errors.
- The initial pytest run stopped at temporary-directory permission errors before the tests executed. The subsequent request to run regression tests outside the sandbox was declined. No passing regression, full-suite, clean-install, or restart-test result is claimed.
- The supplied environments lack `langgraph-checkpoint-sqlite` and `aiosqlite`. Their production imports are deferred to lifespan with an explicit startup error; tests deliberately inject an in-memory saver, and the actual SQLite restart test skips with a stated reason when the package is absent.
- `backend/requirements.lock` is a candidate snapshot of the supplied environment plus declared checkpoint dependencies. It is not a newly resolved, clean-install-verified lock. The M0 clean-install checkpoint remains open.
- The historical `@octavious` Telegram routing failure is still deferred to M5. The test fixtures do not manufacture that missing agent or hide the failure.

Handoff contracts:

- Domain types: `backend/app/models.py`. LangChain conversions: `backend/app/orchestration/langchain_bridge.py`.
- Database ownership: `backend/app/db/migrations.py`. Do not edit already-applied migration contents; append ordered versions. Store constructors no longer create database tables.
- Runtime lifecycle: `backend/app/main.py`. Graph creation: `build_graph(checkpointer, services)`. Tests must inject a deliberate saver through `HarnessRuntime`; production requires the async SQLite saver.
- Chat sends `thread_id`; legacy missing IDs use `default` with a deprecation log. Caller `user_id` and `channel` do not select authority. Responses include `thread_id` and `conversation_key`.
- Provider settings accept `api_key_env`, not a plaintext `api_key`. Public views return `has_api_key`; resolved keys stay in the client boundary.
- Approval decisions accept only approval ID and decision. The original run/conversation/agent/tool/arguments are read from the stored checkpoint and repository.
- Execution claims prevent automatic repetition after a crash with an unknown side-effect outcome. Such claims return `execution_uncertain`. Atomic recovery across legacy JSON tool writes and execution-result persistence cannot be guaranteed until Person 2 migrates those tools in M3; this is an explicit boundary, not an exactly-once promise.
- Durable audit/trajectory storage, unified taint-aware tool policy, broader memory lifecycle work, deterministic agent repository/routing, and frontend approval reconciliation remain with Persons 2 and 3.

Verification commands for the maintainer (from the Poseidon root, using the selected venv):

```powershell
.\backend\.venv\Scripts\python.exe backend\scripts\check_person1.py
.\backend\.venv\Scripts\python.exe backend\scripts\check_person1.py --full
```

The helper overrides temporary paths and checks real-store hashes. The full suite deliberately includes the documented deferred Telegram routing failure. Run the real SQLite restart test and a clean lock install before signing off M0-M2 or handing the implementation over as verified.

---

## Your outcome

Establish the reproducible runtime, isolated tests, trusted identity/conversation boundaries, secret-safe public configuration, durable LangGraph runs, approvals, multi-tool processing, and request-local memory telemetry.

## Execution instructions

1. Read the shared requirements below and inspect current code/tests. The source baseline is historical; re-check it against the current checkout.
2. Begin from the existing repository and establish the M0 baseline.
3. Implement M0 through M2 in order. Complete each milestone and its checkpoint before proceeding. Stop at each checkpoint for review as required by the master plan.
4. Own every task in these milestones, including the small frontend or backend changes explicitly named by the task; assignments are by milestone, not programming language.
5. Preserve unrelated user changes and use isolated temporary storage for all tests.
6. Finish with the handoff checklist below. Do not implement another person's milestones or optional M8.

## Primary editing areas

- backend/requirements.txt and new lock/setup files
- backend/app/startup_checks.py, models.py, db/, orchestration/
- backend/app/main.py, config.py, security/identity.py, gateway request boundaries
- backend/app/memory/ for conversation scoping and removal of shared telemetry
- backend/app/llm_providers.py and public settings responses for M1.3
- Frontend chat API/context and settings models for the compatibility edits explicitly required by M1
- backend/tests/ fixtures and focused M0-M2 regression/integration tests

## Suggested pull requests

PR 1: M0 foundation. PR 2: M1 identity/conversations. PR 3: M2 durable runtime. Preserve the original first-three-PR scope in the master plan.

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

## Learning checklist for your assignment

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

## Completion and handoff

M0, M1, and M2 checkpoints pass. Hand over the locked environment, migration convention, application lifecycle/container, canonical models, ConversationKey propagation, approval and tool-execution repositories, graph factory, and test commands/results. Document the known Telegram routing failure if still deferred to M5; do not hide it.

- [ ] Verify every assigned task and milestone checkpoint; record actual results.
- [ ] Record commit/PR references, setup commands, migrations, contract changes, and documented deviations.
- [ ] Record focused tests and broader checks with pass/fail results and explicitly deferred issues.
- [ ] Confirm tests did not change real `memory-store/` files and preserve existing user work.
- [ ] Hand the reviewed repository and notes to Person 2.
