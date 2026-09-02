from __future__ import annotations

from typing import Any
from uuid import uuid4
from ._storage import read_json, write_json


def crm_read(query: str = "") -> dict[str, Any]:
    contacts = read_json("crm_data.json", {"contacts": []}).get("contacts", [])
    query = query.lower().strip()
    matches = [c for c in contacts if not query or query in str(c).lower()]
    return {"contacts": matches, "count": len(matches)}


def crm_write(action: str, contact: dict[str, Any] | None = None, contact_id: str | None = None) -> dict[str, Any]:
    data = read_json("crm_data.json", {"contacts": []})
    contacts = data.setdefault("contacts", [])
    action = action.lower()
    if action == "create":
        record = dict(contact or {})
        record.setdefault("id", str(uuid4()))
        contacts.append(record)
        result = {"created": record}
    elif action == "update" and contact_id:
        record = next((item for item in contacts if item.get("id") == contact_id), None)
        if record is None:
            raise ValueError("Contact not found")
        record.update(contact or {})
        result = {"updated": record}
    elif action == "delete" and contact_id:
        before = len(contacts)
        data["contacts"] = [item for item in contacts if item.get("id") != contact_id]
        if len(data["contacts"]) == before:
            raise ValueError("Contact not found")
        result = {"deleted": contact_id}
    else:
        raise ValueError("crm_write action must be create, update, or delete with required fields")
    write_json("crm_data.json", data)
    return result
