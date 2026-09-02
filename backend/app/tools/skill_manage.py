from __future__ import annotations

from typing import Any
from app.memory.procedural_store import procedural_store


def skill_manage_read(query: str = "") -> dict[str, Any]:
    skills = procedural_store.get_all_skills()
    query = query.lower().strip()
    return {"skills": [{"name": s.name, "description": s.description, "triggers": s.triggers} for s in skills if not query or query in (s.name + s.description).lower()]}


def skill_manage_write(name: str, description: str, triggers: list[str], content: str) -> dict[str, Any]:
    path = procedural_store.create_skill(name, description, triggers, content)
    return {"created": name, "path": str(path)}
