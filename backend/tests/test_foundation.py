import sqlite3
import pytest
from pydantic import ValidationError


def test_models_roundtrip_multiple_calls_and_ids():
    from app.models import Message, ToolCall
    from app.orchestration.langchain_bridge import from_langchain, to_langchain
    messages = [Message(role='assistant', id='assistant-id', tool_calls=[ToolCall(id='c1', name='calendar_read'), ToolCall(id='c2', name='crm_read')]),
                Message(role='tool', content='{}', tool_call_id='c2', name='crm_read', id='result-id')]
    for message in messages:
        assert from_langchain(to_langchain(message)) == message


def test_trusted_fields_and_empty_identifiers_rejected():
    from app.models import ActorContext, ConversationKey, ToolCall
    with pytest.raises(ValidationError):
        ActorContext(owner_id=' ')
    with pytest.raises(ValidationError):
        ConversationKey(owner_id='owner', channel='made-up', channel_account_id='web', thread_id='x')
    with pytest.raises(ValidationError):
        ToolCall(id='c', name='tool', arguments={'_operator_approved': True})


def test_migrations_repeat_and_reject_newer_schema(tmp_path):
    from app.db.migrations import apply_migrations
    from app.db.connection import connection
    db = tmp_path / 'migration.db'
    schemas = []
    for _ in range(3):
        apply_migrations(db)
        with connection(db) as conn:
            schemas.append(list(conn.execute('SELECT sql FROM sqlite_master ORDER BY name')))
            assert conn.execute('PRAGMA foreign_keys').fetchone()[0] == 1
            assert conn.execute('PRAGMA busy_timeout').fetchone()[0] == 5000
    assert schemas[0] == schemas[1] == schemas[2]
    with connection(db) as conn:
        conn.execute("INSERT INTO schema_migrations(version,checksum) VALUES (999,'future')")
        conn.commit()
    with pytest.raises(RuntimeError, match='newer'):
        apply_migrations(db)


def test_store_constructors_do_not_create_data(tmp_path):
    from app.memory.semantic_store import SemanticStore
    from app.memory.episodic_store import EpisodicStore
    db = tmp_path / 'not-created/state.db'
    SemanticStore(db)
    EpisodicStore(db)
    assert not db.parent.exists()


def test_runtime_reports_real_sqlite_capabilities():
    from app.startup_checks import check_runtime
    capabilities = check_runtime()
    assert capabilities['fts5'] and capabilities['json'] and capabilities['wal']
    assert capabilities['vector_mode'] in {'sqlite-vec', 'python-cosine'}
