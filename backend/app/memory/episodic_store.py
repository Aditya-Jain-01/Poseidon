"""Episodic Memory Store — SQLite structured log + FTS5 full-text search index.

Sprint 2 (Person A):
- Persistent episodic store on disk (`memory-store/state.db`).
- SQLite table for chronological dated events and chat history.
- FTS5 virtual table for keyword relevance ranking.
- SQL recency retrieval + FTS5 relevance retrieval blended into Working Memory.
- Consolidation counting support ("only after N new chats").
"""

import json
import re
import sqlite3
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import Any, Generator

from app.config import settings


def _sanitize_fts_query(query: str) -> str:
    """Sanitize user query string for SQLite FTS5 MATCH syntax."""
    tokens = re.findall(r"\w+", query, re.UNICODE)
    if not tokens:
        return ""
    return " OR ".join(f'"{token}"*' for token in tokens)


class EpisodicStore:
    """SQLite-backed episodic memory with full-text search (FTS5)."""

    def __init__(self, db_path: Path | str | None = None) -> None:
        if db_path is None:
            self.db_path = Path(settings.poseidon_db_path)
        else:
            self.db_path = Path(db_path)
        self.init_db()

    @contextmanager
    def _get_connection(self) -> Generator[sqlite3.Connection, None, None]:
        """Context manager creating a connection and ensuring it is cleanly closed."""
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(str(self.db_path), timeout=10.0)
        conn.row_factory = sqlite3.Row
        try:
            conn.execute("PRAGMA journal_mode=WAL;")
            conn.execute("PRAGMA foreign_keys=ON;")
            yield conn
        finally:
            conn.close()

    def init_db(self) -> None:
        """Initialize database schema, tables, indices, and FTS5 virtual table."""
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        with self._get_connection() as conn:
            cursor = conn.cursor()

            # 1. Base episodic log table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS episodic_events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id TEXT NOT NULL,
                    channel TEXT NOT NULL DEFAULT 'web',
                    run_id TEXT,
                    role TEXT NOT NULL,
                    content TEXT NOT NULL,
                    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    metadata TEXT,
                    consolidated INTEGER NOT NULL DEFAULT 0
                );
            """)

            # 2. Indices for recency & consolidation queries
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_episodic_user_created 
                ON episodic_events(user_id, created_at DESC);
            """)
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_episodic_consolidated 
                ON episodic_events(consolidated);
            """)

            # 3. FTS5 virtual table for keyword relevance search
            cursor.execute("""
                CREATE VIRTUAL TABLE IF NOT EXISTS episodic_fts USING fts5(
                    content,
                    user_id UNINDEXED,
                    event_id UNINDEXED,
                    tokenize='unicode61'
                );
            """)

            # 4. Triggers to keep FTS5 synchronized with episodic_events
            cursor.execute("""
                CREATE TRIGGER IF NOT EXISTS trg_episodic_after_insert
                AFTER INSERT ON episodic_events
                BEGIN
                    INSERT INTO episodic_fts(rowid, content, user_id, event_id)
                    VALUES (new.id, new.content, new.user_id, new.id);
                END;
            """)

            cursor.execute("""
                CREATE TRIGGER IF NOT EXISTS trg_episodic_after_delete
                AFTER DELETE ON episodic_events
                BEGIN
                    DELETE FROM episodic_fts WHERE rowid = old.id;
                END;
            """)

            cursor.execute("""
                CREATE TRIGGER IF NOT EXISTS trg_episodic_after_update
                AFTER UPDATE ON episodic_events
                BEGIN
                    DELETE FROM episodic_fts WHERE rowid = old.id;
                    INSERT INTO episodic_fts(rowid, content, user_id, event_id)
                    VALUES (new.id, new.content, new.user_id, new.id);
                END;
            """)

            conn.commit()

    def log_event(
        self,
        user_id: str,
        role: str,
        content: str,
        channel: str = "web",
        run_id: str | None = None,
        metadata: dict[str, Any] | None = None,
        created_at: str | datetime | None = None,
    ) -> int:
        """Log a single episodic event into persistent storage.

        Returns the newly created event ID.
        """
        meta_json = json.dumps(metadata) if metadata else None
        ts = created_at.isoformat() if isinstance(created_at, datetime) else created_at

        with self._get_connection() as conn:
            cursor = conn.cursor()
            if ts:
                cursor.execute(
                    """
                    INSERT INTO episodic_events (user_id, channel, run_id, role, content, metadata, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (user_id, channel, run_id, role, content, meta_json, ts),
                )
            else:
                cursor.execute(
                    """
                    INSERT INTO episodic_events (user_id, channel, run_id, role, content, metadata)
                    VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (user_id, channel, run_id, role, content, meta_json),
                )
            event_id = cursor.lastrowid
            conn.commit()
            return int(event_id)

    def log_exchange(
        self,
        user_id: str,
        human_msg: str,
        ai_msg: str,
        channel: str = "web",
        run_id: str | None = None,
    ) -> tuple[int, int]:
        """Log a full conversation turn (User prompt + AI reply).

        Returns tuple of (user_event_id, ai_event_id).
        """
        user_id_int = self.log_event(
            user_id=user_id,
            role="user",
            content=human_msg,
            channel=channel,
            run_id=run_id,
        )
        ai_id_int = self.log_event(
            user_id=user_id,
            role="assistant",
            content=ai_msg,
            channel=channel,
            run_id=run_id,
        )
        return user_id_int, ai_id_int

    def get_recent(
        self,
        user_id: str,
        limit: int = 10,
        since: str | datetime | None = None,
    ) -> list[dict[str, Any]]:
        """Retrieve recent episodic events for a user (recency retrieval).

        Returns events ordered chronologically (oldest to newest).
        """
        query = "SELECT id, user_id, channel, run_id, role, content, created_at, metadata, consolidated FROM episodic_events WHERE user_id = ?"
        params: list[Any] = [user_id]

        if since:
            since_str = since.isoformat() if isinstance(since, datetime) else str(since)
            query += " AND created_at >= ?"
            params.append(since_str)

        query += " ORDER BY created_at DESC, id DESC LIMIT ?"
        params.append(limit)

        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, params)
            rows = cursor.fetchall()
            events = [dict(row) for row in reversed(rows)]
            return events

    def search_relevant(
        self,
        user_id: str,
        query: str,
        limit: int = 5,
    ) -> list[dict[str, Any]]:
        """Search episodic events matching query using FTS5 keyword relevance.

        Returns matching events ranked by BM25 relevance.
        """
        sanitized = _sanitize_fts_query(query)
        if not sanitized:
            return []

        sql = """
            SELECT e.id, e.user_id, e.channel, e.run_id, e.role, e.content, e.created_at, e.metadata, e.consolidated,
                   bm25(episodic_fts) as rank
            FROM episodic_fts f
            JOIN episodic_events e ON f.rowid = e.id
            WHERE episodic_fts MATCH ? AND f.user_id = ?
            ORDER BY rank
            LIMIT ?
        """

        with self._get_connection() as conn:
            cursor = conn.cursor()
            try:
                cursor.execute(sql, (sanitized, user_id, limit))
                rows = cursor.fetchall()
                return [dict(row) for row in rows]
            except sqlite3.OperationalError:
                return []

    def retrieve(
        self,
        user_id: str,
        query: str,
        recency_limit: int = 5,
        relevance_limit: int = 5,
    ) -> list[dict[str, Any]]:
        """Hybrid retrieval combining FTS5 relevance and SQL recency.

        Deduplicates records and returns them in chronological order.
        """
        # 1. Fetch relevant records
        relevant_events = self.search_relevant(user_id, query, limit=relevance_limit)

        # 2. Fetch recent records
        recent_events = self.get_recent(user_id, limit=recency_limit)

        # 3. Merge and deduplicate by ID
        seen_ids = set()
        combined: list[dict[str, Any]] = []

        for ev in relevant_events:
            if ev["id"] not in seen_ids:
                seen_ids.add(ev["id"])
                combined.append(ev)

        for ev in recent_events:
            if ev["id"] not in seen_ids:
                seen_ids.add(ev["id"])
                combined.append(ev)

        combined.sort(key=lambda x: (x["created_at"], x["id"]))
        return combined

    def count_unconsolidated(self, user_id: str | None = None) -> int:
        """Count episodic events that have not yet been consolidated."""
        query = "SELECT COUNT(*) FROM episodic_events WHERE consolidated = 0"
        params: list[Any] = []
        if user_id:
            query += " AND user_id = ?"
            params.append(user_id)

        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, params)
            return cursor.fetchone()[0]

    def mark_consolidated(
        self,
        event_ids: list[int] | None = None,
        up_to_id: int | None = None,
    ) -> int:
        """Mark episodic events as consolidated."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            if event_ids:
                placeholders = ",".join("?" for _ in event_ids)
                cursor.execute(
                    f"UPDATE episodic_events SET consolidated = 1 WHERE id IN ({placeholders})",
                    list(event_ids),
                )
            elif up_to_id is not None:
                cursor.execute(
                    "UPDATE episodic_events SET consolidated = 1 WHERE id <= ?",
                    (up_to_id,),
                )
            else:
                cursor.execute("UPDATE episodic_events SET consolidated = 1 WHERE consolidated = 0")
            affected = cursor.rowcount
            conn.commit()
            return affected

    def clear(self, user_id: str | None = None) -> None:
        """Clear episodic memory records (useful for test isolation)."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            if user_id:
                cursor.execute("DELETE FROM episodic_events WHERE user_id = ?", (user_id,))
            else:
                cursor.execute("DELETE FROM episodic_events")
            conn.commit()


# App-wide singleton instance
episodic_store = EpisodicStore()
