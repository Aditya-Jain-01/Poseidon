"""Redirect stores before application imports and enforce owner-data invariance."""
import hashlib
import os
from pathlib import Path
import tempfile

import pytest

PROJECT = Path(__file__).resolve().parents[2]
REAL_STORE = PROJECT / 'memory-store'


def store_hashes():
    return {str(p.relative_to(REAL_STORE)): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in REAL_STORE.rglob('*') if p.is_file()}


BEFORE = store_hashes()
# Windows can retain SQLite/WAL handles briefly after a test.  Cleanup is best
# effort; test success remains governed by the real-store hash assertion below.
_TEST_DIRECTORY = tempfile.TemporaryDirectory(prefix='poseidon-tests-', ignore_cleanup_errors=True)
TEST_ROOT = Path(_TEST_DIRECTORY.name)
os.environ.update(POSEIDON_DB_PATH=str(TEST_ROOT / 'state.db'), AGENTS_DIR=str(TEST_ROOT / 'agents'),
                  LLM_CONFIG_PATH=str(TEST_ROOT / 'llm_config.json'), TELEGRAM_POLLING_ENABLED='false',
                  POSEIDON_API_KEY='test-only-key', POSEIDON_HOST='127.0.0.1',
                  POSEIDON_CONSOLIDATION_THRESHOLD='100000')
os.environ['HF_HUB_OFFLINE'] = '1'
os.environ['TRANSFORMERS_OFFLINE'] = '1'


def pytest_sessionfinish(session, exitstatus):
    changed = store_hashes() != BEFORE
    try:
        _TEST_DIRECTORY.cleanup()
    except PermissionError:
        # A restricted Windows runner can deny chmod during tempfile cleanup.
        # The directory contains only per-run fixture data and is never owner
        # storage; retain the test outcome while the OS reclaims it later.
        pass
    if changed:
        session.exitstatus = 1
        raise RuntimeError('Tests changed the real memory-store')


@pytest.fixture(autouse=True)
def isolated_stores(tmp_path, monkeypatch):
    from app.config import settings
    from app.db.migrations import apply_migrations
    from app.memory.embeddings import embedding_service
    from app.memory.memory_engine import memory_engine, session_store
    from app.memory.semantic_store import semantic_store
    from app.memory.episodic_store import episodic_store
    from app.memory.procedural_store import procedural_store
    from app.soul import soul_store
    from app.llm_providers import llm_provider, DEFAULT_PROVIDERS, DEFAULT_AGENT_OVERRIDES
    db = tmp_path / 'state.db'
    agents = tmp_path / 'agents'
    agents.mkdir()
    # Fixed fixtures rather than the owner's mutable persona directory.
    tool_names = ['crm_read', 'crm_write', 'calendar_read', 'calendar_create', 'notes_reminders_read', 'notes_reminders_create', 'notes_reminders_delete', 'skill_manage_read', 'skill_manage_write']
    for aid in ('poseidon', 'nereus', 'kraken', 'octavious'):
        tools = '\n'.join(f'  - {name}' for name in tool_names)
        (agents / f'{aid}.soul.md').write_text(f'---\ndisplay_name: {aid.capitalize()}\nmodel_preset: cloud_free\nis_prebuilt: true\ntools:\n{tools}\nrouting_signals: []\n---\n# {aid.capitalize()}\n\nTest persona.', encoding='utf-8')
    monkeypatch.setattr(settings, 'poseidon_db_path', db)
    monkeypatch.setattr(settings, 'agents_dir', agents)
    monkeypatch.setattr(settings, 'llm_config_path', tmp_path / 'llm_config.json')
    monkeypatch.setattr(semantic_store, 'db_path', db)
    monkeypatch.setattr(semantic_store, 'memory_md_path', tmp_path / 'memory/MEMORY.md')
    monkeypatch.setattr(episodic_store, 'db_path', db)
    monkeypatch.setattr(procedural_store, 'skills_dir', tmp_path / 'skills')
    procedural_store.reload()
    monkeypatch.setattr(embedding_service, '_model', False)
    monkeypatch.setattr(llm_provider, '_config_path', tmp_path / 'llm_config.json')
    monkeypatch.setattr(llm_provider, '_clients', {})
    monkeypatch.setattr(llm_provider, '_providers', {k: dict(v) for k, v in DEFAULT_PROVIDERS.items()})
    monkeypatch.setattr(llm_provider, '_agent_overrides', {k: dict(v) for k, v in DEFAULT_AGENT_OVERRIDES.items()})
    soul_store.reload()
    session_store.clear()
    apply_migrations(db)
    from langgraph.checkpoint.memory import InMemorySaver
    from app.orchestration.graph import HarnessRuntime, HarnessServices, set_runtime
    from app.orchestration.approval_store import ApprovalStore
    set_runtime(HarnessRuntime(InMemorySaver(), HarnessServices(approvals=ApprovalStore(db))))
    yield
    set_runtime(None)
    session_store.clear()
