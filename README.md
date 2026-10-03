# Poseidon

Poseidon is a local-first personal-agent harness built with FastAPI, LangGraph, React, and SQLite. It assembles each agent turn from an agent persona, active procedural skills, semantic facts, relevant episodic history, and the current conversation, then runs the turn through a bounded tool-calling graph.

> **Project status:** active personal/learning project. The core chat, memory, local tools, approval flow, Telegram adapter, agent definitions, and developer UI work today. The hardening roadmap is not fully implemented; read [Current limitations](#current-limitations) before treating Poseidon as a multi-user or production service.

## What works today

- OpenAI-compatible inference through a configurable model and base URL, including local Ollama and compatible cloud providers.
- A bounded LangGraph loop with typed state, iteration limits, tool-call limits, tool execution, and approval routing.
- Four memory tiers:
  - **Working:** in-process conversation context.
  - **Episodic:** SQLite conversation events with embeddings and vector retrieval.
  - **Semantic:** SQLite FTS5 facts ranked with BM25 and mirrored to a readable `MEMORY.md` file.
  - **Procedural:** file-backed `*.SKILL.md` playbooks selected by trigger matching.
- Background and manually triggered consolidation of episodic events into semantic memory.
- Local tools for notes/reminders, CRM contacts, calendar records, and procedural skills.
- Three tool tiers: `auto`, `guarded_auto`, and `approval_required`.
- Outbound secret/PII redaction, note-content inspection, bounded tool execution, and path validation.
- Web/REST chat plus an optional Telegram webhook or long-polling adapter.
- File-backed agent personas with tool allowlists, routing signals, and per-agent model configuration.
- A React developer interface for chat, approvals, memory inspection, trajectories, topology, agents, gateway status, and model settings.

## Architecture

```text
Browser / REST / Telegram
          |
          v
     InboundEvent
          |
          v
  Agent routing + memory hydration
          |
          v
  LangGraph bounded execution loop
     |          |           |
     |          |           +--> approval gate
     |          +--------------> tool registry + execution guard
     +-------------------------> configured LLM endpoint
          |
          v
   DLP-filtered response
          |
          +--> episodic persistence
          +--> optional consolidation
```

The application is local-first, not necessarily offline. Runtime data is stored under `memory-store/`, but model calls leave the machine when a cloud endpoint is configured. Use Ollama or another local OpenAI-compatible endpoint for fully local inference.

## Memory model

| Tier | Implementation | Lifetime | Used during inference |
|---|---|---|---|
| Working | In-memory session messages | Until process restart | Yes |
| Episodic | `state.db`, embeddings, sqlite-vec when available | Persistent | Yes, vector relevance retrieval |
| Semantic | `state.db` FTS5 index + `MEMORY.md` mirror | Persistent | Yes, BM25 keyword retrieval |
| Procedural | `memory-store/skills/*.SKILL.md` | Persistent | Yes, trigger-based selection |

`MemoryEngine.hydrate_context()` builds the system context before each model call. `MemoryEngine.record_turn()` writes completed conversations to episodic memory. Once the configured threshold is reached, the summarizer can promote durable information into semantic memory.

The SQLite database is the source of truth for episodic and semantic memory. The generated `MEMORY.md` file is for inspection, not primary storage.

## Tool policy

| Tool | Purpose | Tier |
|---|---|---|
| `crm_read` | Search local contacts | `auto` |
| `crm_write` | Create, update, or delete contacts | `approval_required` |
| `notes_reminders_read` | Search notes and reminders | `auto` |
| `notes_reminders_create` | Create a note or reminder | `guarded_auto` |
| `notes_reminders_delete` | Delete a note or reminder | `approval_required` |
| `calendar_read` | Search local calendar records | `auto` |
| `calendar_create` | Create a local calendar record | `approval_required` |
| `skill_manage_read` | List procedural skills | `auto` |
| `skill_manage_write` | Create a procedural skill | `approval_required` |

The calendar tools operate on Poseidon's local JSON store. They do **not** integrate with Google Calendar, Outlook, or an operating-system calendar.

`SandboxGuard` is an in-process validation and timeout boundary for trusted handlers. It is not a container, virtual machine, or adversarial code sandbox.

## Repository layout

```text
Poseidon/
├── backend/
│   ├── app/
│   │   ├── agents/          # Conversational and summarizer agents
│   │   ├── gateway/         # Web, Telegram, memory, agent, and trajectory APIs
│   │   ├── memory/          # Four-tier memory implementation
│   │   ├── orchestration/   # LangGraph state, routing, approvals, trajectories
│   │   ├── security/        # DLP, taint/risk analysis, NoteGuard, execution guard
│   │   ├── tools/           # Native tools, registry, and MCP registration layer
│   │   ├── config.py
│   │   ├── llm_providers.py
│   │   └── main.py
│   ├── tests/
│   └── requirements.txt
├── frontend/                # React 19 + Vite developer interface
├── memory-store/            # Local runtime state and agent/skill definitions
├── docs/superpowers/plans/  # Refactoring and hardening plans
├── .env.example
└── GUARDRAILS.md
```

## Requirements

- Python 3.10 or newer
- Node.js `^20.19.0` or `>=22.12.0` (required by the installed Vite version)
- npm

The embedding dependency may download the configured sentence-transformers model on first use. A cloud LLM configuration also requires network access.

## Quick start

### 1. Configure the environment

From the repository root:

```powershell
Copy-Item .env.example .env
```

Edit `.env` and provide an OpenAI-compatible base URL, model identifier, and suitable API key. Do not commit `.env`.

Example for local Ollama:

```dotenv
POSEIDON_BASE_URL=http://localhost:11434/v1
POSEIDON_MODEL=llama3.2
POSEIDON_API_KEY=ollama
```

Example for another OpenAI-compatible provider:

```dotenv
POSEIDON_BASE_URL=https://provider.example/v1
POSEIDON_MODEL=provider/model-name
POSEIDON_API_KEY=replace-me
```

### 2. Start the backend

PowerShell, from the repository root:

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r backend\requirements.txt
python -m uvicorn app.main:app --app-dir backend --reload --host 127.0.0.1 --port 8000
```

Verify it:

```powershell
Invoke-RestMethod http://127.0.0.1:8000/health | ConvertTo-Json
```

Interactive API documentation is available at `http://127.0.0.1:8000/docs`.

### 3. Start the frontend for development

In a second terminal:

```powershell
Set-Location frontend
npm install
npm run dev
```

Open `http://127.0.0.1:5173`. Vite proxies API requests to the backend on port `8000`.

The Vite page and the FastAPI-served production build are two different frontend instances. During development, use the Vite URL. After creating a production build, use the backend URL instead.

### 4. Serve a production frontend build from FastAPI

```powershell
Set-Location frontend
npm run build
Set-Location ..
python -m uvicorn app.main:app --app-dir backend --host 127.0.0.1 --port 8000
```

FastAPI detects `frontend/dist` and serves it at `http://127.0.0.1:8000`.

## Configuration

Configuration is loaded from the project-root `.env` by `backend/app/config.py`.

### Model and server

| Variable | Default | Purpose |
|---|---|---|
| `POSEIDON_BASE_URL` | NVIDIA-compatible endpoint | OpenAI-compatible inference base URL |
| `POSEIDON_MODEL` | `nvidia/nemotron-3-ultra-550b-a55b` | Model identifier sent to the provider |
| `POSEIDON_API_KEY` | empty | Generic API key for the configured endpoint |
| `OPENROUTER_API_KEY` | empty | OpenRouter credential fallback |
| `NVIDIA_API_KEY` | empty | NVIDIA NIM credential |
| `KRAKEN_API_KEY` | empty | OpenAI-compatible paid-provider credential |
| `POSEIDON_HOST` | `127.0.0.1` | Backend bind address |
| `POSEIDON_PORT` | `8000` | Backend port |

The effective model and provider are visible through `GET /health` and in the frontend Settings/Telemetry views. Restart the backend after changing `.env`; already-created provider clients are cached in process.

### Harness and memory

| Variable | Default | Purpose |
|---|---:|---|
| `POSEIDON_MAX_ITERATIONS` | `5` | Maximum model-loop iterations per turn |
| `POSEIDON_MAX_TOOL_CALLS` | `5` | Maximum executed tool calls per turn |
| `POSEIDON_NOTE_MAX_LENGTH` | `500` | Maximum note/reminder length |
| `POSEIDON_NOTE_MAX_TOTAL` | `500` | Maximum stored notes plus reminders |
| `POSEIDON_OPERATOR_PIN` | empty | Optional step-up PIN for approvals |
| `POSEIDON_CONSOLIDATION_THRESHOLD` | `30` | Unconsolidated events required before automatic consolidation |
| `POSEIDON_EMBEDDING_MODEL` | `all-MiniLM-L6-v2` | Sentence-transformers embedding model |
| `POSEIDON_EMBEDDING_DIM` | `384` | Embedding dimension; must match the model |

### Telegram

| Variable | Default | Purpose |
|---|---|---|
| `TELEGRAM_BOT_TOKEN` | empty | Telegram bot token |
| `TELEGRAM_POLLING_ENABLED` | `false` | Start the local long poller with FastAPI |
| `TELEGRAM_ALLOWED_USER_IDS` | empty | Comma-separated Telegram sender IDs |
| `TELEGRAM_WEBHOOK_SECRET` | empty | Optional webhook secret-token check |

For safety, explicitly set `TELEGRAM_ALLOWED_USER_IDS` before enabling Telegram. In the current implementation, an empty allowlist accepts any Telegram sender who can reach the bot.

## API overview

| Method | Path | Purpose |
|---|---|---|
| `GET` | `/health` | Runtime, model, and Telegram status |
| `POST` | `/chat` | Execute one agent turn |
| `POST` | `/chat/approve` | Approve or deny a parked tool call |
| `POST` | `/security/inspect-tool` | Inspect tool-call risk and parameter differences |
| `GET` | `/memory/semantic` | Read/search semantic facts |
| `GET` | `/memory/episodic` | Read/retrieve episodic events |
| `GET` | `/memory/procedural` | List or match procedural skills |
| `GET` | `/memory/status` | Memory and consolidation status |
| `POST` | `/memory/consolidate` | Trigger consolidation |
| `GET/POST/PUT/DELETE` | `/agents...` | Manage file-backed agent definitions |
| `GET/PUT` | `/settings/llm...` | Inspect or update per-agent model configuration |
| `GET` | `/runs/{run_id}/trajectory` | Read an in-memory execution trajectory |
| `POST` | `/gateway/telegram/webhook` | Receive a Telegram update |

Example chat request:

```powershell
$body = @{
  text = "Remember that I prefer concise answers."
  user_id = "local_user"
  channel = "web"
} | ConvertTo-Json

Invoke-RestMethod `
  -Method Post `
  -Uri "http://127.0.0.1:8000/chat" `
  -ContentType "application/json" `
  -Body $body
```

## Local persistence

| Path | Contents |
|---|---|
| `memory-store/state.db` | Episodic events, vectors, semantic facts, and FTS5 index |
| `memory-store/notes.json` | Notes and reminders |
| `memory-store/calendar.json` | Poseidon-local calendar records |
| `memory-store/crm_data.json` | Poseidon-local contacts |
| `memory-store/memory/MEMORY.md` | Generated readable semantic-memory mirror |
| `memory-store/agents/*.soul.md` | Agent definitions and personas |
| `memory-store/skills/*.SKILL.md` | Procedural playbooks |
| `memory-store/llm_config.json` | Runtime per-agent provider overrides |
| `memory-store/mcp_config.json` | MCP server configuration placeholder |

Frontend chat sessions are stored separately in browser `localStorage`. They are UI history, not the backend's long-term memory. Opening the Vite frontend and the FastAPI-served build can therefore show different browser-side histories because they use different origins.

## Testing and checks

Backend:

```powershell
.\.venv\Scripts\python -m pytest backend\tests -q
```

Frontend:

```powershell
Set-Location frontend
npm run lint
npm run build
```

Tests should use temporary databases and storage paths. Do not point destructive test helpers at the real `memory-store/` directory.

## Current limitations

These are current implementation facts, not future promises:

- The HTTP APIs do not authenticate callers. Request bodies and query parameters can select `user_id`; do not expose the backend to an untrusted network.
- Notes, reminders, CRM contacts, calendar records, and procedural skills are shared local stores rather than fully user-scoped repositories.
- LangGraph is compiled without a durable checkpointer. Working memory, pending approvals, and execution trajectories are lost on process restart.
- The graph executes only the first tool call from a model response containing multiple tool calls.
- The taint/risk analyzer exists, but graph routing currently uses the registry's static tool tier rather than one unified taint-aware policy decision.
- `SandboxGuard` cannot safely isolate untrusted Python or third-party plugin code.
- DLP and prompt-risk detection are deterministic pattern-based safeguards, not comprehensive data-loss or prompt-injection prevention.
- MCP registration infrastructure exists, but external server lifecycle/discovery is not a complete general-purpose MCP client runtime.
- Telegram polling state and update deduplication are not durable across restarts. An empty Telegram allowlist is permissive.
- CORS currently allows all origins, which is suitable only for local development.
- The semantic `MEMORY.md` mirror is a single generated file and can be overwritten when different user IDs are consolidated.

The active backend hardening plan is in `docs/superpowers/plans/2026-10-02-backend-audit-remediation-plan.md`. Its planned capabilities should not be described as implemented until their acceptance tests pass.

## Design intent

Poseidon is currently best understood as a single-user, local-first agent laboratory: it exposes how memory hydration, tool calling, approvals, safety checks, agent routing, and observability fit together without hiding the execution loop. The roadmap retains LangGraph while improving identity ownership, durable approvals/checkpoints, user-scoped storage, unified policy enforcement, memory lifecycle management, and channel idempotency.
