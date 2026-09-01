# Poseidon — Persistent-Memory Agent Harness

A channel-agnostic, local-first personal AI agent harness featuring a **four-tier persistent memory system**, **multi-layered security and guardrail governance**, and an **interactive developer cockpit**.

---

## Current Status

### What is Implemented So Far

| Subsystem / Capability | Implemented Details |
|---|---|
| **Gateway Layer (Web/CLI)** | Normalized `InboundEvent` schema, FastAPI `POST /chat` adapter, per-user channel thread handling. |
| **Working Memory** | In-process dynamic assembly combining system prompt, active procedural playbooks, top-$k$ semantic facts, hybrid episodic history, and live session turns. |
| **Episodic Memory** | SQLite storage (`memory-store/state.db`) with WAL mode, `sqlite-vec` vector index (384-dim normalized embeddings via local `sentence-transformers`), and blended vector KNN relevance + SQL recency retrieval. |
| **Semantic Memory** | SQLite `semantic_facts` with automated FTS5 keyword indexing (`semantic_fts` + SQL triggers) for BM25 top-$k$ fact recall, plus an auto-regenerated Markdown mirror (`memory-store/memory/MEMORY.md`). |
| **Procedural Memory** | Filesystem-backed `*.SKILL.md` parser with YAML frontmatter and case-insensitive trigger keyword matching (`memory-store/skills/`). |
| **Consolidation Pipeline** | Configurable $N$-chat threshold trigger (default: 30 new chats) running the `SummarizerAgent` to distill raw episodes into durable facts and skills, with unconsolidated episode tracking. |
| **Security: Outbound DLP** | Pre-compiled regex firewall (`DLPScanner`) scanning LLM responses to redact API keys (OpenAI, Anthropic, Google, AWS, GitHub, Bearer), private keys, SSNs, and credit cards. |
| **Security: Taint Tracking** | Dynamic provenance tagging for untrusted inbound channels and automated downgrading of read tools to approval-required when context is tainted. |
| **Security: Anti-Poisoning Filter** | Memory write gate (`AdversarialReviewer`) rejecting prompt injections, system overrides, jailbreak phrases, malicious URLs/webhooks, and shell execution patterns before database commit. |
| **Security: Risk & Diff Analysis** | Pre-approval analyzer (`RiskAnalyzer`) classifying tool invocations by risk tier (Low / Medium / High), scanning arguments for dangerous patterns, and computing parameter before/after diffs. |
| **Frontend Cockpit** | React 19 + Vite dashboard featuring 3-panel workspace: Left sidebar (multi-session manager, search, theme switcher), Center canvas (Chat, Trajectory step viewer, Security Gate tab), Right panel (resizable CAD Topology map), and Gateway API Ledger. |

### Planned Future Implementation

| Feature / Subsystem | Planned Details |
|---|---|
| **Live Agentic Tool Execution** | Live execution connectors for external APIs (Google Calendar, CRM backends, live external MCP tool servers). |
| **Sub-Agent Delegation** | Multi-agent task delegation (`delegate_task`) with scoped sub-agent Working Memory slices. |
| **Additional Channels** | Additional adapters for external messaging platforms (e.g., Telegram, Slack, WhatsApp). |
| **LLM Ops & Automated Evals** | Standalone Langfuse/LangSmith tracing, LLM-as-a-judge scoring, and automated release gating. |

### Non-Goals & Architecture Decisions

- **Host Terminal Execution:** Per specification and [GUARDRAILS.md](GUARDRAILS.md), no raw shell or terminal tool is registered in v1 to protect host integrity.

---

## Architecture Overview

```
                      ┌─────────────────────────────────────────┐
                      │             GATEWAY ADAPTER             │
                      │   Web/CLI  (Telegram / Slack — Future)  │
                      │           → InboundEvent                │
                      └────────────────────┬────────────────────┘
                                           │
                                           ▼
                      ┌─────────────────────────────────────────┐
                      │          WORKING MEMORY ASSEMBLY        │
                      │ System Prompt + Procedural Playbooks    │
                      │ + Semantic Facts + Episodic History     │
                      │ + In-RAM Session Store + User Prompt    │
                      └────────────────────┬────────────────────┘
                                           │
                                           ▼
                      ┌─────────────────────────────────────────┐
                      │           LANGGRAPH ORCHESTRATOR        │
                      │   START → QA Agent (OpenRouter) → END   │
                      └────────────────────┬────────────────────┘
                                           │
                                           ▼
                      ┌─────────────────────────────────────────┐
                      │          OUTBOUND DLP FIREWALL          │
                      │  Scans & Redacts Leaked Keys / Secrets  │
                      └──────────────┬──────────────────┬───────┘
                                     │                  │
                Raw Turn Log         │                  │ Sanitized Output
                      ▼              ▼                  ▼
          ┌───────────────────────────────┐      ┌─────────────┐
          │       EPISODIC STORE          │      │   GATEWAY   │
          │ state.db (SQLite + sqlite-vec)│      │  RESPONSE   │
          └──────────────┬────────────────┘      └─────────────┘
                         │
              Every N new chats (e.g. 30)
                         │
                         ▼
          ┌───────────────────────────────┐
          │       SUMMARIZER AGENT        │
          │ Distills facts & playbooks    │
          └──────────────┬────────────────┘
                         │
                         ▼
          ┌───────────────────────────────┐
          │  ADVERSARIAL POISONING FILTER │
          │ Rejects injections / overrides│
          └──────────────┬────────────────┘
                         │
            Safe Facts   │   Safe Skills
            ┌────────────┴────────────┐
            ▼                         ▼
  ┌───────────────────┐     ┌───────────────────┐
  │   SEMANTIC STORE  │     │ PROCEDURAL STORE  │
  │ SQLite FTS5 +     │     │ memory-store/     │
  │ MEMORY.md mirror  │     │ skills/*.SKILL.md │
  └───────────────────┘     └───────────────────┘
```

---

## Memory Subsystems

### 1. Working Memory (`backend/app/memory/working_memory.py`)
- **Lifecycle:** Ephemeral (per-run), assembled fresh on every message turn.
- **Assembly Order:** Base system prompt $\rightarrow$ active procedural playbooks $\rightarrow$ top-$k$ semantic facts $\rightarrow$ blended episodic history $\rightarrow$ live session chat turns $\rightarrow$ current user prompt.
- **Session Store:** In-memory dictionary holding recent turns for immediate conversational continuity within a running server process.

### 2. Episodic Memory (`backend/app/memory/episodic_store.py`)
- **Storage:** SQLite (`memory-store/state.db`) with Write-Ahead Logging (`PRAGMA journal_mode=WAL;`).
- **Vector Indexing:** `sqlite-vec` extension storing 384-dimensional normalized vector embeddings generated offline by `sentence-transformers` (`all-MiniLM-L6-v2`).
- **Retrieval Engine:** Blends vector KNN semantic similarity (`search_relevant`) and SQL recency (`get_recent`), deduplicating events by ID and sorting chronologically.

### 3. Semantic Memory (`backend/app/memory/semantic_store.py`)
- **Storage:** SQLite table `semantic_facts` mirrored into an FTS5 virtual table (`semantic_fts`) via automated SQL insert/update/delete triggers.
- **Retrieval Engine:** BM25 keyword top-$k$ search — intentionally deterministic, fast, and independent of external embedding models for concise personal facts.
- **Human-Readable Mirror:** Automatically regenerates `memory-store/memory/MEMORY.md` whenever facts are added, modified, or soft-deleted.

### 4. Procedural Memory (`backend/app/memory/procedural_store.py`)
- **Storage:** Plain Markdown files (`*.SKILL.md`) with YAML frontmatter stored in `memory-store/skills/`.
- **Retrieval Engine:** Case-insensitive trigger phrase matching against user messages to inject relevant operational playbooks into Working Memory.

### 5. Consolidation Pipeline (`backend/app/memory/consolidation.py` & `backend/app/agents/summarizer_agent.py`)
- **Mechanism:** Tracks unconsolidated episodic entries. When crossing the configured threshold $N$ (default: 30 chats), it activates the `SummarizerAgent`.
- **Extraction:** Distills durable facts (categorized as *preference*, *profile*, *relationship*, or *general*) and repeatable procedural workflows.
- **Security Check:** Passes all candidate items through the `AdversarialReviewer` before writing to disk, then flags the source episodes as consolidated.

---

## Security & Guardrails

Poseidon includes a defense-in-depth security framework built across four modules:

1. **Outbound Data Loss Prevention (`backend/app/security/dlp.py`):**
   - Intercepts all generated LLM responses before delivery.
   - Redacts OpenAI, Anthropic, Google, AWS, and GitHub credentials, Bearer tokens, private keys, credit cards, and SSNs.
2. **Taint Tracking & Data Provenance (`backend/app/security/taint.py`):**
   - Labels incoming messages with trust levels (`TRUSTED` for local Web/CLI; `UNTRUSTED` for external channels).
   - Automatically downgrades auto-run read tools to require operator approval when operating on tainted data.
3. **Anti-Poisoning Reviewer (`backend/app/security/adversarial_filter.py`):**
   - Validates memory candidates against heuristic injection patterns, system override phrases, malicious webhook domains (`.ru`, `webhook.site`, `ngrok.io`), SQL injection, and destructive commands.
4. **Risk Analyzer & Parameter Diffing (`backend/app/security/risk_analyzer.py`):**
   - Analyzes tool parameters, calculates parameter before/after diffs, and computes risk ratings (`high`, `medium`, `low`) for the frontend approval gate.

See [GUARDRAILS.md](GUARDRAILS.md) for the full guardrail policy and tool tier specifications.

---

## Frontend Developer Cockpit

The frontend is a lightweight React 19 + Vite cockpit with vanilla CSS design tokens matching the system specification:

- **3-Panel Workspace:**
  - **Left Sidebar:** Session drawer with full chat history, quick search, session rename/delete, new session creation, Light/Dark theme toggle, and gateway navigation.
  - **Center Canvas:** Interaction area with markdown message rendering, auto-scrolling, session export to JSON, and tab switching between **Chat**, **Trajectory** (turn breakdown), and **Security Gate** (interactive approval cards).
  - **Right Panel:** Collapsible and resizable inspector displaying an interactive SVG **Architecture Topology CAD Map** that pulses active subsystem nodes during execution.
- **Gateway & API Ledger Page (`/gateway`):**
  - Cross-channel event ledger displaying message direction (`IN`/`OUT`), timestamps, channel badges, content previews, and one-click Run ID copying.

---

## API Surface

### Gateway & Chat Endpoints

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/chat` | Submit a chat prompt; returns LLM reply, `run_id`, and evaluated `approval_request` (if applicable). |
| `GET` | `/health` | Health check endpoint returning backend status and active model identifier. |
| `POST` | `/security/inspect-tool` | Inspect tool call arguments for security risks, parameter diffs, and warnings. |

### Memory Endpoints

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/memory/semantic` | Retrieve active semantic facts with optional `category`, `query`, and `limit` filters. |
| `GET` | `/memory/episodic` | Retrieve episodic events with optional `since` ISO timestamp, `query`, and `limit` filters. |
| `GET` | `/memory/procedural` | List all loaded procedural skills or query matching skills by task trigger. |
| `POST` | `/memory/consolidate` | Manually trigger memory consolidation over unconsolidated episodic events. |
| `GET` | `/memory/status` | Retrieve memory statistics (fact count, skill count, unconsolidated chat count). |

---

## Project Structure

```
Poseidon/
├── backend/
│   ├── app/
│   │   ├── main.py                    # FastAPI entry point & static file server
│   │   ├── config.py                  # Pydantic Settings (.env configuration)
│   │   ├── gateway/
│   │   │   ├── web_adapter.py         # HTTP /chat adapter and InboundEvent creation
│   │   │   └── memory_adapter.py      # /memory/* REST endpoints
│   │   ├── orchestration/
│   │   │   ├── graph.py               # LangGraph StateGraph execution pipeline
│   │   │   └── state.py               # AgentState and InboundEvent data schemas
│   │   ├── agents/
│   │   │   ├── qa_agent.py            # Primary conversational agent (OpenRouter / OpenAI SDK)
│   │   │   └── summarizer_agent.py    # Background consolidation & memory distillation agent
│   │   ├── memory/
│   │   │   ├── working_memory.py      # Dynamic Working Memory assembly & session store
│   │   │   ├── episodic_store.py      # SQLite + sqlite-vec hybrid episodic store
│   │   │   ├── semantic_store.py      # SQLite + FTS5 semantic store & MEMORY.md mirror
│   │   │   ├── procedural_store.py    # *.SKILL.md loader and trigger matcher
│   │   │   ├── consolidation.py       # Threshold manager for episodic distillation
│   │   │   └── embeddings.py          # Local sentence-transformers embedding service
│   │   ├── security/
│   │   │   ├── dlp.py                 # Outbound Data Loss Prevention scanner
│   │   │   ├── taint.py               # Channel taint tracking & tool tier downgrading
│   │   │   ├── adversarial_filter.py  # Anti-memory poisoning & injection filter
│   │   │   └── risk_analyzer.py       # Tool parameter inspection & diff generator
│   │   └── prompts/
│   │       └── system_prompt.md       # Base system prompt template
│   ├── tests/                         # Comprehensive pytest test suite
│   └── requirements.txt               # Backend dependencies
│
├── frontend/                          # React + Vite developer cockpit
│   ├── src/
│   │   ├── App.jsx                    # 3-panel workspace layout & routing
│   │   ├── components/
│   │   │   ├── ChatDock/              # Chat canvas, message stream, subheader tabs
│   │   │   ├── LeftSidebar/           # Session management, search, theme switcher
│   │   │   ├── RightPanel/            # Resizable side inspector window
│   │   │   ├── ArchitectureMap/       # Live SVG topology CAD diagram
│   │   │   ├── TrajectoryView/        # Step-by-step turn execution inspector
│   │   │   ├── ApprovalCard/          # Security approval card with diffs and risk badges
│   │   │   └── common/                # Shared cards, tab bars, empty states
│   │   ├── pages/
│   │   │   └── Gateway/               # Cross-channel API message ledger
│   │   └── context/                   # React Context (Chat, Health, Theme)
│   ├── package.json
│   └── vite.config.js                 # Vite proxy configuration to backend (:8000)
│
├── memory-store/                      # Persistent storage directory
│   ├── state.db                       # SQLite database (episodic, vector, semantic FTS5)
│   ├── memory/
│   │   └── MEMORY.md                  # Auto-generated human-readable semantic facts
│   └── skills/
│       └── *.SKILL.md                 # Procedural skill playbooks
│
├── GUARDRAILS.md                      # Authoritative guardrail policy & tool tiers
├── README.md                          # Repository documentation
└── .env.example                       # Environment configuration template
```

---

## Quick Start

### 1. Environment Configuration

Copy `.env.example` to `.env` in the `Poseidon` root directory and set your API key:

```bash
cd Poseidon
cp .env.example .env
```

Key variables in `.env`:
- `OPENROUTER_API_KEY`: Your OpenRouter or OpenAI-compatible API key.
- `POSEIDON_MODEL`: Default model (e.g. `google/gemma-4-31b-it:free` or `anthropic/claude-3.5-sonnet`).
- `POSEIDON_BASE_URL`: API gateway URL (default: `https://openrouter.ai/api/v1`).
- `POSEIDON_CONSOLIDATION_THRESHOLD`: Number of new chats before triggering consolidation (default: `30`).

### 2. Backend Setup & Run

```bash
# Create and activate Python virtual environment
python -m venv venv
venv\Scripts\activate      # Windows
# source venv/bin/activate # Linux / macOS

# Install backend dependencies
cd backend
pip install -r requirements.txt

# Start the FastAPI server
python -m app.main
```

The backend server starts at `http://127.0.0.1:8000`.

### 3. Frontend Setup & Run (Development Mode)

In a separate terminal:

```bash
cd Poseidon/frontend
npm install
npm run dev
```

Open `http://localhost:5173` in your browser. Vite automatically proxies API requests to `http://localhost:8000`.

### 4. Production Single-Process Mode

To serve both frontend and backend from the single FastAPI process:

```bash
cd Poseidon/frontend
npm run build

cd ../backend
python -m app.main
```

FastAPI will serve the built UI assets directly at `http://127.0.0.1:8000/`.

---

## Verification & Testing Examples

### Send a Chat Message

```bash
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"text": "Hello Poseidon! Remember that I prefer dark mode and work in Python."}'
```

### Inspect Semantic Facts

```bash
curl http://localhost:8000/memory/semantic
```

### Inspect Episodic Log

```bash
curl http://localhost:8000/memory/episodic
```

### Trigger On-Demand Memory Consolidation

```bash
curl -X POST http://localhost:8000/memory/consolidate \
  -H "Content-Type: application/json" \
  -d '{"force": true}'
```

### Inspect Tool Security & Diff Analysis

```bash
curl -X POST http://localhost:8000/security/inspect-tool \
  -H "Content-Type: application/json" \
  -d '{
    "tool_name": "crm_write",
    "arguments": {
      "action": "update_record",
      "target_url": "https://suspicious-listener.top/hook"
    },
    "is_tainted": true,
    "original_values": {
      "action": "read_record",
      "target_url": "https://internal.company.corp/api"
    }
  }'
```

---

## Design Principles & Non-Negotiable Rules

1. **Memory Survives Restarts:** Procedural, Semantic, and Episodic stores persist to disk in `memory-store/`. Ephemeral Working Memory is reconstructed per run.
2. **Deterministic Semantic Recall:** Semantic facts use SQLite FTS5 BM25 keyword matching rather than embeddings, keeping recall fast, local, and cheap.
3. **No Unbounded Execution:** Guardrails enforce iteration and tool call limits on every run.
4. **No Terminal Tool in v1:** As mandated by the architecture specification, host terminal / shell execution is intentionally excluded from the registered tool allowlist.
5. **Channel-Agnostic Core:** Gateway adapters normalize all traffic into `InboundEvent`. The orchestration and memory layers never import channel-specific libraries.
