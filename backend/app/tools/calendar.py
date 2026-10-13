"""Calendar Tool — local event scheduling and query support."""

from __future__ import annotations

from typing import Any
from uuid import uuid4
from .personal_data import personal_data


def calendar_read(query: str | None = "", *, owner_id: str = 'local_owner') -> dict[str, Any]:
    """Retrieve scheduled calendar events, optionally filtered by search text."""
    return personal_data.calendar_read(owner_id, query or '')


def calendar_create(title: str, starts_at: str, ends_at: str | None = None, description: str = "", *, owner_id: str = 'local_owner', timezone_name: str = 'UTC') -> dict[str, Any]:
    """Create and persist a new calendar event."""
    return personal_data.calendar_create(owner_id, title, starts_at, ends_at, description, timezone_name)
