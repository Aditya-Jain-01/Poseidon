"""Copy fictional Brain notes into the configured local vault without overwriting data."""
from __future__ import annotations

import shutil
import sys
from pathlib import Path


BACKEND_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_ROOT))

from app.config import settings  # noqa: E402


def main() -> None:
    source = BACKEND_ROOT / "examples" / "brain" / "raw"
    destination = settings.brain_vault_path / "raw" / "demo"
    if destination.is_symlink():
        raise SystemExit(f"Refusing to seed through a symlink: {destination}")
    destination.mkdir(parents=True, exist_ok=True)
    copied = skipped = 0
    for note in sorted(source.glob("*.md")):
        target = destination / note.name
        if target.exists() or target.is_symlink():
            skipped += 1
            continue
        shutil.copyfile(note, target)
        copied += 1
    print(f"Demo Brain notes: {copied} copied, {skipped} already present; vault: {settings.brain_vault_path}")
    print("Scan raw sources in the Brain view to add them to the graph.")


if __name__ == "__main__":
    main()
