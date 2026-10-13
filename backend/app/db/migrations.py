"""Ordered transactional migrations. Constructors never own schema DDL."""
import hashlib
import json
import sqlite3
from app.db.connection import connection

MEMORY_SQL = (
    """CREATE TABLE IF NOT EXISTS semantic_facts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id TEXT NOT NULL,
                    fact TEXT NOT NULL,
                    category TEXT NOT NULL DEFAULT 'general',
                    source_run_id TEXT,
                    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    active INTEGER NOT NULL DEFAULT 1
                );""",
    """CREATE INDEX IF NOT EXISTS idx_semantic_user_category
                ON semantic_facts(user_id, category, active);""",
    """CREATE VIRTUAL TABLE IF NOT EXISTS semantic_fts USING fts5(
                    fact,
                    category UNINDEXED,
                    user_id UNINDEXED,
                    fact_id UNINDEXED,
                    tokenize='unicode61'
                );""",
    """CREATE TRIGGER IF NOT EXISTS trg_semantic_after_insert
                AFTER INSERT ON semantic_facts
                BEGIN
                    INSERT INTO semantic_fts(rowid, fact, category, user_id, fact_id)
                    VALUES (new.id, new.fact, new.category, new.user_id, new.id);
                END;""",
    """CREATE TRIGGER IF NOT EXISTS trg_semantic_after_delete
                AFTER DELETE ON semantic_facts
                BEGIN
                    DELETE FROM semantic_fts WHERE rowid = old.id;
                END;""",
    """CREATE TRIGGER IF NOT EXISTS trg_semantic_after_update
                AFTER UPDATE ON semantic_facts
                BEGIN
                    DELETE FROM semantic_fts WHERE rowid = old.id;
                    INSERT INTO semantic_fts(rowid, fact, category, user_id, fact_id)
                    VALUES (new.id, new.fact, new.category, new.user_id, new.id);
                END;""",
    """CREATE TABLE IF NOT EXISTS episodic_events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id TEXT NOT NULL,
                    channel TEXT NOT NULL DEFAULT 'web',
                    run_id TEXT,
                    role TEXT NOT NULL,
                    content TEXT NOT NULL,
                    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    metadata TEXT,
                    consolidated INTEGER NOT NULL DEFAULT 0
                );""",
    """CREATE INDEX IF NOT EXISTS idx_episodic_user_created 
                ON episodic_events(user_id, created_at DESC);""",
    """CREATE INDEX IF NOT EXISTS idx_episodic_consolidated 
                ON episodic_events(consolidated);""",
)

RUNTIME_SQL = (
    "CREATE TABLE approvals (approval_id TEXT PRIMARY KEY, run_id TEXT NOT NULL, owner_id TEXT NOT NULL, conversation_key_json TEXT NOT NULL, tool_call_id TEXT NOT NULL, tool_name TEXT NOT NULL, canonical_arguments_json TEXT NOT NULL, arguments_hash TEXT NOT NULL, policy_version TEXT NOT NULL, status TEXT NOT NULL CHECK(status IN ('pending','approved','denied','expired','consumed')), created_at TEXT NOT NULL, expires_at TEXT NOT NULL, resolved_at TEXT, consumed_at TEXT, UNIQUE(run_id,tool_call_id))",
    "CREATE TABLE tool_executions (run_id TEXT NOT NULL, tool_call_id TEXT NOT NULL, arguments_hash TEXT NOT NULL, status TEXT NOT NULL CHECK(status IN ('running','completed','failed')), result_json TEXT, PRIMARY KEY(run_id,tool_call_id))",
    "CREATE TABLE completed_turns (run_id TEXT PRIMARY KEY, conversation_key_json TEXT NOT NULL, user_text TEXT NOT NULL, reply TEXT NOT NULL, created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP)",
)
PERSONAL_DATA_SQL = (
    "CREATE TABLE personal_imports (source_name TEXT PRIMARY KEY, checksum TEXT NOT NULL, imported_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP)",
    "CREATE TABLE notes (id TEXT PRIMARY KEY, owner_id TEXT NOT NULL, kind TEXT NOT NULL CHECK(kind IN ('note','reminder')), text TEXT NOT NULL, due_at TEXT, source_message_id TEXT, created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP, UNIQUE(owner_id, source_message_id))",
    "CREATE INDEX idx_notes_owner_kind ON notes(owner_id, kind, created_at DESC)",
    "CREATE TABLE calendar_events (id TEXT PRIMARY KEY, owner_id TEXT NOT NULL, title TEXT NOT NULL, starts_at_utc TEXT NOT NULL, ends_at_utc TEXT, original_timezone TEXT NOT NULL DEFAULT 'UTC', description TEXT NOT NULL DEFAULT '', created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP)",
    "CREATE INDEX idx_calendar_owner_start ON calendar_events(owner_id, starts_at_utc)",
    "CREATE TABLE crm_contacts (id TEXT PRIMARY KEY, owner_id TEXT NOT NULL, payload_json TEXT NOT NULL, created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP, updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP)",
    "CREATE INDEX idx_crm_owner ON crm_contacts(owner_id)",
    "CREATE TABLE personal_tasks (id TEXT PRIMARY KEY, owner_id TEXT NOT NULL, text TEXT NOT NULL, status TEXT NOT NULL DEFAULT 'open', source_message_id TEXT, created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP, UNIQUE(owner_id, source_message_id))",
    "CREATE TABLE named_lists (id TEXT PRIMARY KEY, owner_id TEXT NOT NULL, name TEXT NOT NULL, created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP, UNIQUE(owner_id, name))",
    "CREATE TABLE named_list_items (id TEXT PRIMARY KEY, list_id TEXT NOT NULL REFERENCES named_lists(id) ON DELETE CASCADE, text TEXT NOT NULL, created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP)",
    "CREATE TABLE agent_definitions (id TEXT PRIMARY KEY, version INTEGER NOT NULL, definition_json TEXT NOT NULL, is_seed INTEGER NOT NULL DEFAULT 0, updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP)",
    "CREATE TABLE memory_consolidation_jobs (owner_id TEXT PRIMARY KEY, status TEXT NOT NULL, batch_hash TEXT, last_error TEXT, updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP)",
)
TELEGRAM_AND_AUDIT_SQL = (
    "CREATE TABLE telegram_updates (update_id INTEGER PRIMARY KEY, status TEXT NOT NULL CHECK(status IN ('received','processing','completed','failed')), run_id TEXT NOT NULL UNIQUE, attempt_count INTEGER NOT NULL DEFAULT 0, payload_hash TEXT NOT NULL, last_error TEXT, received_at TEXT NOT NULL, updated_at TEXT NOT NULL, completed_at TEXT)",
    "CREATE INDEX idx_telegram_updates_status ON telegram_updates(status, updated_at)",
    "CREATE TABLE gateway_channel_state (channel TEXT PRIMARY KEY, state_json TEXT NOT NULL, updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP)",
    "CREATE TABLE audit_events (id INTEGER PRIMARY KEY AUTOINCREMENT, event_id TEXT NOT NULL UNIQUE, run_id TEXT NOT NULL, owner_id TEXT NOT NULL, channel TEXT NOT NULL, direction TEXT NOT NULL CHECK(direction IN ('inbound','outbound','internal')), agent_id TEXT, model_name TEXT, event_type TEXT NOT NULL, payload_json TEXT NOT NULL, status TEXT NOT NULL, created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP)",
    "CREATE INDEX idx_audit_run ON audit_events(run_id)",
    "CREATE INDEX idx_audit_owner_created ON audit_events(owner_id, created_at DESC)",
    "CREATE INDEX idx_audit_channel ON audit_events(channel, created_at DESC)",
    "CREATE TABLE trajectory_steps (id INTEGER PRIMARY KEY AUTOINCREMENT, run_id TEXT NOT NULL, step_index INTEGER NOT NULL, step_type TEXT NOT NULL, payload_json TEXT NOT NULL, created_at TEXT NOT NULL, UNIQUE(run_id, step_index))",
    "CREATE INDEX idx_trajectory_steps_run ON trajectory_steps(run_id, step_index)",
)
MIGRATIONS = ((1, MEMORY_SQL), (2, RUNTIME_SQL), (3, PERSONAL_DATA_SQL), (4, TELEGRAM_AND_AUDIT_SQL))


def apply_migrations(db_path, embedding_dim=384):
    if not isinstance(embedding_dim, int) or embedding_dim < 1:
        raise ValueError('Invalid embedding dimension')
    with connection(db_path, vectors=True) as conn:
        conn.execute('BEGIN IMMEDIATE')
        try:
            conn.execute('CREATE TABLE IF NOT EXISTS schema_migrations (version INTEGER PRIMARY KEY, applied_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP, checksum TEXT NOT NULL)')
            existing = {r['version']: r['checksum'] for r in conn.execute('SELECT version, checksum FROM schema_migrations')}
            if any(v > MIGRATIONS[-1][0] for v in existing):
                raise RuntimeError('Database schema is newer than this application')
            if existing and sorted(existing) != list(range(1, max(existing) + 1)):
                raise RuntimeError('Database migration history has gaps')
            for version, statements in MIGRATIONS:
                checksum = hashlib.sha256(json.dumps(statements).encode()).hexdigest()
                if version in existing:
                    if existing[version] != checksum:
                        raise RuntimeError(f'Migration {version} checksum mismatch')
                    continue
                for statement in statements:
                    conn.execute(statement)
                    if version == 1 and statement.startswith('CREATE TABLE IF NOT EXISTS episodic_events'):
                        columns = {r['name'] for r in conn.execute('PRAGMA table_info(episodic_events)')}
                        if 'consolidated' not in columns:
                            conn.execute('ALTER TABLE episodic_events ADD COLUMN consolidated INTEGER NOT NULL DEFAULT 0')
                if version == 1:
                    try:
                        conn.execute('SELECT vec_version()')
                        conn.execute(f'CREATE VIRTUAL TABLE IF NOT EXISTS vec_episodes USING vec0(embedding float[{embedding_dim}])')
                    except sqlite3.OperationalError:
                        conn.execute('CREATE TABLE IF NOT EXISTS vec_episodes (rowid INTEGER PRIMARY KEY, embedding TEXT)')
                conn.execute('INSERT INTO schema_migrations(version, checksum) VALUES (?,?)', (version, checksum))
            conn.commit()
        except BaseException:
            conn.rollback()
            raise
