"""Semantic Memory Store — durable facts and user profile.

Sprint 2 (Person B — Stage 2):
- Persistent semantic store backed by MEMORY.md + SQLite FTS5 index.
- Stores durable facts, user preferences, and profile data.
- Keyword top-k retrieval (no embedding model — deliberately cheap/deterministic).
- Human-readable MEMORY.md mirror auto-regenerated on writes.
- The Summarizer Agent (Stage 5) distills episodic entries into semantic facts.
"""

import json
import re
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Generator

from app.config import settings


def _sanitize_fts_query(query: str) -> str:
    """Sanitize user query string for SQLite FTS5 MATCH syntax."""
    tokens = re.findall(r"\w+", query, re.UNICODE)
    if not tokens:
        return ""
    return " OR ".join(f'"{token}"*' for token in tokens)


class SemanticStore:
    """SQLite + MEMORY.md backed semantic memory with FTS5 keyword search.

    Facts are stored in SQLite for querying and mirrored to a human-readable
    MEMORY.md file that you can open and inspect at any time.
    """

    def __init__(
        self,
        db_path: Path | str | None = None,
        memory_md_path: Path | str | None = None,
    ) -> None:
        if db_path is None:
            self.db_path = Path(settings.poseidon_db_path)
        else:
            self.db_path = Path(db_path)

        if memory_md_path is None:
            self.memory_md_path = self.db_path.parent / "memory" / "MEMORY.md"
        else:
            self.memory_md_path = Path(memory_md_path)

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
        """Initialize semantic memory tables and FTS5 index inside state.db."""
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        with self._get_connection() as conn:
            cursor = conn.cursor()

            # 1. Semantic facts table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS semantic_facts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id TEXT NOT NULL,
                    fact TEXT NOT NULL,
                    category TEXT NOT NULL DEFAULT 'general',
                    source_run_id TEXT,
                    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    active INTEGER NOT NULL DEFAULT 1
                );
            """)

            # 2. Index for user + category lookups
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_semantic_user_category
                ON semantic_facts(user_id, category, active);
            """)

            # 3. FTS5 virtual table for keyword search over facts
            cursor.execute("""
                CREATE VIRTUAL TABLE IF NOT EXISTS semantic_fts USING fts5(
                    fact,
                    category UNINDEXED,
                    user_id UNINDEXED,
                    fact_id UNINDEXED,
                    tokenize='unicode61'
                );
            """)

            # 4. Triggers to keep FTS5 in sync with semantic_facts
            cursor.execute("""
                CREATE TRIGGER IF NOT EXISTS trg_semantic_after_insert
                AFTER INSERT ON semantic_facts
                BEGIN
                    INSERT INTO semantic_fts(rowid, fact, category, user_id, fact_id)
                    VALUES (new.id, new.fact, new.category, new.user_id, new.id);
                END;
            """)

            cursor.execute("""
                CREATE TRIGGER IF NOT EXISTS trg_semantic_after_delete
                AFTER DELETE ON semantic_facts
                BEGIN
                    DELETE FROM semantic_fts WHERE rowid = old.id;
                END;
            """)

            cursor.execute("""
                CREATE TRIGGER IF NOT EXISTS trg_semantic_after_update
                AFTER UPDATE ON semantic_facts
                BEGIN
                    DELETE FROM semantic_fts WHERE rowid = old.id;
                    INSERT INTO semantic_fts(rowid, fact, category, user_id, fact_id)
                    VALUES (new.id, new.fact, new.category, new.user_id, new.id);
                END;
            """)

            conn.commit()

    # ── Write Operations ──

    def add_fact(
        self,
        user_id: str,
        fact: str,
        category: str = "general",
        source_run_id: str | None = None,
    ) -> int:
        """Store a new semantic fact. Returns the fact ID.

        Categories: 'preference', 'profile', 'relationship', 'general'
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO semantic_facts (user_id, fact, category, source_run_id)
                VALUES (?, ?, ?, ?)
                """,
                (user_id, fact.strip(), category, source_run_id),
            )
            fact_id = cursor.lastrowid
            conn.commit()

        # Regenerate the human-readable mirror
        self._regenerate_memory_md(user_id)
        return int(fact_id)

    def update_fact(self, fact_id: int, new_fact: str) -> bool:
        """Update an existing fact's content. Returns True if updated."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                UPDATE semantic_facts
                SET fact = ?, updated_at = CURRENT_TIMESTAMP
                WHERE id = ? AND active = 1
                """,
                (new_fact.strip(), fact_id),
            )
            updated = cursor.rowcount > 0
            conn.commit()

        if updated:
            # Find the user_id to regenerate their MEMORY.md
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT user_id FROM semantic_facts WHERE id = ?", (fact_id,))
                row = cursor.fetchone()
                if row:
                    self._regenerate_memory_md(row["user_id"])
        return updated

    def deactivate_fact(self, fact_id: int) -> bool:
        """Soft-delete a fact (mark as inactive). Returns True if deactivated."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            # Get user_id before deactivating
            cursor.execute("SELECT user_id FROM semantic_facts WHERE id = ?", (fact_id,))
            row = cursor.fetchone()
            user_id = row["user_id"] if row else None

            cursor.execute(
                "UPDATE semantic_facts SET active = 0, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
                (fact_id,),
            )
            deactivated = cursor.rowcount > 0
            conn.commit()

        if deactivated and user_id:
            self._regenerate_memory_md(user_id)
        return deactivated

    # ── Read Operations ──

    def get_all_facts(self, user_id: str, category: str | None = None) -> list[dict[str, Any]]:
        """Get all active semantic facts for a user, optionally filtered by category."""
        query = "SELECT id, user_id, fact, category, source_run_id, created_at, updated_at FROM semantic_facts WHERE user_id = ? AND active = 1"
        params: list[Any] = [user_id]

        if category:
            query += " AND category = ?"
            params.append(category)

        query += " ORDER BY created_at DESC"

        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, params)
            return [dict(row) for row in cursor.fetchall()]

    def retrieve(
        self,
        user_id: str,
        query: str,
        limit: int = 10,
    ) -> list[dict[str, Any]]:
        """Keyword top-k retrieval over semantic facts using FTS5.

        This is the main interface that Working Memory calls.
        Returns matching facts ranked by BM25 relevance.
        """
        sanitized = _sanitize_fts_query(query)
        if not sanitized:
            # Fall back to returning all facts if query can't be tokenized
            return self.get_all_facts(user_id)[:limit]

        sql = """
            SELECT f.id, f.user_id, f.fact, f.category, f.source_run_id,
                   f.created_at, f.updated_at,
                   bm25(semantic_fts) as rank
            FROM semantic_fts s
            JOIN semantic_facts f ON s.rowid = f.id
            WHERE semantic_fts MATCH ? AND s.user_id = ? AND f.active = 1
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
                # FTS query failed — fall back to returning recent facts
                return self.get_all_facts(user_id)[:limit]

    # ── MEMORY.md Mirror ──

    def _regenerate_memory_md(self, user_id: str) -> None:
        """Regenerate the human-readable MEMORY.md file from current facts.

        This is the mirror that you can open and read at any time.
        The database is the source of truth; this file is just the view.
        """
        facts = self.get_all_facts(user_id)
        if not facts:
            return

        # Group facts by category
        by_category: dict[str, list[dict[str, Any]]] = {}
        for f in facts:
            cat = f.get("category", "general")
            by_category.setdefault(cat, []).append(f)

        lines = [
            f"# Memory — {user_id}",
            f"",
            f"_Auto-generated from `state.db`. Last updated: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}_",
            f"",
        ]

        category_labels = {
            "preference": "🎯 Preferences",
            "profile": "👤 Profile",
            "relationship": "🤝 Relationships",
            "general": "📝 General Facts",
        }

        for cat, cat_facts in sorted(by_category.items()):
            label = category_labels.get(cat, f"📋 {cat.title()}")
            lines.append(f"## {label}")
            lines.append("")
            for f in cat_facts:
                ts = f.get("created_at", "")
                lines.append(f"- {f['fact']}  _{ts}_")
            lines.append("")

        # Write the file
        self.memory_md_path.parent.mkdir(parents=True, exist_ok=True)
        self.memory_md_path.write_text("\n".join(lines), encoding="utf-8")

    # ── Utility ──

    def clear(self, user_id: str | None = None) -> None:
        """Clear semantic facts (useful for test isolation)."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            if user_id:
                cursor.execute("DELETE FROM semantic_facts WHERE user_id = ?", (user_id,))
            else:
                cursor.execute("DELETE FROM semantic_facts")
            conn.commit()

    def count(self, user_id: str | None = None) -> int:
        """Count active semantic facts."""
        query = "SELECT COUNT(*) FROM semantic_facts WHERE active = 1"
        params: list[Any] = []
        if user_id:
            query += " AND user_id = ?"
            params.append(user_id)

        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, params)
            return cursor.fetchone()[0]


# App-wide singleton instance
semantic_store = SemanticStore()
