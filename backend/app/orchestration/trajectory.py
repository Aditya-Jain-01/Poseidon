"""Execution trajectory recorder with secret scrubbing and SQLite persistence, keyed by run id."""
from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from collections import defaultdict
from pathlib import Path
from typing import Any

from app.config import settings
from app.security.secrets import redact


# Scrubs API keys, tokens, and bearer headers from trajectory logs
# so they never appear in the /runs/{run_id}/trajectory API response
_SECRET_PATTERN = re.compile(
    r"(?i)(sk-[a-zA-Z0-9_-]{20,}|nvapi-[a-zA-Z0-9_-]{20,}|ghp_[a-zA-Z0-9]{36}|bearer\s+[a-zA-Z0-9._-]+|token=[a-zA-Z0-9._-]+)"
)


def _scrub(val: Any) -> Any:
    if isinstance(val, str):
        return _SECRET_PATTERN.sub("[REDACTED_SECRET]", val)
    if isinstance(val, dict):
        return {k: _scrub(v) for k, v in val.items()}
    if isinstance(val, list):
        return [_scrub(i) for i in val]
    return val


class TrajectoryStore:
    def __init__(self, db_path: Path | str | None = None) -> None:
        self._db_path = Path(db_path) if db_path else None
        self._runs: dict[str, list[dict[str, Any]]] = defaultdict(list)

    @property
    def db_path(self) -> Path:
        return self._db_path or settings.poseidon_db_path

    def record(self, run_id: str, step_type: str, **fields: Any) -> dict[str, Any]:
        scrubbed = {k: redact(_scrub(v)) for k, v in fields.items()}
        ts = datetime.now(timezone.utc).isoformat()
        step = {"step_type": step_type, "timestamp": ts, **scrubbed}
        self._runs[run_id].append(step)

        # Persist to SQLite if DB exists
        if self.db_path.exists():
            try:
                from app.db.connection import connection

                with connection(self.db_path) as conn:
                    # Determine next step_index
                    row = conn.execute(
                        "SELECT COUNT(*) FROM trajectory_steps WHERE run_id = ?",
                        (run_id,),
                    ).fetchone()
                    idx = row[0] if row else len(self._runs[run_id]) - 1

                    payload_json = json.dumps(step, default=str)
                    if len(payload_json) > 32768:
                        payload_json = json.dumps(
                            {"step_type": step_type, "timestamp": ts, "truncated": True}
                        )

                    conn.execute(
                        "INSERT OR REPLACE INTO trajectory_steps (run_id, step_index, step_type, payload_json, created_at) VALUES (?, ?, ?, ?, ?)",
                        (run_id, idx, step_type, payload_json, ts),
                    )
                    conn.commit()
            except Exception:
                pass

        return step

    def get(self, run_id: str) -> list[dict[str, Any]]:
        if run_id in self._runs and len(self._runs[run_id]) > 0:
            return list(self._runs[run_id])

        # If not in-memory (e.g. after server restart), read from SQLite
        if self.db_path.exists():
            try:
                from app.db.connection import connection

                with connection(self.db_path) as conn:
                    rows = conn.execute(
                        "SELECT payload_json FROM trajectory_steps WHERE run_id = ? ORDER BY step_index ASC",
                        (run_id,),
                    ).fetchall()
                    if rows:
                        steps = [json.loads(r[0]) for r in rows]
                        self._runs[run_id] = steps
                        return steps
            except Exception:
                pass

        return list(self._runs.get(run_id, []))


trajectory_store = TrajectoryStore()
