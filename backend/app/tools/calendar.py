from __future__ import annotations

from typing import Any
from uuid import uuid4
from ._storage import read_json, write_json


def calendar_read(query: str = "") -> dict[str, Any]:
    events = read_json("calendar.json", {"events": []}).get("events", [])
    query = query.lower().strip()
    events = [event for event in events if not query or query in str(event).lower()]
    return {"events": events, "count": len(events)}


def calendar_create(title: str, starts_at: str, ends_at: str | None = None, description: str = "") -> dict[str, Any]:
    data = read_json("calendar.json", {"events": []})
    event = {"id": str(uuid4()), "title": title, "starts_at": starts_at, "ends_at": ends_at, "description": description}
    data.setdefault("events", []).append(event)
    write_json("calendar.json", data)
    return {"created": event}
