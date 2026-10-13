# Poseidon Three-Person Execution Plan

## Delivery model

Use a strict sequential handoff. Do not implement later stages in parallel: each stage depends on the contracts and checkpoints produced by the prior stage.

| Order | Owner | Milestones | Required outcome before handoff |
|---|---|---|---|
| 1 | Person 1 — Foundation & Identity | M0–M1 | Reproducible Python/SQLite tests, migrations, canonical models, trusted `local_owner`, `ConversationKey`, session isolation, and provider-key redaction. |
| 2 | Person 2 — Durable Runtime & Tools | M2–M3 | Restart-safe LangGraph/approvals, ordered multi-tool calls, idempotency, one tool execution path, and SQLite personal-data repositories. |
| 3 | Person 3 — Product Correctness & Release | M4–M7 | Memory correctness, deterministic agents/providers, frontend contracts, Telegram durability, audit trail, and offline release gate. |

## Required order

```text
Person 1: M0 → M1
  checkpoint + review
    ↓
Person 2: M2 → M3
  checkpoint + review
    ↓
Person 3: M4 → M5 → M6 → M7
  final release gate
    ↓
Optional later: M8
```

## Person 1 — Foundation & Identity

### Milestone 0: Reproducible Foundation

- Pin the supported Python runtime and dependencies.
- Add startup capability checks.
- Create canonical domain models and the LangChain bridge.
- Add SQLite connection handling, versioned migrations, and isolated test fixtures.
- Ensure tests cannot alter real `memory-store/` data.

### Milestone 1: Local Owner and Conversation Boundary

- Resolve `local_owner` on the server rather than trusting request-provided identity.
- Add and propagate `ConversationKey` and browser `thread_id`.
- Ensure browser sessions do not share backend conversation history.
- Separate internal provider configuration from public settings responses so API keys are never exposed.

### Handoff gate

Person 2 starts only after M0 and M1 checkpoints pass, including migration idempotency, isolated sessions, forged-identity rejection, safe binding behavior, and secret-redaction tests.

## Person 2 — Durable Runtime & Tools

### Milestone 2: Durable LangGraph Runs and Approvals

- Replace the module-global graph with injected graph lifecycle management.
- Use `AsyncSqliteSaver` with FastAPI lifespan management.
- Implement durable approval and tool-execution records.
- Use native LangGraph interrupt/resume behavior.
- Process every tool call in model-provided order and return one result per call ID.
- Remove global request telemetry such as shared memory context.

### Milestone 3: Unified Tool Policy and Personal Data

- Make the tool registry authoritative.
- Implement one policy service and one tool execution service.
- Ensure no graph node, approval endpoint, or channel adapter can bypass tool policy.
- Rename and document the execution guard accurately; it is not adversarial sandboxing.
- Migrate notes, reminders, calendar events, and CRM contacts from JSON storage to transactional SQLite repositories.

### Handoff gate

Person 3 starts only after M2 and M3 checkpoints pass, including restart-safe approvals, tool-call idempotency, multi-tool ordering, policy enforcement, taint escalation, and concurrent data-write tests.

## Person 3 — Product Correctness & Release

### Milestone 4: Memory Correctness and Lifecycle

- Build one deterministic retrieval interface.
- Correct owner-filtered vector selection and ranking.
- Add fact update, forgetting, re-embedding, prompt limits, and supervised consolidation.

### Milestone 5: Agents, Routing, and Provider Configuration

- Stabilize SQLite-backed agent definitions.
- Implement deterministic explicit-agent, command, mention, signal, and default routing precedence.
- Connect frontend agent selection to chat requests.
- Keep provider credentials out of persisted/public configuration.

### Milestone 6: Frontend Contract and Truthfulness

- Centralize typed API contracts.
- Bind approvals to their original run and browser session.
- Replace browser-only Gateway history with durable backend ledger data.
- Make Settings accurately describe execution, memory, and provider capabilities.
- Add frontend tests and remove actionable lint warnings.

### Milestone 7: Telegram Durability, Audit, and Core Release Gate

- Persist Telegram delivery state and handle duplicate/restarted deliveries safely.
- Persist bounded, redacted audit records.
- Create the isolated, offline release gate covering backend and frontend tests without touching real user data.

### Completion gate

The core plan is complete only when M4–M7 checkpoints pass and the offline release gate passes from a clean environment.

## Working agreement

- The next owner may inspect and prepare while the preceding owner works, but must not implement dependent code before the handoff checkpoint passes.
- Each owner reads the relevant current code and tests before editing.
- Each owner adds regression tests and runs focused tests throughout their milestones.
- Each handoff includes a short review of changed contracts, migrations, configuration, known limitations, and checkpoint evidence.
- Do not start Milestone 8 during core hardening. Slack, WhatsApp, real MCP transport, and sub-agent delegation remain optional work after M0–M7 are complete.
