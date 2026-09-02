"""In-memory execution trajectory recorder, keyed by run id."""
from __future__ import annotations
from datetime import datetime, timezone
from collections import defaultdict
from typing import Any


class TrajectoryStore:
    def __init__(self) -> None:
        self._runs: dict[str, list[dict[str, Any]]] = defaultdict(list)

    def record(self, run_id: str, step_type: str, **fields: Any) -> dict[str, Any]:
        step = {"step_type": step_type, "timestamp": datetime.now(timezone.utc).isoformat(), **fields}
        self._runs[run_id].append(step)
        return step

    def get(self, run_id: str) -> list[dict[str, Any]]:
        return list(self._runs.get(run_id, []))


trajectory_store = TrajectoryStore()
