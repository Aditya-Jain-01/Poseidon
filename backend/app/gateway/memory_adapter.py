"""Memory API router — exposes HTTP endpoints for reading and managing persistent memory.

Sprint 2 (Person C — Stage 6):
- GET /memory/semantic — read semantic facts with optional category/query filter.
- GET /memory/episodic — read episodic event timeline and history.
- GET /memory/procedural — list procedural skill playbooks (*.SKILL.md).
- POST /memory/consolidate — trigger memory consolidation on demand.
- GET /memory/status — get memory statistics and consolidation threshold progress.
"""

from typing import Any
from fastapi import APIRouter, Query
from pydantic import BaseModel, Field

from app.memory.semantic_store import semantic_store
from app.memory.episodic_store import episodic_store
from app.memory.procedural_store import procedural_store
from app.memory.consolidation import check_and_trigger_consolidation, get_consolidation_status

router = APIRouter(prefix="/memory", tags=["Memory"])


class ConsolidateRequest(BaseModel):
    user_id: str = Field(default="local_user", description="User ID to consolidate")
    force: bool = Field(default=True, description="Force consolidation even if threshold not reached")


@router.get("/semantic")
async def get_semantic_memory(
    user_id: str = Query(default="local_user", description="User ID"),
    category: str | None = Query(default=None, description="Optional category filter (preference, profile, relationship, general)"),
    query: str | None = Query(default=None, description="Optional search query keyword"),
    limit: int = Query(default=50, ge=1, le=200, description="Max facts to return"),
) -> dict[str, Any]:
    """Retrieve active semantic facts for a user."""
    if query:
        facts = semantic_store.retrieve(user_id=user_id, query=query, limit=limit)
    else:
        facts = semantic_store.get_all_facts(user_id=user_id, category=category)[:limit]

    return {
        "user_id": user_id,
        "count": len(facts),
        "total_facts": semantic_store.count(user_id=user_id),
        "facts": facts,
    }


@router.get("/episodic")
async def get_episodic_memory(
    user_id: str = Query(default="local_user", description="User ID"),
    since: str | None = Query(default=None, description="ISO timestamp to filter events since"),
    query: str | None = Query(default=None, description="Optional keyword search query"),
    limit: int = Query(default=50, ge=1, le=200, description="Max events to return"),
) -> dict[str, Any]:
    """Retrieve chronological episodic events for a user."""
    if query:
        events = episodic_store.search_relevant(user_id=user_id, query=query, limit=limit)
    else:
        events = episodic_store.get_recent(user_id=user_id, limit=limit, since=since)

    unconsolidated_count = episodic_store.count_unconsolidated(user_id=user_id)

    return {
        "user_id": user_id,
        "count": len(events),
        "unconsolidated_count": unconsolidated_count,
        "events": events,
    }


@router.get("/procedural")
async def get_procedural_memory(
    query: str | None = Query(default=None, description="Optional trigger query to match skills"),
) -> dict[str, Any]:
    """Retrieve loaded procedural skills."""
    if query:
        skills = procedural_store.retrieve(task_query=query)
    else:
        skills = procedural_store.get_all_skills()

    formatted_skills = [
        {
            "name": s.name,
            "description": s.description,
            "triggers": s.triggers,
            "content": s.content,
            "file": s.file_path.name,
        }
        for s in skills
    ]

    return {
        "count": len(formatted_skills),
        "skills": formatted_skills,
    }


@router.post("/consolidate")
async def trigger_consolidation_endpoint(
    req: ConsolidateRequest | None = None,
) -> dict[str, Any]:
    """Trigger memory consolidation for unconsolidated episodic entries."""
    user_id = req.user_id if req else "local_user"
    force = req.force if req else True

    result = await check_and_trigger_consolidation(user_id=user_id, force=force)
    return result


@router.get("/status")
async def get_memory_status(
    user_id: str = Query(default="local_user", description="User ID"),
) -> dict[str, Any]:
    """Get high-level summary of memory stores and consolidation status."""
    consolidation_info = get_consolidation_status(user_id=user_id)
    return {
        "user_id": user_id,
        "semantic_facts_count": semantic_store.count(user_id=user_id),
        "procedural_skills_count": procedural_store.count(),
        "consolidation": consolidation_info,
    }
