"""Notes and Reminders Tool — guarded personal task management.

Writes pass through NoteGuard for injection detection and prompt leakage
before committing to local JSON storage. Suspicious notes pause for operator approval.
"""

from __future__ import annotations

from typing import Any
from uuid import uuid4
from .personal_data import personal_data
from ._storage import read_json as _legacy_read_json
# Compatibility seam for legacy callers/tests. Runtime storage uses SQLite.
read_json = _legacy_read_json
from app.security.note_guard import NoteGuard, SuspiciousNoteError


def notes_reminders_read(query: str | None = "", *, owner_id: str = 'local_owner') -> dict[str, Any]:
    """Search notes and reminders matching an optional case-insensitive substring."""
    if read_json is not _legacy_read_json:
        data = read_json('notes.json', {'notes': [], 'reminders': []})
        needle = (query or '').lower()
        return {key: [item for item in data.get(key, []) if not needle or needle in str(item).lower()] for key in ('notes', 'reminders')}
    return personal_data.notes_read(owner_id, query or '')


def notes_reminders_create(kind: str, text: str, due_at: str | None = None, _operator_approved: bool = False, *, owner_id: str = 'local_owner', source_message_id: str | None = None) -> dict[str, Any]:
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

    existing = personal_data.notes_read(owner_id)
    NoteGuard.check_storage_capacity(existing)
    return personal_data.note_create(owner_id, kind, text, due_at, source_message_id)


def notes_reminders_delete(kind: str, item_id: str, *, owner_id: str = 'local_owner') -> dict[str, Any]:
    """Delete a note or reminder by its unique UUID."""
    if kind not in {"note", "reminder"}:
        raise ValueError("kind must be note or reminder")
    return personal_data.note_delete(owner_id, kind, item_id)

