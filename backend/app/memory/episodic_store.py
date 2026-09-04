"""Episodic Memory Store — SQLite structured log + sqlite-vec vector RAG.

Sprint 2 (Vector RAG Upgrade):
- Persistent episodic store on disk (`memory-store/state.db`).
- SQLite table for chronological dated events and chat history.
- sqlite-vec virtual table for vector similarity (KNN) retrieval.
- SQL recency retrieval + Vector RAG relevance retrieval blended into Working Memory.
- Consolidation counting support ("only after N new chats").
"""

import json
import sqlite3
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import Any, Generator

try:
    import sqlite_vec
    HAS_SQLITE_VEC = True
except ImportError:
    sqlite_vec = None
    HAS_SQLITE_VEC = False

try:
    import numpy as np
except ImportError:
    np = None

from app.config import settings
from app.memory.embeddings import embedding_service


class EpisodicStore:
    """SQLite-backed episodic memory with sqlite-vec vector search (RAG)."""

    def __init__(self, db_path: Path | str | None = None, embed_svc=None) -> None:
        if db_path is None:
            self.db_path = Path(settings.poseidon_db_path)
        else:
            self.db_path = Path(db_path)
        self._embed = embed_svc or embedding_service
        self._dim = settings.poseidon_embedding_dim
        self.init_db()

    @contextmanager
    def _get_connection(self) -> Generator[sqlite3.Connection, None, None]:
        """Context manager creating a connection with sqlite-vec loaded if available."""
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(str(self.db_path), timeout=10.0)
        conn.row_factory = sqlite3.Row
        try:
            conn.execute("PRAGMA journal_mode=WAL;")
            conn.execute("PRAGMA foreign_keys=ON;")
            if HAS_SQLITE_VEC and sqlite_vec is not None:
                try:
                    conn.enable_load_extension(True)
                    sqlite_vec.load(conn)
                    conn.enable_load_extension(False)
                except Exception:
                    pass
            yield conn
        finally:
            conn.close()

    def init_db(self) -> None:
        """Initialize database schema, tables, indices, and vec0 virtual table."""
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

            # 3. sqlite-vec virtual table for vector similarity search (or fallback table)
            try:
                cursor.execute(f"""
                    CREATE VIRTUAL TABLE IF NOT EXISTS vec_episodes USING vec0(
                        embedding float[{self._dim}]
                    );
                """)
            except Exception:
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS vec_episodes (
                        rowid INTEGER PRIMARY KEY,
                        embedding TEXT
                    );
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
        """Log a single episodic event and store its vector embedding.

        Returns the newly created event ID.
        """
        meta_json = json.dumps(metadata) if metadata else None
        ts = created_at.isoformat() if isinstance(created_at, datetime) else created_at

        # Generate the embedding vector for this content
        vector = self._embed.embed_text(content)
        vec_json = json.dumps(vector)

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

            # Insert the vector into vec_episodes (rowid must match event id)
            try:
                cursor.execute(
                    "INSERT INTO vec_episodes(rowid, embedding) VALUES (?, ?)",
                    (event_id, vec_json),
                )
            except Exception:
                pass

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
        """Search episodic events using vector similarity (KNN).

        Embeds the query, finds the closest vectors in vec_episodes,
        then joins back to episodic_events for the full record.
        Filters by user_id after the KNN search.
        """
        if not query.strip():
            return []

        # Embed the query text
        query_vector = self._embed.embed_text(query)
        vec_json = json.dumps(query_vector)

        # KNN search via sqlite-vec: fetch more than `limit` to allow for
        # user_id filtering (vec0 doesn't support WHERE on external columns)
        fetch_limit = limit * 4

        # sqlite-vec requires `AND k = ?` instead of `LIMIT ?` for KNN queries
        sql = """
            SELECT v.rowid AS event_id, v.distance
            FROM vec_episodes v
            WHERE v.embedding MATCH ?
              AND k = ?
            ORDER BY v.distance
        """

        with self._get_connection() as conn:
            cursor = conn.cursor()
            try:
                cursor.execute(sql, (vec_json, fetch_limit))
                vec_rows = cursor.fetchall()
                if not vec_rows:
                    return []
                results: list[dict[str, Any]] = []
                for vr in vec_rows:
                    if len(results) >= limit:
                        break
                    ev_cursor = conn.cursor()
                    ev_cursor.execute(
                        "SELECT id, user_id, channel, run_id, role, content, created_at, metadata, consolidated "
                        "FROM episodic_events WHERE id = ? AND user_id = ?",
                        (vr["event_id"], user_id),
                    )
                    row = ev_cursor.fetchone()
                    if row:
                        event_dict = dict(row)
                        event_dict["_vec_distance"] = vr["distance"]
                        results.append(event_dict)
                return results
            except sqlite3.OperationalError:
                # Fallback: load embeddings from table and compute cosine distance in Python
                try:
                    cursor.execute("""
                        SELECT e.id, e.user_id, e.channel, e.run_id, e.role, e.content, e.created_at, e.metadata, e.consolidated, v.embedding
                        FROM episodic_events e
                        JOIN vec_episodes v ON e.id = v.rowid
                        WHERE e.user_id = ?
                    """, (user_id,))
                    all_rows = cursor.fetchall()
                    if not all_rows:
                        return []
                    
                    if np is not None:
                        q_arr = np.array(query_vector, dtype=float)
                        q_norm = np.linalg.norm(q_arr)
                        if q_norm == 0:
                            return []

                        scored = []
                        for r in all_rows:
                            r_dict = dict(r)
                            emb_raw = r_dict.pop("embedding", None)
                            if emb_raw:
                                try:
                                    emb_list = json.loads(emb_raw) if isinstance(emb_raw, str) else emb_raw
                                    v_arr = np.array(emb_list, dtype=float)
                                    v_norm = np.linalg.norm(v_arr)
                                    if v_norm > 0:
                                        sim = np.dot(q_arr, v_arr) / (q_norm * v_norm)
                                        dist = 1.0 - float(sim)
                                        r_dict["_vec_distance"] = dist
                                        scored.append((dist, r_dict))
                                except Exception:
                                    pass
                    else:
                        q_norm = sum(x * x for x in query_vector) ** 0.5
                        if q_norm == 0:
                            return []

                        scored = []
                        for r in all_rows:
                            r_dict = dict(r)
                            emb_raw = r_dict.pop("embedding", None)
                            if emb_raw:
                                try:
                                    emb_list = json.loads(emb_raw) if isinstance(emb_raw, str) else emb_raw
                                    v_norm = sum(x * x for x in emb_list) ** 0.5
                                    if v_norm > 0:
                                        dot = sum(a * b for a, b in zip(query_vector, emb_list))
                                        sim = dot / (q_norm * v_norm)
                                        dist = 1.0 - float(sim)
                                        r_dict["_vec_distance"] = dist
                                        scored.append((dist, r_dict))
                                except Exception:
                                    pass

                    scored.sort(key=lambda x: x[0])
                    return [item[1] for item in scored[:limit]]
                except Exception:
                    return []

    def retrieve(
        self,
        user_id: str,
        query: str,
        recency_limit: int = 5,
        relevance_limit: int = 5,
    ) -> list[dict[str, Any]]:
        """Retrieve episodic events semantically relevant to the user query.

        If a query is provided, performs vector similarity search to avoid
        polluting the context with unrelated prior session chat history.
        """
        if not query or not query.strip():
            # If no query provided, return recent events as fallback
            return self.get_recent(user_id, limit=recency_limit)

        # Vector RAG search for semantically relevant episodic events
        relevant_events = self.search_relevant(user_id, query.strip(), limit=relevance_limit)
        seen_ids = set()
        combined: list[dict[str, Any]] = []

        for ev in relevant_events:
            if ev["id"] not in seen_ids:
                seen_ids.add(ev["id"])
                ev.pop("_vec_distance", None)
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
                # Get IDs to delete from vec table
                cursor.execute("SELECT id FROM episodic_events WHERE user_id = ?", (user_id,))
                ids = [row[0] for row in cursor.fetchall()]
                cursor.execute("DELETE FROM episodic_events WHERE user_id = ?", (user_id,))
                for eid in ids:
                    cursor.execute("DELETE FROM vec_episodes WHERE rowid = ?", (eid,))
            else:
                cursor.execute("DELETE FROM episodic_events")
                cursor.execute("DELETE FROM vec_episodes")
            conn.commit()


# App-wide singleton instance
episodic_store = EpisodicStore()
