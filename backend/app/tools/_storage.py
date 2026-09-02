"""Small, atomic-ish JSON store helpers used by local tools."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from app.config import settings


def store_path(filename: str) -> Path:
    return Path(settings.poseidon_db_path).parent / filename


def read_json(filename: str, default: Any) -> Any:
    path = store_path(filename)
    if not path.exists():
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(default, indent=2), encoding="utf-8")
        return default
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError(f"{filename} contains invalid JSON") from exc


def write_json(filename: str, value: Any) -> None:
    path = store_path(filename)
    path.parent.mkdir(parents=True, exist_ok=True)
    temp_path = path.with_suffix(path.suffix + ".tmp")
    temp_path.write_text(json.dumps(value, indent=2, ensure_ascii=False), encoding="utf-8")
    temp_path.replace(path)
