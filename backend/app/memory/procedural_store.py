"""Procedural Memory Store — "how to act" playbooks and skill instructions.

Sprint 2 (Person B — Stage 3):
- Loads *.SKILL.md files from the `memory-store/skills/` directory.
- Direct load by name/task match (not searched via embedding or FTS).
- Each SKILL.md file has YAML frontmatter (name, triggers, description)
  followed by markdown instructions.
- The agent can write new skills via `skill_manage` once the Summarizer
  notices a repeatable pattern.
"""

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from app.config import settings


@dataclass
class Skill:
    """A single procedural skill parsed from a *.SKILL.md file."""

    name: str
    description: str
    triggers: list[str]
    content: str
    file_path: Path

    def matches(self, query: str) -> bool:
        """Check if a query matches any of this skill's trigger keywords.

        Uses case-insensitive substring matching against trigger phrases.
        """
        query_lower = query.lower()
        for trigger in self.triggers:
            if trigger.lower() in query_lower:
                return True
        return False

    def to_prompt_block(self) -> str:
        """Format this skill as a block suitable for injection into Working Memory."""
        return (
            f"### Skill: {self.name}\n"
            f"_{self.description}_\n\n"
            f"{self.content}"
        )

    def __str__(self) -> str:
        return self.to_prompt_block()


def _parse_frontmatter(text: str) -> tuple[dict[str, Any], str]:
    """Parse YAML-like frontmatter from a SKILL.md file.

    Expects format:
    ---
    name: Skill Name
    description: What this skill does
    triggers: [keyword1, keyword2, keyword3]
    ---
    ... markdown content ...

    Returns (frontmatter_dict, body_content).
    """
    match = re.match(r"^---\s*\n(.*?)\n---\s*\n(.*)", text, re.DOTALL)
    if not match:
        return {}, text

    fm_text = match.group(1)
    body = match.group(2).strip()

    fm: dict[str, Any] = {}
    for line in fm_text.strip().split("\n"):
        line = line.strip()
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        key = key.strip().lower()
        value = value.strip()

        # Parse list values like [item1, item2, item3]
        if value.startswith("[") and value.endswith("]"):
            items = [item.strip().strip("\"'") for item in value[1:-1].split(",")]
            fm[key] = [item for item in items if item]
        else:
            fm[key] = value.strip("\"'")

    return fm, body


class ProceduralStore:
    """Loads and matches procedural skills from *.SKILL.md files.

    Skills are flat markdown files with YAML frontmatter defining trigger
    keywords. When a user query matches a skill's triggers, the skill
    instructions are injected into Working Memory so the agent knows
    "how to act" for that specific task.
    """

    def __init__(self, skills_dir: Path | str | None = None) -> None:
        if skills_dir is None:
            db_path = Path(settings.poseidon_db_path)
            self.skills_dir = db_path.parent / "skills"
        else:
            self.skills_dir = Path(skills_dir)

        self._skills: list[Skill] = []
        self.reload()

    def reload(self) -> None:
        """Scan the skills directory and load all *.SKILL.md files."""
        self._skills = []

        if not self.skills_dir.exists():
            self.skills_dir.mkdir(parents=True, exist_ok=True)
            return

        for skill_file in sorted(self.skills_dir.glob("*.SKILL.md")):
            try:
                skill = self._load_skill_file(skill_file)
                if skill:
                    self._skills.append(skill)
            except Exception as e:
                # Log but don't crash — a broken skill file shouldn't kill the agent
                print(f"[ProceduralStore] Warning: failed to load {skill_file.name}: {e}")

    def _load_skill_file(self, file_path: Path) -> Skill | None:
        """Parse a single SKILL.md file into a Skill object."""
        text = file_path.read_text(encoding="utf-8")
        fm, body = _parse_frontmatter(text)

        name = fm.get("name", file_path.stem.replace(".SKILL", ""))
        description = fm.get("description", "")
        triggers = fm.get("triggers", [])

        if isinstance(triggers, str):
            triggers = [triggers]

        if not body.strip():
            return None

        return Skill(
            name=name,
            description=description,
            triggers=triggers,
            content=body,
            file_path=file_path,
        )

    def retrieve(self, task_query: str) -> list[Skill]:
        """Find all skills whose triggers match the given query.

        This is the main interface that Working Memory calls.
        Returns matching skills (may be empty).
        """
        return [skill for skill in self._skills if skill.matches(task_query)]

    def get_all_skills(self) -> list[Skill]:
        """Return all loaded skills (for the dashboard Tools/Memory tab)."""
        return list(self._skills)

    def get_skill_by_name(self, name: str) -> Skill | None:
        """Look up a specific skill by its name."""
        for skill in self._skills:
            if skill.name.lower() == name.lower():
                return skill
        return None

    def create_skill(
        self,
        name: str,
        description: str,
        triggers: list[str],
        content: str,
    ) -> Path:
        """Write a new SKILL.md file and reload the store.

        Called by the Summarizer Agent when it discovers a repeatable pattern,
        or by the `skill_manage` tool.
        """
        safe_name = re.sub(r"[^\w\-]", "_", name.lower())
        file_path = self.skills_dir / f"{safe_name}.SKILL.md"

        trigger_str = ", ".join(triggers)
        skill_text = (
            f"---\n"
            f"name: {name}\n"
            f"description: {description}\n"
            f"triggers: [{trigger_str}]\n"
            f"---\n\n"
            f"{content}\n"
        )

        self.skills_dir.mkdir(parents=True, exist_ok=True)
        file_path.write_text(skill_text, encoding="utf-8")

        # Reload to pick up the new skill
        self.reload()
        return file_path

    def count(self) -> int:
        """Return the number of loaded skills."""
        return len(self._skills)


# App-wide singleton instance
procedural_store = ProceduralStore()
