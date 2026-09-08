# Poseidon — Governed Persistent-Memory Agent Harness

<p align="left">
  <img src="https://img.shields.io/badge/Python-3.10+-3776AB?style=flat-square&logo=python&logoColor=white" alt="Python 3.10+" />
  <img src="https://img.shields.io/badge/FastAPI-0.115+-009688?style=flat-square&logo=fastapi&logoColor=white" alt="FastAPI" />
  <img src="https://img.shields.io/badge/LangGraph-StateGraph-FF6F00?style=flat-square" alt="LangGraph" />
  <img src="https://img.shields.io/badge/Storage-SQLite%20+%20sqlite--vec-003B57?style=flat-square&logo=sqlite&logoColor=white" alt="SQLite & sqlite-vec" />
  <img src="https://img.shields.io/badge/Protocol-MCP%20Client-8A2BE2?style=flat-square" alt="Model Context Protocol" />
  <img src="https://img.shields.io/badge/Gateway-Telegram%20Dual--Mode-26A5E4?style=flat-square&logo=telegram&logoColor=white" alt="Telegram Gateway" />
  <img src="https://img.shields.io/badge/Frontend-React%2019%20+%20Vite-61DAFB?style=flat-square&logo=react&logoColor=black" alt="React 19 + Vite" />
  <img src="https://img.shields.io/badge/Design-Nothing%20Design%20System-000000?style=flat-square" alt="Nothing Design System" />
  <img src="https://img.shields.io/badge/License-MIT-blue.svg?style=flat-square" alt="License: MIT" />
</p>

Poseidon is a local-first, channel-agnostic execution harness for a persistent personal AI agent. It pairs a **four-tier cognitive memory architecture** (Working, Episodic, Semantic, and Procedural) with **bounded LangGraph execution**, **multi-provider LLM inference (Local Ollama, NVIDIA NIM, OpenAI, OpenRouter)**, **adaptive security guardrails (NoteGuard, DLP, sandboxed capabilities)**, and a **developer cockpit** designed under the Nothing Design System industrial aesthetic.

---

## Table of Contents

- [Project Overview](#project-overview)
- [Core Concepts](#core-concepts)
- [Repository Structure](#repository-structure)
- [Runtime & Request Flow](#runtime--request-flow)
- [Setup & Verified Commands](#setup--verified-commands)
- [Configuration & Environment Variables](#configuration--environment-variables)
- [Important APIs & Interfaces](#important-apis--interfaces)
- [Tools & Integrations](#tools--integrations)
- [Memory Hierarchy & Persistence](#memory-hierarchy--persistence)
- [Testing](#testing)
- [Deployment & Operations](#deployment--operations)
- [Current Limitations](#current-limitations)

---

## Project Overview

Standard LLM agent implementations suffer from context amnesia, uncontrolled execution loops, brittle tool dispatch, and host security vulnerabilities. 

Poseidon addresses these challenges by isolating agent execution inside a governed, local-first runtime harness:
- **Persistent Cognitive Memory:** Retains long-term personal facts, past conversations, and procedural playbooks across application restarts without expensive external vector database dependencies.
- **Governed Tool Execution:** Implements strict three-tier tool safety (`auto`, `guarded_auto`, `approval_required`), filesystem containment to `memory-store/`, execution timeouts, and outbound Data Loss Prevention (DLP) filtering.
- **Model Flexibility:** Connects to 100% private local models (Ollama) or high-performance cloud providers (NVIDIA NIM, OpenAI, OpenRouter) with runtime endpoint health verification.
- **Omni-Channel Operations:** Normalizes interactions across local Web interfaces, developer CLI tools, and a dual-mode Telegram bot adapter with user allowlisting and interactive human approval controls.
- **Industrial Observability:** Offers an interactive developer cockpit built on the Nothing Design System, providing real-time trajectory visualization, architecture topology CAD tracking, and memory hydration telemetry.

---

## Core Concepts

- **`InboundEvent` (`app.orchestration.state`):** The canonical cross-channel event schema. Encapsulates `user_id`, `channel`, `channel_thread_id`, `text`, `timestamp`, `is_tainted`, and `taint_sources`.
- **`AgentState` (`app.orchestration.state`):** Typed state container passed through the LangGraph cycle, accumulating message history, iteration count, tool call count, active approvals, and intermediate results.
- **`MemoryEngine` (`app.memory.memory_engine`):** Unified deep facade orchestrating context hydration across the four cognitive memory tiers and handling conversational turn persistence.
- **`NoteGuard` (`app.security.note_guard`):** Three-tier adaptive pre-write validator:
  - `Tier 1 (ALLOW)`: Benign personal notes auto-save instantly.
  - `Tier 2 (SUSPICIOUS)`: Content with URLs, IPs, credentials, or sensitive keywords pauses execution and requests human approval.
  - `Tier 3 (REJECT)`: Prompt delimiters (`<|im_start|>`), jailbreaks, or injection attempts are hard-blocked.
- **`SandboxGuard` (`app.security.sandbox`):** In-process capability jail enforcing filesystem confinement to `memory-store/`, argument traversal sanitization, 5.0-second execution timeouts, and strict shell/terminal execution prohibition.
- **`DLPScanner` (`app.security.dlp`):** Pre-compiled regular expression firewall redacting credentials (OpenAI, Anthropic, AWS, Google, GitHub), bearer tokens, private keys, credit cards, and SSNs before responses egress the system.
- **`TelegramLongPoller` (`app.gateway.telegram_adapter`):** Local background runner that pulls updates directly from the Telegram Bot API over outbound HTTPS. Operates behind firewalls/NATs without public IP addresses, domain names, or reverse proxies.
- **Nothing Design System (`nothing-design` + `ui-ux-pro-max`):** Frontend interface architecture utilizing a pure black OLED background (`#000000`), 24px dot-matrix ambient grid, graphite pill containers (`#111111`, `#1A1A1A`), crisp 1px borders without drop shadows, and functional accent red (`#D71921`).

---

## Repository Structure

```
Poseidon/
├── backend/
│   ├── app/
│   │   ├── main.py                    # FastAPI application entrypoint & lifespan lifecycle
│   │   ├── config.py                  # Pydantic BaseSettings configuration loader
│   │   ├── soul.py                    # Poseidon agent persona loader & prompt assembler
│   │   ├── llm_providers.py           # Multi-provider LLM manager (Local/Cloud/Custom)
│   │   ├── gateway/
│   │   │   ├── web_adapter.py         # HTTP /chat and approval REST endpoints
│   │   │   ├── telegram_adapter.py    # Dual-mode Telegram runner (Long-Polling & Webhook)
│   │   │   ├── agents_adapter.py      # Agent settings & LLM configuration REST endpoints
│   │   │   ├── memory_adapter.py      # /memory/* REST endpoints
│   │   │   └── trajectory_adapter.py  # /runs/{run_id}/trajectory REST endpoint
│   │   ├── orchestration/
│   │   │   ├── graph.py               # LangGraph StateGraph execution pipeline
│   │   │   ├── router.py              # Inbound intent router
│   │   │   ├── state.py               # AgentState and InboundEvent data schemas
│   │   │   ├── approval_store.py      # In-memory parked action store for HITL
│   │   │   └── trajectory.py          # Granular step telemetry recorder
│   │   ├── agents/
│   │   │   ├── qa_agent.py            # Primary conversational execution agent
│   │   │   └── summarizer_agent.py    # Background consolidation distillation agent
│   │   ├── memory/
│   │   │   ├── memory_engine.py       # Unified deep facade for 4-tier cognitive memory
│   │   │   ├── working_memory.py      # Backward-compatible context hydration wrapper
│   │   │   ├── episodic_store.py      # SQLite WAL + sqlite-vec dense vector store
│   │   │   ├── semantic_store.py      # SQLite FTS5 BM25 store + MEMORY.md mirror
│   │   │   ├── procedural_store.py    # *.SKILL.md playbook trigger matcher
│   │   │   ├── consolidation.py       # Threshold trigger for background distillation
│   │   │   └── embeddings.py          # sentence-transformers embedding service
│   │   ├── tools/
│   │   │   ├── registry.py            # Central tool catalog & unified function schemas
│   │   │   ├── mcp_manager.py         # Model Context Protocol client & loader
│   │   │   ├── calendar.py            # Calendar read & create tool handlers
│   │   │   ├── crm.py                 # CRM read & write tool handlers
│   │   │   ├── notes_reminders.py     # Notes read, create, and delete tool handlers
│   │   │   ├── skill_manage.py        # Procedural skill read & write tool handlers
│   │   │   └── _storage.py            # Local JSON persistent helper
│   │   └── security/
│   │       ├── note_guard.py          # 3-tier adaptive write validator for notes
│   │       ├── sandbox.py             # Path jailing, timeout, and no-shell sandbox
│   │       ├── dlp.py                 # Outbound credential and PII regex scanner
│   │       ├── taint.py               # Channel trust tracking and risk evaluator
│   │       ├── adversarial_filter.py  # Anti-memory poisoning & injection filter
│   │       └── risk_analyzer.py       # Parameter diffing and risk classification
│   ├── tests/                         # Comprehensive pytest test suite (19 test modules)
│   └── requirements.txt               # Backend dependencies
│
├── frontend/                          # Developer Cockpit (React 19 + Vite)
│   ├── src/
│   │   ├── App.jsx                    # 3-panel workspace layout & route configuration
│   │   ├── main.jsx                   # React root mount
│   │   ├── api/                       # API client modules (chat, agents, memory)
│   │   ├── context/                   # React Contexts (Chat, Health, Agent, Theme)
│   │   ├── components/
│   │   │   ├── ChatDock/              # Chat canvas, status ribbon, prompt input box
│   │   │   ├── LeftSidebar/           # Sessions list, history search, navigation
│   │   │   ├── RightPanel/            # Resizable Inspector (Turn, Topology, Telemetry)
│   │   │   ├── ArchitectureMap/       # Interactive SVG topology CAD map
│   │   │   ├── TrajectoryView/        # Turn-by-turn execution telemetry inspector
│   │   │   ├── ApprovalCard/          # Inline tool approval card with parameter diffs
│   │   │   └── common/                # Shared UI primitives (Card, TabBar, Badges)
│   │   ├── pages/
│   │   │   ├── Gateway/               # Cross-channel API message ledger
│   │   │   ├── Settings/              # Models, Memory Studio, and Guardrails studio
│   │   │   └── Overview/              # System architecture & diagnostic summary
│   │   └── styles/                    # Nothing Design System CSS tokens & base styles
│   ├── package.json
│   └── vite.config.js                 # Vite dev proxy configuration
│
├── memory-store/                      # Persistent runtime storage
│   ├── state.db                       # SQLite database (episodic, vector, semantic FTS5)
│   ├── agents/
│   │   └── poseidon.soul.md           # Poseidon agent persona and system configuration
│   ├── memory/
│   │   └── MEMORY.md                  # Auto-generated human-readable semantic mirror
│   ├── skills/
│   │   └── *.SKILL.md                 # Procedural skill playbooks
│   ├── mcp_config.json                # Model Context Protocol server configuration
│   └── llm_config.json                # Runtime LLM provider overrides
│
├── GUARDRAILS.md                      # Source-of-truth security policies and tool tiers
├── CONTEXT.md                         # Platform terminology and design system standards
├── README.md                          # Repository documentation
└── .env.example                       # Environment configuration template
```

---

## Runtime & Request Flow

1. **Inbound Ingestion & Normalization:**
   - A request arrives via HTTP `POST /chat` or through Telegram.
   - The gateway computes channel provenance and risk via `calculate_overall_risk()`. Third-party sources are tagged as tainted (`is_tainted=True`).
   - The payload is normalized into an `InboundEvent`.

2. **Context Hydration:**
   - `MemoryEngine.hydrate_context()` queries all memory tiers in parallel:
     - Retrieves relevant procedural playbooks (`*.SKILL.md`) matching keywords in the prompt.
     - Performs SQLite FTS5 BM25 search to pull the top-$k$ relevant semantic facts.
     - Queries `sqlite-vec` for dense vector KNN cosine similarity, blending it with recent chronological episodic turns.
     - Loads active in-memory session history turns.
   - Assembles the complete message list initialized with Poseidon's system prompt.

3. **LangGraph State Machine Execution:**
   - The message list is injected into `AgentState` and passed to `agent_node`.
   - The agent invokes the configured LLM through `LLMProvider`.
   - `next_step` conditional routing evaluates model tool calls:
     - **No tool call:** The response proceeds to the output stage.
     - **Iteration / Tool limits exceeded:** Execution routes to `limit_node` to prevent runaway loops.
     - **`auto` tier tools:** Dispatched directly to `tool_executor`.
     - **`guarded_auto` tools (`notes_reminders_create`):** Dispatched to `guarded_tool_executor` where `NoteGuard.inspect()` executes. If suspicious patterns are detected, execution raises `SuspiciousNoteError` and redirects to `approval_gate`.
     - **`approval_required` tools:** Routed to `approval_gate`. The action is parked in `approval_store`, pausing execution and emitting an `approval_request` payload.

4. **Human-in-the-Loop Resumption:**
   - The operator reviews parameters and structural diffs via the Web ApprovalCard or Telegram.
   - An approval or denial decision is posted to `POST /chat/approve` (or sent via `/approve [PIN]` in Telegram).
   - `resume_approval()` loads the parked state, executes the tool via `SandboxGuard`, and resumes the LangGraph cycle.

5. **Output Governance & Persistence:**
   - Generated model responses pass through `DLPScanner.scan_and_redact()`. Any detected credentials or sensitive tokens are masked.
   - The sanitized reply is returned to the originating channel.
   - `MemoryEngine.record_turn()` stores the exchange in the episodic database (`state.db`) and generates embeddings.
   - If unconsolidated turns exceed `POSEIDON_CONSOLIDATION_THRESHOLD`, background consolidation triggers automatically.

---

## Setup & Verified Commands

### Prerequisites
- Python 3.10+
- Node.js 18+ and npm

### 1. Environment Configuration

```bash
# In project root
cp .env.example .env
```

Edit `.env` to configure your preferred LLM provider keys and server settings.

### 2. Backend Execution

```bash
# From Poseidon/backend
python -m venv venv

# Windows
venv\Scripts\activate

# Linux / macOS
# source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Start FastAPI with auto-reload
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

### 3. Frontend Execution (Development)

```bash
# From Poseidon/frontend
npm install

# Start Vite development server
npm run dev
```
Open `http://localhost:5173`. API requests are automatically proxied to `http://127.0.0.1:8000`.

### 4. Single-Process Production Bundle

```bash
# 1. Build the frontend client
cd Poseidon/frontend
npm run build

# 2. Start FastAPI backend (automatically serves frontend/dist static bundle)
cd ../backend
uvicorn app.main:app --host 127.0.0.1 --port 8000
```
Access the complete application at `http://127.0.0.1:8000/`.

---

## Configuration & Environment Variables

All settings are defined and validated in `backend/app/config.py`:

| Variable | Type | Default | Description |
|---|---|---|---|
| `OPENROUTER_API_KEY` | string | `""` | OpenRouter API authentication key |
| `NVIDIA_API_KEY` | string | `""` | NVIDIA NIM API key for cloud-free models |
| `KRAKEN_API_KEY` | string | `""` | Optional commercial OpenAI key for paid model tiers |
| `POSEIDON_API_KEY` | string | `""` | Direct fallback API key |
| `POSEIDON_MODEL` | string | `nvidia/nemotron-3-ultra-550b-a55b` | Default model identifier |
| `POSEIDON_BASE_URL` | string | `https://integrate.api.nvidia.com/v1` | OpenAI-compatible base URL endpoint |
| `POSEIDON_HOST` | string | `127.0.0.1` | Backend bind host address |
| `POSEIDON_PORT` | int | `8000` | Backend bind port |
| `POSEIDON_MAX_ITERATIONS` | int | `5` | Maximum agent reasoning cycles per turn |
| `POSEIDON_MAX_TOOL_CALLS` | int | `5` | Maximum tool calls permitted per turn |
| `POSEIDON_MAX_APPROVAL_REQUESTS_PER_HOUR` | int | `5` | Rate cap on human approval alerts |
| `POSEIDON_OUTBOUND_MSG_RATE_LIMIT` | int | `20` | Rate cap on outbound messages per hour |
| `POSEIDON_CRONJOB_APPROVAL_TIMEOUT_HOURS` | int | `12` | Expiration window for unattended actions |
| `POSEIDON_NOTE_MAX_LENGTH` | int | `500` | Maximum character length for a single note |
| `POSEIDON_NOTE_MAX_TOTAL` | int | `500` | Maximum combined notes and reminders in storage |
| `POSEIDON_OPERATOR_PIN` | string | `""` | Optional PIN for step-up verification on approvals |
| `POSEIDON_CONSOLIDATION_THRESHOLD` | int | `30` | Unconsolidated turn count triggering background distillation |
| `POSEIDON_DB_PATH` | Path | `memory-store/state.db` | Filesystem path to SQLite database |
| `POSEIDON_EMBEDDING_MODEL` | string | `all-MiniLM-L6-v2` | Sentence-transformers vector model |
| `POSEIDON_EMBEDDING_DIM` | int | `384` | Vector dimension size (must match embedding model) |
| `TELEGRAM_BOT_TOKEN` | string | `""` | Telegram Bot API token |
| `TELEGRAM_ALLOWED_USER_IDS` | string | `""` | Comma-separated list of permitted Telegram user IDs |
| `TELEGRAM_POLLING_ENABLED` | bool | `false` | Enable local background long-polling runner |
| `TELEGRAM_WEBHOOK_SECRET` | string | `""` | Secret token for validating incoming Telegram webhooks |

---

## Important APIs & Interfaces

### Chat & Execution Endpoints

- **`POST /chat`**
  - **Payload:** `{"text": string, "user_id"?: string, "channel"?: string}`
  - **Response:**
    ```json
    {
      "reply": "I have created your note for tomorrow's meeting.",
      "run_id": "8f3b2164-...",
      "approval_request": null,
      "active_agent": "poseidon",
      "memory_context": {
        "semantic_facts": ["User prefers Python and Rust"],
        "episodic_events": ["User mentioned project deadline on Friday"],
        "procedural_skills": ["note_taking_routine"]
      },
      "trajectory": [...]
    }
    ```

- **`POST /chat/approve`**
  - **Payload:** `{"approval_id": string, "decision": "approved" | "denied"}`
  - **Response:** `{"status": "completed", "reply": string, "run_id": string}`

- **`POST /security/inspect-tool`**
  - **Payload:** `{"tool_name": string, "arguments": object, "is_tainted"?: bool, "original_values"?: object}`
  - **Response:** `{"risk_level": "high" | "medium" | "low", "has_dangerous_params": bool, "param_diff": object, "warnings": string[]}`

- **`GET /health`**
  - **Response:** `{"status": "ok", "model": string, "provider": string, "configured": bool, "mode": "local-first", "telegram_polling": bool}`

- **`GET /runs/{run_id}/trajectory`**
  - **Response:** `{"run_id": string, "count": int, "steps": object[]}`

### Memory Endpoints

- **`GET /memory/semantic?query={query}&category={category}&limit={limit}`**: Retrieve filtered semantic facts.
- **`GET /memory/episodic?query={query}&since={iso_timestamp}&limit={limit}`**: Retrieve chronological or similarity-ranked episodic events.
- **`GET /memory/procedural?query={query}`**: List or search procedural skill playbooks.
- **`POST /memory/consolidate`**: Force background memory consolidation (`{"user_id": "local_user", "force": true}`).
- **`GET /memory/status?user_id={user_id}`**: Telemetry on fact counts, loaded skills, and unconsolidated chat count.

### Settings & Gateway Endpoints

- **`GET /settings/llm`**: Get active provider configurations.
- **`PUT /settings/llm/{agent_id}`**: Update provider preset (`local`, `cloud_free`, `cloud_paid`, `custom`), model, or endpoint.
- **`GET /settings/llm/check/{agent_id}`**: Check endpoint network reachability.
- **`POST /gateway/telegram/webhook`**: Inbound webhook for server deployments (requires `X-Telegram-Bot-Api-Secret-Token`).

---

## Tools & Integrations

### Native Tool Catalog

| Tool Name | Approval Tier | Description |
|---|---|---|
| `crm_read` | `auto` | Query local contacts, relationships, and metadata (`contacts.json`). |
| `crm_write` | `approval_required` | Create, update, or delete local CRM records. |
| `notes_reminders_read` | `auto` | Read stored personal notes and reminders (`notes_reminders.json`). |
| `notes_reminders_create` | `guarded_auto` | Create notes or reminders. Evaluated by NoteGuard; suspicious patterns escalate to human approval. |
| `notes_reminders_delete` | `approval_required` | Permanently delete stored notes or reminders. |
| `calendar_read` | `auto` | Read upcoming events and schedule details (`calendar.json`). |
| `calendar_create` | `approval_required` | Schedule new calendar events. |
| `skill_manage_read` | `auto` | Inspect loaded procedural memory skills in `memory-store/skills/`. |
| `skill_manage_write` | `approval_required` | Create or update procedural skill files on disk. |

### Model Context Protocol (MCP) Manager (`app/tools/mcp_manager.py`)

External capabilities can be connected declaratively via `memory-store/mcp_config.json`:
- Supports `stdio` and external process servers.
- Discovered tools are dynamically mapped to OpenAI function schemas.
- **Fail-safe governance:** Every MCP tool defaults to `approval_required` unless explicitly designated as read-only.

### Sandbox Isolation (`app/security/sandbox.py`)

Every tool executes inside `SandboxGuard`:
- **Directory Path Jailing:** File operations must resolve strictly within canonical paths under `memory-store/`. Path traversal (`..`) or absolute system path escapes trigger `SandboxSecurityError`.
- **Execution Timeouts:** Enforces a 5.0-second timeout per tool execution.
- **Terminal Prohibition:** Rejects any invocation matching shell, bash, or terminal execution patterns.

---

## Memory Hierarchy & Persistence

Poseidon stores all durable state locally under `memory-store/`:

1. **Working Memory (In-RAM):** Assembled per turn by `MemoryEngine`. Combines Poseidon's system prompt, active procedural skills, top-$k$ semantic facts, hybrid episodic turns, and recent in-memory session history.
2. **Episodic Memory (`memory-store/state.db`):** Chronological log of conversational turns stored in SQLite with WAL enabled. Embeddings (384-dim) are stored in the `episodic_vectors` virtual table via `sqlite-vec`.
3. **Semantic Memory (`memory-store/state.db` & `memory-store/memory/MEMORY.md`):** Durable profile data and facts stored in `semantic_facts` and indexed via FTS5 BM25 keyword search. Synchronously mirrored to `MEMORY.md` for human inspection.
4. **Procedural Memory (`memory-store/skills/*.SKILL.md`):** Markdown playbooks with YAML frontmatter defining multi-step routines. Injected into context when user prompts match defined trigger keywords.
5. **Background Consolidation:** When unconsolidated turns cross `POSEIDON_CONSOLIDATION_THRESHOLD`, `SummarizerAgent` distills raw turns into durable facts, verifies them through `AdversarialReviewer`, commits to `semantic_facts`, and regenerates `MEMORY.md`.

---

## Testing

The backend includes a comprehensive pytest test suite covering storage, orchestration, security, and adapters:

```bash
cd Poseidon/backend

# Run all test suites
pytest

# Run tests with detailed verbose output
pytest -v

# Run a specific test module
pytest tests/test_security_note_guard.py
pytest tests/test_telegram_adapter.py
pytest tests/test_mcp_integration.py
```

### Verified Test Modules (`backend/tests/`):
- `test_agents_adapter.py`: REST API agent settings and trajectory endpoints.
- `test_consolidation.py`: Background distillation pipeline and threshold logic.
- `test_episodic_store.py`: SQLite WAL and `sqlite-vec` KNN similarity queries.
- `test_harness_approval_resumption.py`: Parked tool action state and resume flow.
- `test_llm_providers.py`: Provider resolution and mock inference dispatch.
- `test_mcp_integration.py`: MCP configuration parsing and dynamic tool discovery.
- `test_memory_api.py`: `/memory/*` HTTP endpoints.
- `test_memory_engine.py`: 4-tier context hydration and turn recording.
- `test_procedural_store.py`: Skill playbook parsing and keyword trigger matching.
- `test_sandbox_guard.py`: Filesystem jailing, execution timeouts, and shell blocks.
- `test_security_adversarial_filter.py`: Anti-memory poisoning regex rules.
- `test_security_dlp.py`: Outbound credential and token redaction scanner.
- `test_security_risk_analyzer.py`: Parameter diffing and risk classification.
- `test_security_taint.py`: Channel trust tracking and tier downgrading.
- `test_semantic_store.py`: SQLite FTS5 BM25 recall and `MEMORY.md` mirroring.
- `test_soul.py`: Agent configuration parsing and prompt assembly.
- `test_telegram_adapter.py`: Long-polling, webhook secret verification, and PIN approvals.
- `test_working_memory.py`: Context assembly and backward compatibility.

Frontend linting:
```bash
cd Poseidon/frontend
npm run lint
```

---

## Deployment & Operations

### Local Long-Polling Telegram Setup
1. Message [@BotFather](https://t.me/BotFather) on Telegram to generate a bot token.
2. Retrieve your numeric Telegram user ID from [@userinfobot](https://t.me/userinfobot).
3. Configure `.env`:
   ```dotenv
   TELEGRAM_BOT_TOKEN=123456789:ABCdefGHIjklMNOpqrSTUvwxYZ
   TELEGRAM_POLLING_ENABLED=true
   TELEGRAM_ALLOWED_USER_IDS=987654321
   ```
4. Start the backend. `TelegramLongPoller` runs inside the FastAPI lifespan, polling Telegram directly from your machine behind firewalls or NATs.
5. In Telegram chat:
   - Send regular prompts to interact with Poseidon.
   - When an action requires confirmation, reply with `/approve` (or `/approve <PIN>` if `POSEIDON_OPERATOR_PIN` is set), or `/deny` to cancel.

### Webhook Deployment (Server Deployments)
When deploying to a public VPS with a domain and TLS certificate:
1. Configure `.env`:
   ```dotenv
   TELEGRAM_BOT_TOKEN=123456789:ABCdefGHIjklMNOpqrSTUvwxYZ
   TELEGRAM_POLLING_ENABLED=false
   TELEGRAM_WEBHOOK_SECRET=your-secure-webhook-secret
   ```
2. Register the webhook with Telegram:
   ```bash
   curl -F "url=https://your-domain.com/gateway/telegram/webhook" \
        -F "secret_token=your-secure-webhook-secret" \
        https://api.telegram.org/bot<TELEGRAM_BOT_TOKEN>/setWebhook
   ```

---

## Current Limitations

1. **Single Agent Focus:** Poseidon operates as a singular personal assistant. Multi-agent delegation and dynamic agent routing are currently shelved.
2. **No Arbitrary Shell Access:** Host command line and terminal execution tools are strictly prohibited to safeguard host integrity.
3. **No Web Fetch / Browser Automation:** Automated web search and browser interaction capabilities are not implemented in the v1 runtime.
4. **Local Embedding Compute:** Vector embeddings utilize local CPU execution via `sentence-transformers` (`all-MiniLM-L6-v2`), which requires initial model weight download (~80MB).
5. **Fail-Closed MCP Approvals:** MCP tools default to `approval_required` and must be manually allowlisted before auto-running.

---

<p align="center">
  <sub>Poseidon Persistent-Memory Agent Harness • Local-First • Governed • Privacy-Centric</sub>
</p>
