# Poseidon — Persistent-Memory Agent

A channel-agnostic personal agent with persistent memory, built incrementally.

## Quick Start

### 1. Set up environment

```bash
cd poseidon-agent
cp .env.example .env
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

### 5. Check health

```bash
curl http://localhost:8000/health
```

## Current Status

**Sprint 1** — one channel (Web/CLI), one agent, Working Memory only. No persistence, no tools.

See [EXPLAINER.md](EXPLAINER.md) for a detailed walkthrough of how the system works.

See [GUARDRAILS.md](GUARDRAILS.md) for the guardrail policy (source of truth).
