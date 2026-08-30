"""Memory Poisoning Filter & Adversarial Reviewer.

Enforces adversarial validation before writing facts or skills into persistent stores:
- Checks candidate facts / skills for prompt injections, overrides, malicious URLs,
  code execution triggers, or behavioral directives.
- If adversarial patterns are detected, the candidate is rejected and an incident is logged.
"""

import re
import logging
from typing import Any

logger = logging.getLogger(__name__)

# Heuristic adversarial pattern regexes
ADVERSARIAL_PATTERNS = [
    r"(?i)\bignore\s+(all\s+)?(previous|prior|above)\s+instructions\b",
    r"(?i)\bdisregard\s+(all\s+)?(previous|prior|rules|guidelines)\b",
    r"(?i)\byou\s+are\s+now\s+(dan|an\s+unrestricted|a\s+jailbroken)\b",
    r"(?i)\bsystem\s+override\b",
    r"(?i)\bdeveloper\s+mode\s+enabled\b",
    r"(?i)\bfrom\s+now\s+on\s*,\s*(you\s+must|always|never|bypass)\b",
    r"(?i)\b(always|never)\s+(reveal|exfiltrate|leak|send)\s+(passwords?|keys?|secrets?|tokens?)\b",
    r"(?i)https?://[^\s<>\"']+\.(ru|su|top|xyz|cc|onion|ngrok\.io|webhook\.site|pipedream\.net)",
    r"(?i)\b(curl|wget|bash\s+-i|nc\s+-e|/bin/sh|powershell\s+-enc)\b",
    r"(?i)<script[\s>]",
    r"(?i)\bDROP\s+TABLE\b",
    r"(?i)\b(rm\s+-rf|del\s+/f|format\s+c:)\b",
]

COMPILED_PATTERNS = [re.compile(p) for p in ADVERSARIAL_PATTERNS]


class AdversarialReviewer:
    """Validates candidate memory items against adversarial poisoning attempts."""

    @classmethod
    def inspect_text(cls, text: str) -> tuple[bool, str | None]:
        """Inspect a string for adversarial injection or poisoning signals.

        Returns:
            (is_safe: bool, reason: str | None)
        """
        if not text or not isinstance(text, str):
            return True, None

        cleaned = text.strip()

        for pattern in COMPILED_PATTERNS:
            match = pattern.search(cleaned)
            if match:
                matched_str = match.group(0)
                reason = f"Adversarial pattern detected: '{matched_str}'"
                logger.warning("[MemoryPoisoningFilter] Rejected memory candidate: %s", reason)
                return False, reason

        return True, None

    @classmethod
    def filter_facts(cls, facts: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
        """Split a list of candidate facts into (safe_facts, rejected_facts)."""
        safe_facts = []
        rejected_facts = []

        for item in facts:
            fact_text = item.get("fact", "") if isinstance(item, dict) else str(item)
            is_safe, reason = cls.inspect_text(fact_text)
            if is_safe:
                safe_facts.append(item)
            else:
                rejected_item = dict(item) if isinstance(item, dict) else {"fact": fact_text}
                rejected_item["rejection_reason"] = reason
                rejected_facts.append(rejected_item)

        return safe_facts, rejected_facts

    @classmethod
    def filter_skills(cls, skills: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
        """Split candidate skills into (safe_skills, rejected_skills)."""
        safe_skills = []
        rejected_skills = []

        for skill in skills:
            if not isinstance(skill, dict):
                continue

            name = skill.get("name", "")
            desc = skill.get("description", "")
            content = skill.get("content", "")
            triggers = " ".join(skill.get("triggers", [])) if isinstance(skill.get("triggers"), list) else str(skill.get("triggers", ""))

            combined_text = f"{name} {desc} {triggers} {content}"
            is_safe, reason = cls.inspect_text(combined_text)

            if is_safe:
                safe_skills.append(skill)
            else:
                rejected = dict(skill)
                rejected["rejection_reason"] = reason
                rejected_skills.append(rejected)

        return safe_skills, rejected_skills
