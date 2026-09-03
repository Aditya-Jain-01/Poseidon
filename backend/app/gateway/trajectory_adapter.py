"""Trajectory REST API adapter — Sprint 4 (Person C).

Exposes execution telemetry recorded by TrajectoryStore per run_id.
"""

from __future__ import annotations

from typing import Any
from fastapi import APIRouter
from app.orchestration.trajectory import trajectory_store

router = APIRouter(tags=["Trajectory"])


@router.get("/runs/{run_id}/trajectory")
async def get_run_trajectory(run_id: str) -> dict[str, Any]:
    """Retrieve granular recorded execution steps for a specific run_id."""
    steps = trajectory_store.get(run_id)
    return {
        "run_id": run_id,
        "count": len(steps),
        "steps": steps,
    }
