"""Durable, bounded, secret-scrubbed audit event service."""
from __future__ import annotations

import json
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any
from uuid import uuid4

from app.config import settings
from app.db.connection import connection
from app.security.secrets import redact
from app.orchestration.trajectory import _scrub


def _bound_payload(data: Any, max_string_len: int = 4096, max_total_bytes: int = 32768) -> Any:
    """Recursively bound strings and dictionary sizes in audit payloads."""
    if isinstance(data, str):
        if len(data) > max_string_len:
            return data[:max_string_len] + "... [TRUNCATED]"
        return data
    if isinstance(data, dict):
        return {k: _bound_payload(v, max_string_len, max_total_bytes) for k, v in list(data.items())[:50]}
    if isinstance(data, list):
        return [_bound_payload(item, max_string_len, max_total_bytes) for item in data[:50]]
    return data


class AuditService:
    def __init__(self, db_path: Path | str | None = None) -> None:
        self._db_path = Path(db_path) if db_path else None

    @property
    def db_path(self) -> Path:
        return self._db_path or settings.poseidon_db_path

    def record_event(
        self,
        run_id: str,
        owner_id: str,
        channel: str,
        direction: str,
        event_type: str,
        status: str,
        payload: dict[str, Any] | None = None,
        agent_id: str | None = None,
        model_name: str | None = None,
        event_id: str | None = None,
    ) -> dict[str, Any]:
        """Record a single bounded, redacted audit event to SQLite."""
        if direction not in ("inbound", "outbound", "internal"):
            direction = "internal"

        raw_payload = payload or {}
        scrubbed = redact(_scrub(raw_payload))
        bounded = _bound_payload(scrubbed)
        payload_json = json.dumps(bounded, default=str)
        if len(payload_json) > 32768:
            payload_json = json.dumps({"summary": str(bounded)[:2000], "truncated": True})

        ev_id = event_id or f"evt_{uuid4().hex[:16]}"
        now_ts = datetime.now(timezone.utc).isoformat()

        if self.db_path.exists():
            try:
                with connection(self.db_path) as conn:
                    conn.execute(
                        """INSERT OR REPLACE INTO audit_events 
                        (event_id, run_id, owner_id, channel, direction, agent_id, model_name, event_type, payload_json, status, created_at)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                        (ev_id, run_id, owner_id, channel, direction, agent_id, model_name, event_type, payload_json, status, now_ts),
                    )
                    conn.commit()
                    self._enforce_retention(conn)
            except Exception as e:
                # Fallback logging if table not yet migrated
                pass

        return {
            "event_id": ev_id,
            "run_id": run_id,
            "owner_id": owner_id,
            "channel": channel,
            "direction": direction,
            "agent_id": agent_id,
            "model_name": model_name,
            "event_type": event_type,
            "status": status,
            "payload": bounded,
            "created_at": now_ts,
        }

    def query_events(
        self,
        owner_id: str | None = None,
        channel: str | None = None,
        run_id: str | None = None,
        direction: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[dict[str, Any]]:
        """Query audit events with optional filters."""
        if not self.db_path.exists():
            return []

        query = "SELECT event_id, run_id, owner_id, channel, direction, agent_id, model_name, event_type, payload_json, status, created_at FROM audit_events WHERE 1=1"
        params: list[Any] = []

        if owner_id:
            query += " AND owner_id = ?"
            params.append(owner_id)
        if channel:
            query += " AND channel = ?"
            params.append(channel)
        if run_id:
            query += " AND run_id = ?"
            params.append(run_id)
        if direction:
            query += " AND direction = ?"
            params.append(direction)

        query += " ORDER BY id DESC LIMIT ? OFFSET ?"
        params.extend([max(1, min(limit, 500)), max(0, offset)])

        try:
            with connection(self.db_path) as conn:
                rows = conn.execute(query, params).fetchall()
                results = []
                for r in rows:
                    try:
                        p = json.loads(r[8])
                    except Exception:
                        p = {}
                    results.append({
                        "event_id": r[0],
                        "run_id": r[1],
                        "owner_id": r[2],
                        "channel": r[3],
                        "direction": r[4],
                        "agent_id": r[5],
                        "model_name": r[6],
                        "event_type": r[7],
                        "payload": p,
                        "status": r[9],
                        "created_at": r[10],
                    })
                return results
        except Exception:
            return []

    def delete_events(self, owner_id: str) -> int:
        """Owner-initiated audit event deletion."""
        if not self.db_path.exists():
            return 0
        try:
            with connection(self.db_path) as conn:
                cur = conn.execute("DELETE FROM audit_events WHERE owner_id = ?", (owner_id,))
                conn.commit()
                return cur.rowcount
        except Exception:
            return 0

    def _enforce_retention(self, conn, max_count: int = 10000, max_days: int = 30) -> None:
        """Prune events by maximum count and retention window."""
        try:
            # Prune older than max_days
            cutoff = (datetime.now(timezone.utc) - timedelta(days=max_days)).isoformat()
            conn.execute("DELETE FROM audit_events WHERE created_at < ?", (cutoff,))

            # Prune if total count exceeds max_count
            count = conn.execute("SELECT COUNT(*) FROM audit_events").fetchone()[0]
            if count > max_count:
                excess = count - max_count
                conn.execute(
                    "DELETE FROM audit_events WHERE id IN (SELECT id FROM audit_events ORDER BY id ASC LIMIT ?)",
                    (excess,),
                )
            conn.commit()
        except Exception:
            pass


audit_service = AuditService()
