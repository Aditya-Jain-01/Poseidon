# Poseidon — Persistent-Memory Agent

A channel-agnostic personal agent with persistent memory, built incrementally.

## Quick Start

### 1. Set up environment

```bash
cd Poseidon
# Edit .env — at minimum set OPENROUTER_API_KEY
```

### 2. Install dependencies

```bash
cd backend
pip install -r requirements.txt
```

### 3. Run the server

```bash
cd backend
python -m app.main
```

The server starts at `http://127.0.0.1:8000`.

### 4. Send a message

```bash
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"text": "Hello, what can you do?"}'
```

### 5. Check health & memory

```bash
# Health
curl http://localhost:8000/health

# Semantic facts
curl http://localhost:8000/memory/semantic

# Episodic history
curl http://localhost:8000/memory/episodic

# Trigger consolidation
curl -X POST http://localhost:8000/memory/consolidate
```

---

## Architecture & Current Status

### **Sprint 2: Persistent Memory Layer** (Current)
- **Episodic Store** (`memory-store/state.db`): SQLite chronological event log with FTS5 keyword indexing.
- **Semantic Store** (`memory-store/memory/MEMORY.md` + FTS5): Persistent durable facts with BM25 retrieval and human-readable Markdown mirror.
- **Procedural Store** (`memory-store/skills/*.SKILL.md`): Task-matched skill playbooks loaded into Working Memory.
- **Working Memory**: Dynamic assembly combining base system prompt, procedural playbooks, top-k semantic facts, recency/relevance episodic history, and active session context.
- **Summarizer Agent & Consolidation**: Automatic N-new-chats background distillation pipeline extracting durable facts and skills from unconsolidated episodic logs.
- **Memory API**: REST endpoints `/memory/semantic`, `/memory/episodic`, `/memory/procedural`, `/memory/consolidate`, and `/memory/status`.

---

See [GUARDRAILS.md](GUARDRAILS.md) for the guardrail policy (source of truth).
