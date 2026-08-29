"""Consolidation Manager — triggers memory distillation after N new chats.

Sprint 2 (Person C — Stage 5):
- Enforces the "only after N new chats" threshold rule (spec source of truth).
- Prevents expensive LLM summarization on every single turn.
- Pulls unconsolidated episodic entries and hands them to the Summarizer Agent.
- Provides programmatic and on-demand consolidation triggers.
"""

from typing import Any
import sqlite3

from app.config import settings
from app.memory.episodic_store import episodic_store
from app.agents import summarizer_agent


def get_unconsolidated_events(user_id: str, limit: int | None = None) -> list[dict[str, Any]]:
    """Retrieve all unconsolidated episodic events for a specific user."""
    query = """
        SELECT id, user_id, channel, run_id, role, content, created_at, metadata, consolidated
        FROM episodic_events
        WHERE user_id = ? AND consolidated = 0
        ORDER BY created_at ASC, id ASC
    """
    params: list[Any] = [user_id]
    if limit:
        query += " LIMIT ?"
        params.append(limit)

    with episodic_store._get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(query, params)
        return [dict(row) for row in cursor.fetchall()]


def get_consolidation_status(user_id: str) -> dict[str, Any]:
    """Get current consolidation progress for a user."""
    threshold = settings.poseidon_consolidation_threshold
    unconsolidated_count = episodic_store.count_unconsolidated(user_id=user_id)
    return {
        "user_id": user_id,
        "unconsolidated_count": unconsolidated_count,
        "threshold": threshold,
        "ready": unconsolidated_count >= threshold,
        "progress_percent": min(100, int((unconsolidated_count / max(1, threshold)) * 100)),
        "message": f"{unconsolidated_count}/{threshold} chats until next automatic consolidation",
    }


async def check_and_trigger_consolidation(
    user_id: str,
    force: bool = False,
    limit: int | None = None,
) -> dict[str, Any]:
    """Check if consolidation threshold is met, or run immediately if forced.

    If threshold is reached or force=True:
    1. Fetches all unconsolidated episodic records for this user.
    2. Passes them to Summarizer Agent to extract facts & skills.
    3. Saves extracted facts to SemanticStore and skills to ProceduralStore.
    4. Marks episodic records as consolidated.
    """
    threshold = settings.poseidon_consolidation_threshold
    unconsolidated_count = episodic_store.count_unconsolidated(user_id=user_id)

    if not force and unconsolidated_count < threshold:
        return {
            "consolidated": False,
            "reason": "threshold_not_reached",
            "unconsolidated_count": unconsolidated_count,
            "threshold": threshold,
            "message": f"{unconsolidated_count}/{threshold} chats until next automatic consolidation",
        }

    # Fetch unconsolidated records
    events = get_unconsolidated_events(user_id=user_id, limit=limit)
    if not events:
        return {
            "consolidated": False,
            "reason": "no_events_to_consolidate",
            "unconsolidated_count": 0,
            "threshold": threshold,
            "message": "No unconsolidated events present",
        }

    # Distill and persist
    result = await summarizer_agent.summarize_and_consolidate(user_id=user_id, events=events)
    remaining_unconsolidated = episodic_store.count_unconsolidated(user_id=user_id)

    return {
        "consolidated": True,
        "forced": force,
        "events_processed": result.get("events_processed", 0),
        "facts_added": result.get("facts_added", 0),
        "skills_added": result.get("skills_added", 0),
        "fact_ids": result.get("fact_ids", []),
        "skills": result.get("skills", []),
        "unconsolidated_count": remaining_unconsolidated,
        "threshold": threshold,
        "message": f"Successfully consolidated {result.get('events_processed', 0)} events into {result.get('facts_added', 0)} facts.",
    }
