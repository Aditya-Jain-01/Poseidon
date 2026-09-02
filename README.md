# Poseidon — Persistent-Memory Agent Harness

<p align="left">
  <img src="https://img.shields.io/badge/Python-3.10+-3776AB?style=flat-square&logo=python&logoColor=white" alt="Python 3.10+" />
  <img src="https://img.shields.io/badge/FastAPI-0.115+-009688?style=flat-square&logo=fastapi&logoColor=white" alt="FastAPI" />
  <img src="https://img.shields.io/badge/LangGraph-StateGraph-FF6F00?style=flat-square" alt="LangGraph" />
  <img src="https://img.shields.io/badge/Storage-SQLite%20+%20sqlite--vec-003B57?style=flat-square&logo=sqlite&logoColor=white" alt="SQLite & sqlite-vec" />
  <img src="https://img.shields.io/badge/Frontend-React%2019%20+%20Vite-61DAFB?style=flat-square&logo=react&logoColor=black" alt="React 19 + Vite" />
  <img src="https://img.shields.io/badge/License-MIT-blue.svg?style=flat-square" alt="License: MIT" />
</p>

A local-first, channel-agnostic AI agent execution harness featuring a **four-tier persistent memory architecture**, **multi-layered security and guardrail governance**, and an **interactive developer cockpit**.

---

## Table of Contents

- [Overview](#overview)
- [Key Features](#key-features)
- [System Architecture](#system-architecture)
- [Memory Subsystems](#memory-subsystems)
- [Security & Governance Framework](#security--governance-framework)
- [Developer Cockpit UI](#developer-cockpit-ui)
- [API Reference](#api-reference)
- [Repository Structure](#repository-structure)
- [Getting Started](#getting-started)
- [Verification & Example Workflows](#verification--example-workflows)
- [Architectural Principles & Non-Goals](#architectural-principles--non-goals)

---

## Overview

Traditional LLM applications are ephemeral: context is wiped when a session terminates, long-term learning requires expensive fine-tuning, and uncontrolled tool-calling risks severe security vulnerabilities.

**Poseidon** provides a governed, local-first runtime environment (harness) for agentic execution. It isolates agent runs into ephemeral execution states while binding them to a persistent, 4-tier memory hierarchy. It also enforces comprehensive inbound and outbound security barriers—including prompt injection filtering, outbound credential redaction (DLP), and human-in-the-loop tool approval gates.

---

## Key Features

| Capability | Technical Implementation |
|---|---|
| **4-Tier Persistent Memory** | Working memory dynamic context hydration, Episodic memory with `sqlite-vec` dense retrieval, Semantic memory with FTS5 BM25 keyword search, and filesystem-backed `*.SKILL.md` procedural routines. |
| **Background Consolidation** | Periodic $N$-turn consolidation pipeline running a background `SummarizerAgent` to distill raw conversational episodes into durable long-term knowledge. |
| **LangGraph Orchestration** | Typed `AgentState` state machines with reducer-based message accumulation and strict execution bounds (`max_iterations`, `max_tool_calls`). |
| **Outbound DLP Firewall** | Pre-compiled regex scanner redacting API keys (OpenAI, Anthropic, AWS, Google, GitHub), bearer tokens, private keys, and PII prior to client delivery. |
| **Anti-Poisoning Write Gate** | Pre-commit heuristic and semantic filter (`AdversarialReviewer`) rejecting prompt injections, system overrides, and untrusted URLs before memory persistence. |
| **Risk & Parameter Diff Analyzer** | Automated classification of tool execution risk tiers (Low / Medium / High) with structural parameter diffing for human approval workflows. |
| **Channel-Agnostic Gateway** | Decoupled adapter layer normalizing inbound events (`InboundEvent`) with per-channel taint tracking and zero downstream coupling. |
| **Developer Cockpit** | React 19 + Vite dashboard featuring multi-session management, step-by-step turn execution inspection, interactive security gates, and a live CAD topology visualizer. |

---

## System Architecture

```mermaid
flowchart TD
    subgraph Inbound ["1. Gateway Layer"]
        CLI["Web / CLI Adapter"] -->|Normalize| EV["InboundEvent Schema"]
    end

    subgraph Assembly ["2. Context Hydration"]
        EV --> WM["Working Memory Assembler"]
        PROC["Procedural Memory (*.SKILL.md)"] -.->|Playbooks| WM
        SEM["Semantic Memory (FTS5 BM25)"] -.->|Top-k Facts| WM
        EPIS["Episodic Memory (sqlite-vec)"] -.->|KNN + Recency| WM
        SP["System Prompt Template"] -.-> WM
    end

    subgraph Runtime ["3. Governed Execution Loop"]
        WM --> LG["LangGraph Orchestration Engine"]
        LG --> QA["QA Agent Loop"]
        QA -->|Tool Invocation| RISK{"Risk Analyzer Gate"}
        RISK -->|Low Risk| EXEC["Execute Tool"]
        RISK -->|High Risk| HITL["Human Approval Required"]
        EXEC --> QA
        HITL --> QA
    end

    subgraph SecurityOut ["4. Output Governance"]
        QA --> DLP["Outbound DLP Firewall"]
        DLP -->|Sanitized Stream| RES["Client Gateway Response"]
        QA -.->|Raw Turn Logs| EPIS_STORE[("Episodic Store (state.db)")]
    end

    subgraph Consolidation ["5. Background Consolidation"]
        EPIS_STORE -->|Threshold Trigger (N chats)| SUMM["Summarizer Agent"]
        SUMM --> ADV{"Anti-Poisoning Reviewer"}
        ADV -->|Safe Facts| SEM_STORE[("Semantic Store (FTS5 + MEMORY.md)")]
        ADV -->|Safe Skills| PROC_STORE["Procedural Store (memory-store/skills)"]
    end
```

---

## Memory Subsystems

Poseidon separates cognitive storage into four distinct operational tiers:

```
┌─────────────────────────────────────────────────────────────────────────────┐
│ 1. WORKING MEMORY (Ephemeral in-RAM Context)                                 │
│    System Prompt + Active Skills + Semantic Facts + Episodic Turns + Prompt │
└──────────────────────────────────────┬──────────────────────────────────────┘
                                       │
            ┌──────────────────────────┼──────────────────────────┐
            ▼                          ▼                          ▼
┌───────────────────────┐  ┌───────────────────────┐  ┌───────────────────────┐
│ 2. EPISODIC MEMORY    │  │ 3. SEMANTIC MEMORY    │  │ 4. PROCEDURAL MEMORY  │
│ SQLite WAL + sqlite-  │  │ SQLite FTS5 (BM25)    │  │ Filesystem-backed     │
│ vec (384-dim dense)   │  │ + MEMORY.md mirror    │  │ *.SKILL.md playbooks  │
└───────────────────────┘  └───────────────────────┘  └───────────────────────┘
```

### 1. Working Memory (`backend/app/memory/working_memory.py`)
- **Lifecycle:** Ephemeral (per-run), assembled fresh on every message turn.
- **Assembly Pipeline:** Base system prompt $\rightarrow$ active procedural playbooks $\rightarrow$ top-$k$ semantic facts $\rightarrow$ blended episodic history $\rightarrow$ live session chat turns $\rightarrow$ current user prompt.
- **Session Store:** In-memory dictionary holding recent turns for immediate conversational continuity within a running server process.

### 2. Episodic Memory (`backend/app/memory/episodic_store.py`)
- **Storage:** SQLite (`memory-store/state.db`) with Write-Ahead Logging (`PRAGMA journal_mode=WAL;`).
- **Vector Indexing:** `sqlite-vec` extension storing 384-dimensional normalized vector embeddings generated locally by `sentence-transformers` (`all-MiniLM-L6-v2`).
- **Retrieval Engine:** Blends vector KNN semantic similarity (`search_relevant`) and SQL recency (`get_recent`), deduplicating events by ID and sorting chronologically.

### 3. Semantic Memory (`backend/app/memory/semantic_store.py`)
- **Storage:** SQLite table `semantic_facts` mirrored into an FTS5 virtual table (`semantic_fts`) via automated SQL insert/update/delete triggers.
- **Retrieval Engine:** BM25 keyword top-$k$ search—intentionally deterministic, fast, and independent of external embedding models for concise personal facts.
- **Human-Readable Mirror:** Automatically regenerates `memory-store/memory/MEMORY.md` whenever facts are added, modified, or soft-deleted.

### 4. Procedural Memory (`backend/app/memory/procedural_store.py`)
- **Storage:** Plain Markdown files (`*.SKILL.md`) with YAML frontmatter stored in `memory-store/skills/`.
- **Retrieval Engine:** Case-insensitive trigger phrase matching against user messages to inject relevant operational playbooks into Working Memory.

### 5. Consolidation Pipeline (`backend/app/memory/consolidation.py`)
- **Trigger:** Tracks unconsolidated episodic entries and fires automatically upon crossing a configurable threshold $N$ (default: `30` chats).
- **Distillation:** Runs a dedicated `SummarizerAgent` to extract durable facts (*preference*, *profile*, *relationship*, *general*) and operational workflows.
- **Verification:** Passes all candidate items through the `AdversarialReviewer` before database commit, then marks raw episodes as consolidated.

---

## Security & Governance Framework

Poseidon implements defense-in-depth governance across all execution boundaries:

```
 Inbound Input                    Agent Execution                     Outbound Output
 ─────────────                    ───────────────                     ───────────────
 [Taint Tracking] ──▶ [Loop & Tool Caps] ──▶ [Risk Analyzer & Approval] ──▶ [Outbound DLP]
                             │
                             ▼
                 [Anti-Poisoning Write Gate] ──▶ [Memory Commit]
```

1. **Outbound Data Loss Prevention (`backend/app/security/dlp.py`):**
   - Intercepts all generated LLM responses before delivery.
   - Pre-compiled regex engine scans for and redacts credentials (OpenAI, Anthropic, Google, AWS, GitHub), Bearer tokens, private keys, credit cards, and SSNs.
2. **Channel Taint Tracking (`backend/app/security/taint.py`):**
   - Tags incoming events with trust levels (`TRUSTED` for local Web/CLI; `UNTRUSTED` for third-party webhooks).
   - Automatically downgrades automated read tools to require human approval when operating on tainted context.
3. **Anti-Poisoning Reviewer (`backend/app/security/adversarial_filter.py`):**
   - Evaluates memory write candidates against heuristic injection patterns, system prompt overrides, malicious webhook endpoints (`.ru`, `webhook.site`, `ngrok.io`), SQL injection, and destructive shell signatures.
4. **Tool Risk Analysis & Parameter Diffing (`backend/app/security/risk_analyzer.py`):**
   - Analyzes tool parameters, calculates structural before/after diffs, and computes risk ratings (`high`, `medium`, `low`) for human-in-the-loop approval workflows.

> [!NOTE]
> For complete policy details and tool tier classifications, refer to [GUARDRAILS.md](GUARDRAILS.md).

---

## Developer Cockpit UI

The frontend is a lightweight **React 19 + Vite** dashboard utilizing vanilla CSS design tokens:

- **3-Panel Workspace:**
  - **Left Sidebar:** Multi-session management, full-text history search, session rename/delete, Light/Dark theme switching, and gateway navigation.
  - **Center Canvas:** Chat feed with markdown rendering, turn execution telemetry, and subheader tab navigation between **Chat**, **Trajectory** (step-by-step turn inspector), and **Security Gate** (interactive approval cards).
  - **Right Panel:** Collapsible and resizable side panel hosting an interactive SVG **Architecture Topology CAD Map** that dynamically pulses active subsystem nodes during runtime.
- **Gateway & API Ledger (`/gateway`):**
  - Unified cross-channel message ledger displaying transmission direction (`IN`/`OUT`), timestamps, channel badges, content previews, and Run ID tracing.

---

## API Reference

### Gateway & Chat Endpoints

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/chat` | Submit a prompt; returns LLM response, `run_id`, and `approval_request` (if triggered). |
| `GET` | `/health` | Service health status and active LLM model identifier. |
| `POST` | `/security/inspect-tool` | Inspect tool call arguments for security risks, parameter diffs, and warnings. |

### Memory Management Endpoints

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/memory/semantic` | Retrieve active semantic facts (`category`, `query`, and `limit` filters supported). |
| `GET` | `/memory/episodic` | Retrieve episodic log events (`since` ISO timestamp, `query`, and `limit` filters supported). |
| `GET` | `/memory/procedural` | List loaded procedural skills or query matching skills by task trigger keyword. |
| `POST` | `/memory/consolidate` | Manually trigger memory consolidation over unconsolidated episodic events (`force: true`). |
| `GET` | `/memory/status` | Retrieve memory telemetry (fact count, skill count, unconsolidated chat count). |

---

## Repository Structure

```
Poseidon/
├── backend/
│   ├── app/
│   │   ├── main.py                    # FastAPI application & static asset server
│   │   ├── config.py                  # Pydantic Settings configuration
│   │   ├── gateway/
│   │   │   ├── web_adapter.py         # HTTP /chat adapter and InboundEvent normalizer
│   │   │   └── memory_adapter.py      # /memory/* REST endpoints
│   │   ├── orchestration/
│   │   │   ├── graph.py               # LangGraph StateGraph execution pipeline
│   │   │   └── state.py               # AgentState and InboundEvent data schemas
│   │   ├── agents/
│   │   │   ├── qa_agent.py            # Primary conversational agent (OpenRouter / OpenAI SDK)
│   │   │   └── summarizer_agent.py    # Background consolidation & memory distillation agent
│   │   ├── memory/
│   │   │   ├── working_memory.py      # Working Memory assembly & session store
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
│   ├── tests/                         # Pytest test suite
│   └── requirements.txt               # Python backend dependencies
│
├── frontend/                          # React 19 + Vite developer cockpit
│   ├── src/
│   │   ├── App.jsx                    # 3-panel workspace layout & routing
│   │   ├── components/
│   │   │   ├── ChatDock/              # Chat feed, message stream, subheader tabs
│   │   │   ├── LeftSidebar/           # Session management, search, theme toggle
│   │   │   ├── RightPanel/            # Resizable side inspector panel
│   │   │   ├── ArchitectureMap/       # Live SVG topology CAD diagram
│   │   │   ├── TrajectoryView/        # Step-by-step turn execution inspector
│   │   │   └── ApprovalCard/          # Security approval card with diffs and risk badges
│   │   ├── pages/
│   │   │   └── Gateway/               # Cross-channel API message ledger
│   │   └── context/                   # React Context providers (Chat, Health, Theme)
│   ├── package.json
│   └── vite.config.js                 # Vite dev proxy configuration
│
├── memory-store/                      # Persistent storage directory
│   ├── state.db                       # SQLite database (episodic, vector, semantic FTS5)
│   ├── memory/
│   │   └── MEMORY.md                  # Auto-generated human-readable semantic mirror
│   └── skills/
│       └── *.SKILL.md                 # Procedural skill playbooks
│
├── GUARDRAILS.md                      # Security guardrail policy & tool tier specification
├── README.md                          # Repository documentation
└── .env.example                       # Environment configuration template
```

---

## Getting Started

### Prerequisites
- **Python 3.10+**
- **Node.js 18+ & npm** (for frontend development)

### 1. Environment Setup

Copy `.env.example` to `.env` in the `Poseidon/` directory:

```bash
cd Poseidon
cp .env.example .env
```

Configure your environment variables:
```dotenv
OPENROUTER_API_KEY=your_openrouter_api_key_here
POSEIDON_MODEL=google/gemma-4-31b-it:free
POSEIDON_BASE_URL=https://openrouter.ai/api/v1
POSEIDON_CONSOLIDATION_THRESHOLD=30
```

### 2. Backend Execution

```bash
# Create and activate virtual environment
python -m venv venv

# Windows
venv\Scripts\activate
# Linux / macOS
# source venv/bin/activate

# Install dependencies
cd backend
pip install -r requirements.txt

# Start the FastAPI server
python -m app.main
```
The backend will initialize at `http://127.0.0.1:8000`.

### 3. Frontend Execution (Development Mode)

In a separate terminal:

```bash
cd Poseidon/frontend
npm install
npm run dev
```
Open `http://localhost:5173` in your browser. API calls are automatically proxied to `:8000`.

### 4. Single-Process Production Mode

To serve the compiled UI directly through FastAPI:

```bash
cd Poseidon/frontend
npm run build

cd ../backend
python -m app.main
```
FastAPI will host the full application and UI bundle on `http://127.0.0.1:8000/`.

---

## Verification & Example Workflows

### Send a Chat Interaction
```bash
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"text": "Hello Poseidon! Remember that I prefer Python and dark mode."}'
```

### Query Retrieved Semantic Facts
```bash
curl "http://localhost:8000/memory/semantic?query=Python"
```

### Query Episodic Event History
```bash
curl "http://localhost:8000/memory/episodic?limit=5"
```

### Force Background Memory Consolidation
```bash
curl -X POST http://localhost:8000/memory/consolidate \
  -H "Content-Type: application/json" \
  -d '{"force": true}'
```

### Run Tool Risk & Parameter Diff Inspection
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

## Architectural Principles & Non-Goals

1. **Memory Survives Restarts:** All episodic, semantic, and procedural stores persist deterministically to disk in `memory-store/`. Ephemeral Working Memory is reconstructed per run.
2. **Deterministic Semantic Recall:** Semantic facts utilize SQLite FTS5 BM25 keyword matching rather than embeddings, ensuring sub-millisecond, local, zero-cost recall for personal facts.
3. **Bounded Execution:** LangGraph state machines enforce iteration and tool call caps on every cycle to eliminate runaway agentic loops.
4. **No Host Terminal Access in v1:** Raw shell / terminal execution tools are strictly excluded from the registered tool allowlist to safeguard host operating system integrity.
5. **Channel-Agnostic Core:** Gateway adapters normalize all inbound traffic into `InboundEvent` payloads. The orchestration and memory subsystems have zero coupling to specific communication channels.

---

<p align="center">
  <sub>Built with LangGraph, FastAPI, and SQLite. Designed for local-first, privacy-focused persistent AI agent workflows.</sub>
</p>
