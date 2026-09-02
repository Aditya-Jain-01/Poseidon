"""Soul Store — Drop-in *.soul.md agent persona and configuration subsystem.

Sprint 4 (Person A):
- Scans `memory-store/agents/*.soul.md` for prebuilt and custom agent definitions.
- Parses YAML frontmatter (tools, model presets, routing signals) and markdown personality.
- Manages agent lifecycle: load, create (max 2 custom), update, delete, system prompt generation.
"""

from __future__ import annotations

import os
import re
from pathlib import Path
from typing import Any

from app.config import settings

PREBUILT_IDS = {"octavious", "nereus", "kraken"}
MAX_CUSTOM_AGENTS = 2


def _get_agents_dir() -> Path:
    """Resolve the directory containing *.soul.md files."""
    if hasattr(settings, "agents_dir") and settings.agents_dir:
        path = Path(settings.agents_dir)
    else:
        path = Path(settings.poseidon_db_path).parent / "agents"
    path.mkdir(parents=True, exist_ok=True)
    return path


def _parse_frontmatter(text: str) -> tuple[dict[str, Any], str]:
    """Extract and parse YAML frontmatter and markdown body from soul file.

    Format:
    ---
    display_name: Name
    tools:
      - tool1
    ---
    # Markdown Personality Body
    """
    match = re.match(r"^---\s*\r?\n(.*?)\r?\n---\s*\r?\n(.*)$", text, re.DOTALL)
    if not match:
        return {}, text.strip()

    fm_raw = match.group(1)
    body = match.group(2).strip()

    # Try standard yaml if available
    try:
        import yaml  # type: ignore

        parsed = yaml.safe_load(fm_raw)
        if isinstance(parsed, dict):
            return parsed, body
    except Exception:
        pass

    # Fallback YAML-like parser for zero-dependency resilience
    fm: dict[str, Any] = {}
    current_list_key: str | None = None

    for line in fm_raw.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue

        # Handle list item: "- item"
        if stripped.startswith("- "):
            item_val = stripped[2:].strip().strip("\"'")
            if current_list_key:
                if not isinstance(fm.get(current_list_key), list):
                    fm[current_list_key] = []
                fm[current_list_key].append(item_val)
            continue

        # Reset list key on normal key: value
        current_list_key = None
        if ":" in stripped:
            key, val = stripped.split(":", 1)
            key = key.strip()
            val = val.strip()

            if val.startswith("[") and val.endswith("]"):
                items = [x.strip().strip("\"'") for x in val[1:-1].split(",") if x.strip()]
                fm[key] = items
            elif not val:
                # Potential start of indented list
                current_list_key = key
                fm[key] = []
            elif val.lower() == "true":
                fm[key] = True
            elif val.lower() == "false":
                fm[key] = False
            else:
                fm[key] = val.strip("\"'")

    return fm, body


def _dump_frontmatter(metadata: dict[str, Any], body: str) -> str:
    """Serialize metadata and body into a formatted .soul.md string."""
    try:
        import yaml  # type: ignore

        fm_yaml = yaml.dump(metadata, sort_keys=False, default_flow_style=False).strip()
        return f"---\n{fm_yaml}\n---\n\n{body}\n"
    except Exception:
        pass

    # Fallback serializer
    lines = ["---"]
    for k, v in metadata.items():
        if isinstance(v, list):
            lines.append(f"{k}:")
            for item in v:
                lines.append(f"  - {item}")
        elif isinstance(v, bool):
            lines.append(f"{k}: {'true' if v else 'false'}")
        else:
            lines.append(f"{k}: {v}")
    lines.append("---")
    lines.append("")
    lines.append(body.strip())
    lines.append("")
    return "\n".join(lines)


class SoulStore:
    """Manages drop-in agent souls (*.soul.md)."""

    def __init__(self) -> None:
        self._cache: dict[str, dict[str, Any]] = {}
        self._loaded = False

    def load_all_agents(self, force_reload: bool = False) -> list[dict[str, Any]]:
        """Load and cache all agents from the memory-store/agents directory."""
        if self._loaded and not force_reload:
            return list(self._cache.values())

        agents_dir = _get_agents_dir()
        discovered: dict[str, dict[str, Any]] = {}

        for file_path in sorted(agents_dir.glob("*.soul.md")):
            agent_id = file_path.name.replace(".soul.md", "").lower()
            try:
                content = file_path.read_text(encoding="utf-8")
                fm, body = _parse_frontmatter(content)

                is_prebuilt = agent_id in PREBUILT_IDS or bool(fm.get("is_prebuilt", False))
                discovered[agent_id] = {
                    "id": agent_id,
                    "display_name": fm.get("display_name", agent_id.capitalize()),
                    "avatar": str(fm.get("avatar", agent_id[0].upper())),
                    "color": fm.get("color", "#39ff14" if agent_id == "octavious" else ("#00bfff" if agent_id == "nereus" else "#ff4500")),
                    "role": fm.get("role", "Specialized Agent"),
                    "description": fm.get("description", ""),
                    "personality": body,
                    "model_preset": fm.get("model_preset", "cloud_free"),
                    "tools": list(fm.get("tools", [])),
                    "routing_signals": list(fm.get("routing_signals", [])),
                    "is_prebuilt": is_prebuilt,
                    "file_path": str(file_path),
                }
            except Exception as e:
                print(f"[SoulStore] Error loading {file_path.name}: {e}")

        # Order: prebuilt agents first in standard order, then custom agents alphabetically
        ordered: dict[str, dict[str, Any]] = {}
        for pid in ["octavious", "nereus", "kraken"]:
            if pid in discovered:
                ordered[pid] = discovered.pop(pid)
        for cid, data in sorted(discovered.items()):
            ordered[cid] = data

        self._cache = ordered
        self._loaded = True
        return list(self._cache.values())

    def get_agent(self, agent_id: str) -> dict[str, Any] | None:
        """Lookup an agent by ID."""
        if not self._loaded:
            self.load_all_agents()
        return self._cache.get(agent_id.lower())

    def get_custom_count(self) -> int:
        """Return the number of user-created custom agents."""
        agents = self.load_all_agents()
        return sum(1 for a in agents if not a.get("is_prebuilt"))

    def create_agent(self, config: dict[str, Any]) -> dict[str, Any]:
        """Create a new custom agent by generating a *.soul.md file.

        Enforces a hard maximum of 2 custom agents.
        """
        raw_id = config.get("id") or config.get("display_name", "custom_agent")
        agent_id = re.sub(r"[^a-z0-9_]+", "_", raw_id.lower()).strip("_")

        if not agent_id:
            agent_id = "agent_custom"

        if agent_id in PREBUILT_IDS:
            raise ValueError(f"Agent ID '{agent_id}' is reserved for prebuilt agents.")

        if self.get_agent(agent_id):
            raise ValueError(f"Agent with ID '{agent_id}' already exists.")

        if self.get_custom_count() >= MAX_CUSTOM_AGENTS:
            raise ValueError(f"Maximum limit of {MAX_CUSTOM_AGENTS} custom agents reached.")

        metadata = {
            "display_name": config.get("display_name", agent_id.capitalize()),
            "avatar": config.get("avatar", agent_id[0].upper())[:1],
            "color": config.get("color", "#a855f7"),
            "role": config.get("role", "Specialized Agent"),
            "description": config.get("description", ""),
            "model_preset": config.get("model_preset", "cloud_free"),
            "tools": list(config.get("tools", [])),
            "routing_signals": list(config.get("routing_signals", [agent_id])),
            "is_prebuilt": False,
        }

        personality = config.get("personality", f"# {metadata['display_name']}\n\nYou are a specialized agent.").strip()
        file_content = _dump_frontmatter(metadata, personality)

        target_file = _get_agents_dir() / f"{agent_id}.soul.md"
        target_file.write_text(file_content, encoding="utf-8")

        self.load_all_agents(force_reload=True)
        created = self.get_agent(agent_id)
        if not created:
            raise RuntimeError(f"Failed to load newly created agent '{agent_id}'.")
        return created

    def update_agent(self, agent_id: str, updates: dict[str, Any]) -> dict[str, Any]:
        """Update an existing agent's configuration or personality."""
        existing = self.get_agent(agent_id)
        if not existing:
            raise KeyError(f"Agent '{agent_id}' not found.")

        file_path = Path(existing["file_path"])
        metadata = {
            "display_name": updates.get("display_name", existing["display_name"]),
            "avatar": str(updates.get("avatar", existing["avatar"]))[:1],
            "color": updates.get("color", existing["color"]),
            "role": updates.get("role", existing["role"]),
            "description": updates.get("description", existing["description"]),
            "model_preset": updates.get("model_preset", existing["model_preset"]),
            "tools": list(updates.get("tools", existing["tools"])),
            "routing_signals": list(updates.get("routing_signals", existing["routing_signals"])),
            "is_prebuilt": existing["is_prebuilt"],  # Cannot change prebuilt status
        }

        personality = updates.get("personality", existing["personality"]).strip()
        file_content = _dump_frontmatter(metadata, personality)
        file_path.write_text(file_content, encoding="utf-8")

        self.load_all_agents(force_reload=True)
        updated = self.get_agent(agent_id)
        if not updated:
            raise RuntimeError(f"Failed to reload agent '{agent_id}' after update.")
        return updated

    def delete_agent(self, agent_id: str) -> bool:
        """Delete a custom agent. Rejects deletion of prebuilt agents."""
        existing = self.get_agent(agent_id)
        if not existing:
            raise KeyError(f"Agent '{agent_id}' not found.")

        if existing.get("is_prebuilt"):
            raise ValueError(f"Cannot delete prebuilt agent '{agent_id}'. You may edit it instead.")

        file_path = Path(existing["file_path"])
        if file_path.exists():
            file_path.unlink()

        self.load_all_agents(force_reload=True)
        return True

    def build_system_prompt(self, agent_id: str) -> str:
        """Build the complete system prompt for a specific agent.

        Combines the agent's personality with global behavioral guidelines.
        """
        agent = self.get_agent(agent_id)
        if not agent:
            agent = self.get_agent("octavious")

        if not agent:
            return "You are Poseidon, a personal AI assistant. Be concise and direct."

        personality = agent.get("personality", "").strip()
        return personality

    def get_routing_signals(self) -> dict[str, str]:
        """Aggregate keyword routing signals mapped to agent IDs.

        Returns a dictionary mapping lowercase trigger keyword -> agent_id.
        """
        signals: dict[str, str] = {}
        for agent in self.load_all_agents():
            aid = agent["id"]
            for sig in agent.get("routing_signals", []):
                cleaned = sig.strip().lower()
                if cleaned:
                    signals[cleaned] = aid
        return signals

    def reload(self) -> list[dict[str, Any]]:
        """Force re-scan and reload of all agent souls."""
        return self.load_all_agents(force_reload=True)


# Global singleton
soul_store = SoulStore()
