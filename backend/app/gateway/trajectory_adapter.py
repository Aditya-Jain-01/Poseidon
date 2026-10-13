"""Trajectory and Audit/Gateway REST API adapter.

Exposes execution telemetry recorded by TrajectoryStore and durable ledger events.
"""

from __future__ import annotations

from typing import Any
from fastapi import APIRouter, Depends, Query
from app.orchestration.trajectory import trajectory_store
from app.security.audit import audit_service
from app.models import ActorContext
from app.security.identity import resolve_actor

router = APIRouter(tags=["Trajectory", "Audit", "Gateway"])


@router.get("/runs/{run_id}/trajectory")
async def get_run_trajectory(run_id: str) -> dict[str, Any]:
    """Retrieve granular recorded execution steps for a specific run_id."""
    steps = trajectory_store.get(run_id)
    return {
        "run_id": run_id,
        "count": len(steps),
        "steps": steps,
    }


@router.get("/gateway/events")
@router.get("/audit/events")
async def get_gateway_events(
    channel: str | None = Query(None),
    run_id: str | None = Query(None),
    direction: str | None = Query(None),
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    actor: ActorContext = Depends(resolve_actor),
) -> dict[str, Any]:
    """Retrieve durable gateway/audit events from the SQLite ledger."""
    events = audit_service.query_events(
        owner_id=actor.owner_id,
        channel=channel,
        run_id=run_id,
        direction=direction,
        limit=limit,
        offset=offset,
    )
    return {
        "count": len(events),
        "events": events,
    }


@router.delete("/audit/events")
async def delete_audit_events(
    actor: ActorContext = Depends(resolve_actor),
) -> dict[str, Any]:
    """Owner-initiated audit event deletion."""
    deleted_count = audit_service.delete_events(actor.owner_id)
    return {
        "status": "deleted",
        "count": deleted_count,
    }
