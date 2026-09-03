"""Agent Management & LLM Settings REST API — Sprint 4 (Person C).

Provides endpoints for:
- Agent CRUD (list, get, create, update, delete, reload)
- LLM provider configuration per agent (get, update, health-check)
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.soul import soul_store
from app.llm_providers import llm_provider


# ── Request / Response Models ──────────────────────────────────────

class CreateAgentRequest(BaseModel):
    """Payload for creating a new custom agent."""
    display_name: str
    avatar: str = Field(default="A", max_length=1)
    color: str = Field(default="#a855f7")
    role: str = Field(default="Specialized Agent")
    description: str = Field(default="")
    personality: str = Field(default="")
    model_preset: str = Field(default="cloud_free")
    tools: list[str] = Field(default_factory=list)
    routing_signals: list[str] = Field(default_factory=list)


class UpdateAgentRequest(BaseModel):
    """Payload for updating an existing agent (partial updates supported)."""
    display_name: str | None = None
    avatar: str | None = None
    color: str | None = None
    role: str | None = None
    description: str | None = None
    personality: str | None = None
    model_preset: str | None = None
    tools: list[str] | None = None
    routing_signals: list[str] | None = None


class UpdateLLMRequest(BaseModel):
    """Payload for updating an agent's LLM provider assignment."""
    preset: str | None = None
    base_url: str | None = None
    api_key: str | None = None
    model: str | None = None


# ── Router ─────────────────────────────────────────────────────────

router = APIRouter(tags=["Agents & Settings"])


# ── Agent CRUD ─────────────────────────────────────────────────────

@router.get("/agents")
async def list_agents() -> list[dict[str, Any]]:
    """List all agents (prebuilt + custom) with their full config."""
    return soul_store.load_all_agents()


@router.get("/agents/{agent_id}")
async def get_agent(agent_id: str) -> dict[str, Any]:
    """Get a single agent's full configuration."""
    agent = soul_store.get_agent(agent_id)
    if not agent:
        raise HTTPException(status_code=404, detail=f"Agent '{agent_id}' not found.")
    return agent


@router.post("/agents", status_code=201)
async def create_agent(req: CreateAgentRequest) -> dict[str, Any]:
    """Create a new custom agent. Max 2 custom agents allowed."""
    try:
        config = req.model_dump()
        created = soul_store.create_agent(config)
        return created
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except RuntimeError as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.put("/agents/{agent_id}")
async def update_agent(agent_id: str, req: UpdateAgentRequest) -> dict[str, Any]:
    """Update an existing agent's personality, tools, routing signals, or model preset."""
    updates = {k: v for k, v in req.model_dump().items() if v is not None}
    if not updates:
        raise HTTPException(status_code=400, detail="No update fields provided.")
    try:
        updated = soul_store.update_agent(agent_id, updates)
        return updated
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except RuntimeError as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.delete("/agents/{agent_id}")
async def delete_agent(agent_id: str) -> dict[str, str]:
    """Delete a custom agent. Prebuilt agents cannot be deleted."""
    try:
        soul_store.delete_agent(agent_id)
        return {"status": "deleted", "agent_id": agent_id}
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.post("/agents/reload")
async def reload_agents() -> dict[str, Any]:
    """Force re-scan of the agents directory for new/changed soul files."""
    agents = soul_store.reload()
    return {"status": "reloaded", "count": len(agents), "agents": [a["id"] for a in agents]}


# ── LLM Settings ──────────────────────────────────────────────────

@router.get("/settings/llm")
async def get_llm_settings() -> dict[str, Any]:
    """Get current LLM provider configuration for all agents."""
    return llm_provider.get_all_configs()


@router.put("/settings/llm/{agent_id}")
async def update_llm_settings(agent_id: str, req: UpdateLLMRequest) -> dict[str, Any]:
    """Update an agent's LLM provider (switch between local/cloud/custom)."""
    agent = soul_store.get_agent(agent_id)
    if not agent:
        raise HTTPException(status_code=404, detail=f"Agent '{agent_id}' not found.")

    result = llm_provider.update_provider(
        agent_id=agent_id,
        preset=req.preset,
        base_url=req.base_url,
        api_key=req.api_key,
        model=req.model,
    )
    return result


@router.get("/settings/llm/check/{agent_id}")
async def check_llm_health(agent_id: str) -> dict[str, Any]:
    """Check whether an agent's configured LLM endpoint is reachable."""
    agent = soul_store.get_agent(agent_id)
    if not agent:
        raise HTTPException(status_code=404, detail=f"Agent '{agent_id}' not found.")

    return await llm_provider.check_availability(agent_id)
