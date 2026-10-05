"""Notes and Reminders Tool — guarded personal task management.

Writes pass through NoteGuard for injection detection and prompt leakage
before committing to local JSON storage. Suspicious notes pause for operator approval.
"""

from __future__ import annotations

from typing import Any
from uuid import uuid4
from ._storage import read_json, write_json
from app.security.note_guard import NoteGuard, SuspiciousNoteError


def notes_reminders_read(query: str | None = "") -> dict[str, Any]:
    """Search notes and reminders matching an optional case-insensitive substring."""
    data = read_json("notes.json", {"notes": [], "reminders": []})
    query = (query or "").lower().strip()
    result = {key: [item for item in data.get(key, []) if not query or query in str(item).lower()] for key in ("notes", "reminders")}
    return result


def notes_reminders_create(kind: str, text: str, due_at: str | None = None, _operator_approved: bool = False) -> dict[str, Any]:
    """Create a note or reminder, subject to NoteGuard security validation and storage quotas."""
    if kind not in {"note", "reminder"}:
        raise ValueError("kind must be note or reminder")

    verdict = NoteGuard.inspect(text)

    if verdict.verdict == "reject":
        reason = "; ".join(verdict.reasons)
        raise ValueError(f"Note creation blocked by security policy: {reason}")

    if verdict.verdict == "suspicious" and not _operator_approved:
        raise SuspiciousNoteError(
            kind=kind,
            text=text,
            due_at=due_at,
            reasons=verdict.reasons,
        )

    data = read_json("notes.json", {"notes": [], "reminders": []})
    NoteGuard.check_storage_capacity(data)

    item = {"id": str(uuid4()), "text": text}
    if due_at:
        item["due_at"] = due_at
    key = "notes" if kind == "note" else "reminders"
    data.setdefault(key, []).append(item)
    write_json("notes.json", data)
    return {"created": item, "kind": kind}


def notes_reminders_delete(kind: str, item_id: str) -> dict[str, Any]:
    """Delete a note or reminder by its unique UUID."""
    key = "notes" if kind == "note" else "reminders" if kind == "reminder" else None
    if key is None:
        raise ValueError("kind must be note or reminder")
    data = read_json("notes.json", {"notes": [], "reminders": []})
    old = data.get(key, [])
    data[key] = [item for item in old if item.get("id") != item_id]
    if len(old) == len(data[key]):
        raise ValueError(f"{kind} not found")
    write_json("notes.json", data)
    return {"deleted": item_id, "kind": kind}

