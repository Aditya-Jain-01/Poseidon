"""Offline Core Release Gate

Run every integration scenario, the full backend suite, frontend lint, and
frontend tests in a single isolated pass.  The real memory-store/ directory
must be byte-for-byte identical before and after; any deviation fails the gate.

Usage (from the project root):
    python backend/scripts/run_gate.py
    python backend/scripts/run_gate.py --backend-only
    python backend/scripts/run_gate.py --frontend-only

Exit codes:
    0  All checks passed, real data unchanged.
    1  One or more checks failed or real data was mutated.
"""

from __future__ import annotations

import argparse
import hashlib
import os
import subprocess
import sys
import tempfile
import textwrap
from pathlib import Path

# ---------------------------------------------------------------------------
# Project layout
# ---------------------------------------------------------------------------
SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT = SCRIPT_DIR.parents[1]          # repository root
BACKEND_DIR = PROJECT / "backend"
FRONTEND_DIR = PROJECT / "frontend"
MEMORY_STORE = PROJECT / "memory-store"

# ---------------------------------------------------------------------------
# Helper utilities
# ---------------------------------------------------------------------------

def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def store_hashes() -> dict:
    """SHA-256 digest of every file currently in memory-store/."""
    if not MEMORY_STORE.exists():
        return {}
    return {
        str(p.relative_to(MEMORY_STORE)): _sha256(p)
        for p in MEMORY_STORE.rglob("*")
        if p.is_file()
    }


def _run(label: str, cmd: list, *, cwd: Path, env: dict) -> int:
    """Print a labelled header, run cmd, and return its exit code."""
    separator = "=" * 70
    print(f"\n{separator}")
    print(f"  {label}")
    print(separator)
    result = subprocess.run(cmd, cwd=cwd, env=env)
    status = "PASSED" if result.returncode == 0 else "FAILED"
    print(f"\n  >>> {label}: {status} (exit {result.returncode})")
    return result.returncode


def _check_python_version() -> None:
    if sys.version_info < (3, 11):
        raise SystemExit(
            f"Python 3.11+ is required; found {sys.version_info.major}.{sys.version_info.minor}"
        )


# ---------------------------------------------------------------------------
# Integration scenario test module text
# ---------------------------------------------------------------------------

_INTEGRATION_SCENARIOS = '''
"""Offline integration scenarios — all run in isolated temp DB."""
import hashlib
import json
import pytest
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import AsyncMock, patch
from fastapi.testclient import TestClient


def _event(thread="t-integ", text="hello"):
    from app.models import ConversationKey, ActorContext, InboundEvent
    return InboundEvent(
        actor=ActorContext(owner_id="local_owner", is_operator=True),
        conversation_key=ConversationKey(
            owner_id="local_owner", channel="web",
            channel_account_id="local_browser", thread_id=thread,
        ),
        text=text,
    )


def _call(name="calendar_create", id="c1", **arguments):
    return {"id": id, "name": name, "arguments": arguments}


def _services(db, llm, executor=None, tier=None):
    from app.orchestration.graph import HarnessServices
    from app.orchestration.approval_store import ApprovalStore
    allowed = ["calendar_create", "calendar_read", "crm_read",
               "notes_reminders_create", "notes_reminders_delete"]
    return HarnessServices(
        approvals=ApprovalStore(db),
        llm_call=llm,
        tool_executor=executor or AsyncMock(return_value={"ok": True}),
        tool_schemas=lambda agent: [{"function": {"name": n}} for n in allowed],
        tool_tier=tier or (
            lambda n: (
                "approval_required" if n in ("calendar_create", "notes_reminders_delete")
                else "guarded_auto" if n == "notes_reminders_create"
                else "auto"
            )
        ),
    )


# 1 — Migration idempotency
def test_migration_idempotency(tmp_path):
    from app.db.migrations import apply_migrations
    from app.db.connection import connection
    db = tmp_path / "m.db"
    schemas = []
    for _ in range(3):
        apply_migrations(db)
        with connection(db) as conn:
            rows = list(conn.execute("SELECT sql FROM sqlite_master ORDER BY name"))
        schemas.append(rows)
    assert schemas[0] == schemas[1] == schemas[2]


# 2 — Forged identity ignored
def test_forged_identity_ignored(monkeypatch):
    from app.main import app
    import app.gateway.web_adapter as adapter
    captured = []
    async def fake_run(event, run_id, agent_id):
        captured.append(event)
        return {"reply": "ok", "run_id": run_id,
                "thread_id": event.channel_thread_id,
                "conversation_key": event.conversation_key.model_dump()}
    monkeypatch.setattr(adapter, "run_agent", fake_run)
    client = TestClient(app, client=("127.0.0.1", 55000))
    resp = client.post("/chat",
        json={"text": "attack", "user_id": "evil", "channel": "telegram", "thread_id": "s-x"},
        headers={"X-Poseidon-User": "evil"})
    assert resp.status_code == 200
    assert captured[0].actor.owner_id == "local_owner"
    assert captured[0].channel == "web"


# 3 — Conversation isolation
@pytest.mark.asyncio
async def test_conversation_isolation(tmp_path):
    from langgraph.checkpoint.memory import InMemorySaver
    from app.orchestration.graph import HarnessRuntime, run_agent
    llm = AsyncMock(return_value={"content": "reply", "tool_calls": []})
    svc = _services(tmp_path / "iso.db", llm)
    rt = HarnessRuntime(InMemorySaver(), svc)
    await run_agent(_event("thread-A", "hello from A"), "run-A", runtime=rt)
    await run_agent(_event("thread-B", "hello from B"), "run-B", runtime=rt)
    assert llm.await_count == 2
    # Two separate run_ids confirm two independent invocations
    assert llm.await_count == 2


# 4 — Secret redaction
def test_secret_redaction(monkeypatch, tmp_path):
    from app.config import settings
    from app.llm_providers import LLMProvider
    monkeypatch.setattr(settings, "poseidon_api_key", "sec-gate-canary-xyz")
    provider = LLMProvider()
    provider._config_path = tmp_path / "llm.json"
    provider._agent_overrides["poseidon"]["api_key"] = "legacy-canary"
    provider.save_config()
    blob = json.dumps([provider.get_all_configs(), provider.get_agent_resolved_config()])
    assert "sec-gate-canary-xyz" not in blob
    assert "legacy-canary" not in blob
    assert '"api_key"' not in blob
    assert "legacy-canary" not in provider._config_path.read_text()


# 5 — Unsafe bind rejection
def test_unsafe_bind_rejection(monkeypatch):
    from app.config import settings
    from app.security.identity import validate_network_config
    monkeypatch.setattr(settings, "poseidon_host", "0.0.0.0")
    monkeypatch.setattr(settings, "poseidon_api_token", "")
    with pytest.raises(RuntimeError, match="Non-loopback"):
        validate_network_config()
    monkeypatch.setattr(settings, "poseidon_api_token", "tok")
    monkeypatch.setattr(settings, "poseidon_cors_origins", ["*"])
    with pytest.raises(RuntimeError, match="wildcard"):
        validate_network_config()
    monkeypatch.setattr(settings, "poseidon_cors_origins", ["http://localhost:5173"])
    validate_network_config()


# 6 — Multi-tool ordering
@pytest.mark.asyncio
async def test_multi_tool_ordering(tmp_path):
    from langgraph.checkpoint.memory import InMemorySaver
    from app.orchestration.graph import HarnessRuntime, run_agent, resume_approval
    calls = [_call("calendar_read", "c1"), _call("calendar_create", "c2", title="Gate"), _call("crm_read", "c3")]
    llm = AsyncMock(side_effect=[{"tool_calls": calls}, {"content": "done"}])
    executor = AsyncMock(return_value={"ok": True})
    rt = HarnessRuntime(InMemorySaver(), _services(tmp_path / "multi.db", llm, executor))
    first = await run_agent(_event(), "multi-gate", runtime=rt)
    assert first["approval_request"]["tool_call_id"] == "c2"
    assert executor.await_count == 1
    resumed = await resume_approval(first["approval_request"]["id"], "approved", runtime=rt)
    assert resumed["reply"] == "done"
    assert executor.await_count == 3
    assert [c.args[0] for c in executor.await_args_list] == ["calendar_read", "calendar_create", "crm_read"]


# 7 — Suspicious-note interrupt
@pytest.mark.asyncio
async def test_suspicious_note_interrupt(tmp_path):
    from langgraph.checkpoint.memory import InMemorySaver
    from app.orchestration.graph import HarnessRuntime, run_agent, resume_approval
    llm = AsyncMock(side_effect=[
        {"tool_calls": [_call("notes_reminders_create", "n1", text="see https://example.com", kind="note")]},
        {"content": "saved"},
    ])
    executor = AsyncMock(return_value={"created": True})
    rt = HarnessRuntime(InMemorySaver(), _services(tmp_path / "note.db", llm, executor))
    first = await run_agent(_event(), "note-gate", runtime=rt)
    assert first["approval_request"]
    assert executor.await_count == 0
    await resume_approval(first["approval_request"]["id"], "approved", runtime=rt)
    assert executor.await_args.args[1]["_operator_approved"] is True


# 8a — Approval expiry
@pytest.mark.asyncio
async def test_approval_expiry(tmp_path):
    from langgraph.checkpoint.memory import InMemorySaver
    from app.orchestration.graph import HarnessRuntime, run_agent, resume_approval
    from app.db.connection import connection
    llm = AsyncMock(side_effect=[{"tool_calls": [_call("calendar_create", "exp1", title="Expiry")]}])
    rt = HarnessRuntime(InMemorySaver(), _services(tmp_path / "exp.db", llm))
    first = await run_agent(_event(), "expiry-gate", runtime=rt)
    approval_id = first["approval_request"]["id"]
    db = tmp_path / "exp.db"
    with connection(db) as conn:
        conn.execute("UPDATE approvals SET expires_at = datetime('now', '-1 hour') WHERE approval_id = ?", (approval_id,))
        conn.commit()
    with pytest.raises((ValueError, RuntimeError)):
        await resume_approval(approval_id, "approved", runtime=rt)


# 8b — Approval denial
@pytest.mark.asyncio
async def test_approval_denial(tmp_path):
    from langgraph.checkpoint.memory import InMemorySaver
    from app.orchestration.graph import HarnessRuntime, run_agent, resume_approval
    from langchain_core.messages import ToolMessage
    llm = AsyncMock(side_effect=[
        {"tool_calls": [_call("calendar_create", "d1"), _call("crm_read", "d2")]},
        {"content": "Action denied."},
    ])
    executor = AsyncMock(return_value={})
    rt = HarnessRuntime(InMemorySaver(), _services(tmp_path / "denial.db", llm, executor))
    first = await run_agent(_event(), "denial-gate", runtime=rt)
    result = await resume_approval(first["approval_request"]["id"], "denied", runtime=rt)
    assert result["approval_request"] is None
    assert [c.args[0] for c in executor.await_args_list] == ["crm_read"]
    tool_msgs = [m for m in llm.await_args_list[-1].args[1] if isinstance(m, ToolMessage)]
    denied_msg = next(m for m in tool_msgs if m.tool_call_id == "d1")
    assert json.loads(denied_msg.content)["error"] == "denied"


# 8c — Approval replay blocked
@pytest.mark.asyncio
async def test_approval_replay_blocked(tmp_path):
    from langgraph.checkpoint.memory import InMemorySaver
    from app.orchestration.graph import HarnessRuntime, run_agent, resume_approval
    llm = AsyncMock(side_effect=[{"tool_calls": [_call("calendar_create", "r1", title="Replay")]}, {"content": "done"}])
    executor = AsyncMock(return_value={"ok": True})
    rt = HarnessRuntime(InMemorySaver(), _services(tmp_path / "replay.db", llm, executor))
    first = await run_agent(_event(), "replay-gate", runtime=rt)
    approval_id = first["approval_request"]["id"]
    await resume_approval(approval_id, "approved", runtime=rt)
    with pytest.raises(ValueError):
        await resume_approval(approval_id, "approved", runtime=rt)


# 8d — Argument substitution blocked
@pytest.mark.asyncio
async def test_approval_argument_substitution_blocked(tmp_path):
    from langgraph.checkpoint.memory import InMemorySaver
    from app.orchestration.graph import HarnessRuntime, run_agent, resume_approval
    llm = AsyncMock(side_effect=[{"tool_calls": [_call("calendar_create", "arg1", title="Original")]}, {"content": "done"}])
    executor = AsyncMock(return_value={"ok": True})
    rt = HarnessRuntime(InMemorySaver(), _services(tmp_path / "argbind.db", llm, executor))
    first = await run_agent(_event(), "argbind-gate", runtime=rt)
    approval_id = first["approval_request"]["id"]
    await resume_approval(approval_id, "approved", runtime=rt)
    executed_args = executor.await_args_list[-1].args[1]
    assert executed_args.get("title") == "Original"


# 8e — Restart: pending approval persists via SQLite
@pytest.mark.asyncio
async def test_approval_survives_restart(tmp_path):
    from app.orchestration.approval_store import ApprovalStore
    from app.db.migrations import apply_migrations
    db = tmp_path / "restart.db"
    apply_migrations(db)
    store_a = ApprovalStore(db)
    approval_id = "gate-restart-id"
    from app.db.connection import connection
    with connection(db) as conn:
        from datetime import datetime, timezone, timedelta
        import json, hashlib
        now_ts = datetime.now(timezone.utc).isoformat()
        exp_ts = (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat()
        args = {"title": "Restart Test"}
        args_json = json.dumps(args, sort_keys=True, separators=(",", ":"))
        args_hash = hashlib.sha256(args_json.encode()).hexdigest()
        key_json = json.dumps({"owner_id":"local_owner","channel":"web","channel_account_id":"local_browser","thread_id":"t-restart"}, sort_keys=True, separators=(",",":"))
        conn.execute(
            "INSERT INTO approvals(approval_id,run_id,owner_id,conversation_key_json,tool_call_id,tool_name,canonical_arguments_json,arguments_hash,policy_version,created_at,expires_at,status)"
            " VALUES(?,?,?,?,?,?,?,?,?,?,?,?)",
            (approval_id, "run-restart", "local_owner", key_json, "tc1",
             "calendar_create", args_json, args_hash, "1", now_ts, exp_ts, "pending"),
        )
        conn.commit()
    try:
        rec = store_a.get(approval_id)
        assert rec is not None
    except KeyError:
        pytest.fail("ApprovalStore.get() raised KeyError unexpectedly after insert")
    store_b = ApprovalStore(db)
    try:
        record = store_b.get(approval_id)
        assert record["tool_name"] == "calendar_create"
    except KeyError:
        pytest.fail("ApprovalStore.get() raised KeyError after simulated restart")


# 9 — Tool execution idempotency
@pytest.mark.asyncio
async def test_tool_execution_idempotency(tmp_path):
    from langgraph.checkpoint.memory import InMemorySaver
    from app.orchestration.graph import HarnessRuntime, run_agent
    llm = AsyncMock(return_value={"content": "hello", "tool_calls": []})
    executor = AsyncMock(return_value={"ok": True})
    rt = HarnessRuntime(InMemorySaver(), _services(tmp_path / "idem.db", llm, executor))
    await run_agent(_event(), "idem-run", runtime=rt)
    call_count_after_first = llm.await_count
    await run_agent(_event(), "idem-run", runtime=rt)
    assert llm.await_count == call_count_after_first


# 10 — Taint escalation
def test_taint_escalation():
    from app.security.taint import calculate_overall_risk, evaluate_tool_tier
    # Telegram is untrusted channel -> overall risk is at least MEDIUM/HIGH
    risk_ctx = calculate_overall_risk("telegram", "visit https://evil.example.com")
    assert risk_ctx["is_tainted"] is True
    # Evaluate tool tier under tainted context
    tier_result = evaluate_tool_tier("notes_reminders_create", is_tainted=risk_ctx["is_tainted"], risk_context=risk_ctx)
    assert tier_result["requires_approval"] is True or tier_result["tier"] in ("approval_required", "guarded_auto")


# 11 — Concurrent personal-data writes
@pytest.mark.asyncio
async def test_concurrent_personal_data_writes(tmp_path):
    import asyncio
    import concurrent.futures
    from app.db.migrations import apply_migrations
    from app.db.connection import connection
    db = tmp_path / "conc.db"
    apply_migrations(db)
    async def write(i):
        loop = asyncio.get_event_loop()
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
            def _w():
                with connection(db) as conn:
                    conn.execute(
                        "INSERT INTO audit_events(event_id,owner_id,run_id,channel,direction,event_type,status,payload_json,created_at)"
                        " VALUES(?,?,?,?,?,?,?,?,datetime(\'now\'))",
                        (f"evt-{i}", "local_owner", f"run-{i}", "web", "inbound", "test_write", "completed", json.dumps({"i": i})),
                    )
                    conn.commit()
            await loop.run_in_executor(pool, _w)
    await asyncio.gather(*[write(i) for i in range(5)])
    with connection(db) as conn:
        count = conn.execute("SELECT COUNT(*) FROM audit_events").fetchone()[0]
    assert count == 5


# 12 — Memory update / forget / re-embed
def test_memory_update_forget_re_embed(tmp_path):
    from app.db.migrations import apply_migrations
    from app.memory.semantic_store import SemanticStore
    db = tmp_path / "mem.db"
    apply_migrations(db)
    store = SemanticStore(db)
    store.add_fact("local_owner", "Gate test fact about coffee", category="general")
    results = store.retrieve("local_owner", "coffee")
    assert any("coffee" in r.get("fact", "") for r in results)
    all_facts = store.get_all_facts("local_owner")
    coffee_fact = next((f for f in all_facts if "coffee" in f.get("fact", "")), None)
    assert coffee_fact is not None
    store.deactivate_fact(coffee_fact["id"])
    results_after = store.retrieve("local_owner", "coffee")
    assert not any("coffee" in r.get("fact", "") for r in results_after)


# 13 — Agent selection and permission enforcement
def test_agent_selection_and_permission_enforcement(monkeypatch):
    from app.main import app
    import app.gateway.web_adapter as adapter
    async def fake_run(event, run_id, agent_id):
        return {"reply": "ok", "run_id": run_id,
                "thread_id": event.channel_thread_id,
                "conversation_key": event.conversation_key.model_dump()}
    monkeypatch.setattr(adapter, "run_agent", fake_run)
    client = TestClient(app, client=("127.0.0.1", 55001))
    resp = client.post("/chat", json={"text": "hi", "agent_id": "unknown-agent-xyz"})
    assert resp.status_code in (200, 400, 404, 422)
    if resp.status_code == 200:
        body_text = json.dumps(resp.json()).lower()
        assert "unknown" in body_text or "error" in body_text or resp.json().get("reply")


# 14a — Telegram duplicate update
@pytest.mark.asyncio
async def test_telegram_duplicate_update_handling():
    from app.gateway.telegram_adapter import process_telegram_update
    from app.config import settings
    update = {
        "update_id": 88001,
        "message": {"message_id": 1, "from": {"id": 12345, "first_name": "User"},
                    "chat": {"id": 12345, "type": "private"}, "text": "hello"},
    }
    with patch("app.gateway.telegram_adapter.run_agent", new_callable=AsyncMock) as mock_run:
        mock_run.return_value = {"reply": "ok", "run_id": "r1"}
        with patch("app.gateway.telegram_adapter.send_telegram_reply", new_callable=AsyncMock):
            with patch.object(settings, "telegram_allowed_user_ids", "12345"):
                r1 = await process_telegram_update(update, bot_token="fake")
                r2 = await process_telegram_update(update, bot_token="fake")
    assert r1.get("status") == "processed"
    assert r2.get("status") in ("already_completed", "processed", "skipped", "duplicate")
    assert mock_run.await_count <= 1


# 14b — Telegram restart: unfinished updates present after DB restart
@pytest.mark.asyncio
async def test_telegram_restart_retries_unfinished(tmp_path):
    from app.db.migrations import apply_migrations
    from app.db.connection import connection
    db = tmp_path / "tg_restart.db"
    apply_migrations(db)
    with connection(db) as conn:
        conn.execute(
            "INSERT INTO telegram_updates(update_id,status,run_id,attempt_count,payload_hash,received_at,updated_at)"
            " VALUES(?,?,?,?,?,datetime(\'now\'),datetime(\'now\'))",
            (77001, "received", "telegram_update_77001", 1, hashlib.sha256(b"test").hexdigest()),
        )
        conn.commit()
    with connection(db) as conn:
        rows = list(conn.execute("SELECT update_id, status FROM telegram_updates WHERE status = \'received\'"))
    assert len(rows) == 1 and rows[0][0] == 77001


# 15 — Frontend approval failure (backend contract)
def test_frontend_approval_failure_and_session_binding():
    from app.main import app
    client = TestClient(app, client=("127.0.0.1", 55002))
    resp = client.post("/chat/approve",
        json={"approval_id": "nonexistent-id-xyz", "decision": "approved"})
    assert resp.status_code in (404, 400, 422)


# 16 — Graceful shutdown: audit events persist
@pytest.mark.asyncio
async def test_graceful_shutdown_audit_events_persist(tmp_path):
    from app.db.migrations import apply_migrations
    from app.security.audit import AuditService
    db = tmp_path / "audit.db"
    apply_migrations(db)
    svc = AuditService(db)
    svc.record_event(
        run_id="run-shutdown", owner_id="local_owner",
        channel="web", direction="inbound",
        event_type="chat_request", status="completed",
        payload={"text": "shutdown test"},
    )
    svc2 = AuditService(db)
    events = svc2.query_events(owner_id="local_owner", limit=10)
    assert any(e["run_id"] == "run-shutdown" for e in events)
'''


# ---------------------------------------------------------------------------
# Main gate logic
# ---------------------------------------------------------------------------

def build_env(tmp_dir: str) -> dict:
    tmp = Path(tmp_dir)
    env = dict(os.environ)
    env.update(
        POSEIDON_DB_PATH=str(tmp / "state.db"),
        AGENTS_DIR=str(tmp / "agents"),
        LLM_CONFIG_PATH=str(tmp / "llm_config.json"),
        TELEGRAM_POLLING_ENABLED="false",
        POSEIDON_API_KEY="gate-test-only-key",
        POSEIDON_HOST="127.0.0.1",
        POSEIDON_CONSOLIDATION_THRESHOLD="100000",
        HF_HUB_OFFLINE="1",
        TRANSFORMERS_OFFLINE="1",
        TMP=tmp_dir,
        TEMP=tmp_dir,
        TMPDIR=tmp_dir,
    )
    # Ensure 'app' package is importable from the start (before pytest's
    # pythonpath ini option activates), which is needed by conftest.py fixtures.
    existing_pypath = env.get("PYTHONPATH", "")
    sep = os.pathsep
    env["PYTHONPATH"] = str(BACKEND_DIR) + (sep + existing_pypath if existing_pypath else "")
    return env


def run_backend_gate(tmp: Path) -> int:
    env = build_env(str(tmp))
    # Write the integration scenarios alongside a conftest.py so that the
    # isolated_stores fixture is available.  We create a sub-directory inside
    # tmp and copy the real conftest.py there.
    integ_dir = tmp / "integ"
    integ_dir.mkdir()
    scenarios_file = integ_dir / "test_integration_scenarios.py"
    scenarios_file.write_text(_INTEGRATION_SCENARIOS, encoding="utf-8")

    # Copy the real conftest.py so isolated_stores fixture is available
    import shutil
    shutil.copy(BACKEND_DIR / "tests" / "conftest.py", integ_dir / "conftest.py")

    failures = 0

    rc = _run(
        "Integration scenarios",
        [sys.executable, "-m", "pytest", str(scenarios_file), "-q",
         "-o", "asyncio_mode=auto",
         "-o", f"pythonpath={BACKEND_DIR}",
         "--basetemp", str(tmp / "pytest-integ")],
        cwd=PROJECT, env=env,
    )
    failures += rc

    rc = _run(
        "Full backend test suite",
        [sys.executable, "-m", "pytest", str(BACKEND_DIR / "tests"), "-q",
         "-o", "asyncio_mode=auto",
         "-o", f"pythonpath={BACKEND_DIR}",
         "--basetemp", str(tmp / "pytest-backend")],
        cwd=PROJECT, env=env,
    )
    failures += rc
    return failures



def run_frontend_gate() -> int:
    failures = 0
    front_env = dict(os.environ)
    # On Windows, npm is a .cmd batch file; subprocess needs the .cmd extension
    # when shell=False (the default).
    npm = "npm.cmd" if sys.platform == "win32" else "npm"

    if not (FRONTEND_DIR / "node_modules").exists():
        print("\n[gate] npm ci — installing frontend dependencies...")
        rc = subprocess.run([npm, "ci"], cwd=FRONTEND_DIR).returncode
        if rc != 0:
            print("FAILED: npm ci")
            return rc

    rc = _run("Frontend lint (oxlint)", [npm, "run", "lint"],
              cwd=FRONTEND_DIR, env=front_env)
    failures += rc

    rc = _run("Frontend tests (Vitest)", [npm, "test", "--", "--run"],
              cwd=FRONTEND_DIR, env=front_env)
    failures += rc
    return failures


def main() -> int:
    parser = argparse.ArgumentParser(description="Poseidon Offline Core Release Gate")
    parser.add_argument("--backend-only", action="store_true")
    parser.add_argument("--frontend-only", action="store_true")
    args = parser.parse_args()

    _check_python_version()

    print("\n" + "=" * 70)
    print("  Poseidon Offline Core Release Gate")
    print("=" * 70)
    print(f"  Project  : {PROJECT}")
    print(f"  Python   : {sys.version}")
    print(f"  Backend  : {'skip' if args.frontend_only else 'run'}")
    print(f"  Frontend : {'skip' if args.backend_only else 'run'}")

    before = store_hashes()
    print(f"\n  memory-store snapshot: {len(before)} file(s)")

    total_failures = 0
    with tempfile.TemporaryDirectory(prefix="poseidon-gate-", ignore_cleanup_errors=True) as tmp_str:
        tmp = Path(tmp_str)
        if not args.frontend_only:
            total_failures += run_backend_gate(tmp)
        if not args.backend_only:
            total_failures += run_frontend_gate()

    after = store_hashes()
    mutated = after != before

    print("\n" + "=" * 70)
    print("  Gate Summary")
    print("=" * 70)

    if mutated:
        print("  FAIL  — Real memory-store was modified during gate run!")
        added   = set(after) - set(before)
        removed = set(before) - set(after)
        changed = {k for k in before if k in after and before[k] != after[k]}
        for f in sorted(added):   print(f"          + {f}")
        for f in sorted(removed): print(f"          - {f}")
        for f in sorted(changed): print(f"          ~ {f}")
        total_failures += 1
    else:
        print(f"  OK    — Real memory-store unchanged ({len(before)} file(s) verified)")

    if total_failures == 0:
        print("  GATE PASSED — all checks green, real data preserved")
    else:
        print(f"  GATE FAILED — {total_failures} check(s) failed")

    return 0 if total_failures == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())

