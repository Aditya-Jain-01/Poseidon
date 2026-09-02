from __future__ import annotations

from typing import Any
from uuid import uuid4
from ._storage import read_json, write_json


def notes_reminders_read(query: str = "") -> dict[str, Any]:
    data = read_json("notes.json", {"notes": [], "reminders": []})
    query = query.lower().strip()
    result = {key: [item for item in data.get(key, []) if not query or query in str(item).lower()] for key in ("notes", "reminders")}
    return result


def notes_reminders_create(kind: str, text: str, due_at: str | None = None) -> dict[str, Any]:
    if kind not in {"note", "reminder"}:
        raise ValueError("kind must be note or reminder")
    data = read_json("notes.json", {"notes": [], "reminders": []})
    item = {"id": str(uuid4()), "text": text}
    if due_at:
        item["due_at"] = due_at
    key = "notes" if kind == "note" else "reminders"
    data.setdefault(key, []).append(item)
    write_json("notes.json", data)
    return {"created": item, "kind": kind}


def notes_reminders_delete(kind: str, item_id: str) -> dict[str, Any]:
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
