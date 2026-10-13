"""CRM Tool — manages customer and contact records with approval gating."""

from __future__ import annotations

from typing import Any
from uuid import uuid4
from .personal_data import personal_data
from ._storage import read_json as _legacy_read_json
read_json = _legacy_read_json


def crm_read(query: str | None = "", *, owner_id: str = 'local_owner') -> dict[str, Any]:
    """Retrieve CRM contacts matching an optional substring query."""
    if read_json is not _legacy_read_json:
        contacts = read_json('crm_data.json', {'contacts': []}).get('contacts', [])
        needle = (query or '').lower()
        matches = [row for row in contacts if not needle or needle in str(row).lower()]
        return {'contacts': matches, 'count': len(matches)}
    return personal_data.crm_read(owner_id, query or '')


def crm_write(action: str, contact: dict[str, Any] | None = None, contact_id: str | None = None, *, owner_id: str = 'local_owner') -> dict[str, Any]:
    """Execute create, update, or delete mutations on contacts (classified as approval_required)."""
    return personal_data.crm_write(owner_id, action, contact, contact_id)
