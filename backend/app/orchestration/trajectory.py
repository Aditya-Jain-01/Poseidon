"""Execution trajectory recorder with secret scrubbing, keyed by run id."""
from __future__ import annotations
import re
from datetime import datetime, timezone
from collections import defaultdict
from typing import Any


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
    def __init__(self) -> None:
        self._runs: dict[str, list[dict[str, Any]]] = defaultdict(list)

    def record(self, run_id: str, step_type: str, **fields: Any) -> dict[str, Any]:
        scrubbed = {k: _scrub(v) for k, v in fields.items()}
        step = {"step_type": step_type, "timestamp": datetime.now(timezone.utc).isoformat(), **scrubbed}
        self._runs[run_id].append(step)
        return step

    def get(self, run_id: str) -> list[dict[str, Any]]:
        return list(self._runs.get(run_id, []))


trajectory_store = TrajectoryStore()
