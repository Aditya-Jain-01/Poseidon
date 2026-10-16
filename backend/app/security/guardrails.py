"""Durable, single-owner guardrails shared by every gateway and tool run."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
import json
from pathlib import Path

from app.config import settings
from app.db.connection import connection
from app.db.migrations import apply_migrations


class HarnessPausedError(RuntimeError):
    """A tool or approval cannot proceed while the operator has paused runs."""


class GuardrailRateLimitError(RuntimeError):
    """An hourly guardrail limit has been reached."""


def record_limit_alert(conn, kind: str, timestamp: datetime) -> None:
    """Surface one durable operator-visible audit alert per kind and UTC hour."""
    conn.execute(
        "INSERT OR IGNORE INTO audit_events(event_id,run_id,owner_id,channel,direction,event_type,payload_json,status,created_at) "
        "VALUES (?,?,?,?,?,?,?,?,?)",
        (f'guardrail:{kind}:{timestamp.strftime("%Y%m%d%H")}', 'guardrails', 'local_owner',
         'internal', 'internal', 'guardrail_limit', json.dumps({'kind': kind}), 'blocked', timestamp.isoformat()),
    )


class GuardrailStore:
    def __init__(self, db_path: Path | None = None):
        self._db_path = db_path

    @property
    def db_path(self) -> Path:
        return self._db_path or settings.poseidon_db_path

    def is_paused(self) -> bool:
        apply_migrations(self.db_path)
        with connection(self.db_path) as conn:
            return bool(conn.execute("SELECT paused FROM guardrail_state WHERE id=1").fetchone()[0])

    def require_active(self) -> None:
        if self.is_paused():
            raise HarnessPausedError("Tool execution is paused by the operator")

    def set_paused(self, paused: bool) -> bool:
        apply_migrations(self.db_path)
        with connection(self.db_path) as conn:
            with conn:
                conn.execute("UPDATE guardrail_state SET paused=?, updated_at=? WHERE id=1",
                             (int(paused), datetime.now(timezone.utc).isoformat()))
        return paused

    def reserve_outbound_attempt(self, channel: str) -> None:
        """Count attempted sends, including failures and retries, before network I/O."""
        apply_migrations(self.db_path)
        now = datetime.now(timezone.utc)
        cutoff = (now - timedelta(hours=1)).isoformat()
        with connection(self.db_path) as conn:
            conn.execute("BEGIN IMMEDIATE")
            try:
                conn.execute("DELETE FROM outbound_attempts WHERE created_at < ?", (cutoff,))
                count = conn.execute("SELECT COUNT(*) FROM outbound_attempts WHERE created_at >= ?", (cutoff,)).fetchone()[0]
                if count >= settings.poseidon_outbound_msg_rate_limit:
                    record_limit_alert(conn, 'outbound', now)
                    conn.commit()
                    raise GuardrailRateLimitError("Outbound message limit reached; delivery is paused for this hour")
                conn.execute("INSERT INTO outbound_attempts(channel,created_at) VALUES (?,?)", (channel, now.isoformat()))
                conn.commit()
            except BaseException:
                conn.rollback()
                raise


guardrail_store = GuardrailStore()
