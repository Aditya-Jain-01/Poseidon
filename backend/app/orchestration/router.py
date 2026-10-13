"""Agent router — routes inbound text to an appropriate agent."""
from __future__ import annotations

import re
from typing import Any

from app.orchestration.graph import DEFAULT_PRIMARY_AGENT
from app.soul import soul_store


class UnknownAgentError(ValueError):
    def __init__(self, agent_id: str, available: list[str]):
        super().__init__(f"unknown_agent: {agent_id}; available: {', '.join(available)}")
        self.agent_id, self.available = agent_id, available


def route_request(user_text: str, default_agent: str = DEFAULT_PRIMARY_AGENT, explicit_agent_id: str | None = None) -> str:
    """Resolve explicit API selection, directive, mention, signals, then default.

    Explicit selections never silently fall back: callers can display a useful
    ``unknown_agent`` response rather than pretending a different agent ran.
    """
    available = [a['id'] for a in soul_store.load_all_agents()]
    if explicit_agent_id:
        candidate = explicit_agent_id.lower().strip()
        if candidate not in available:
            raise UnknownAgentError(candidate, available)
        return candidate
    if not user_text:
        return default_agent

    cleaned = user_text.strip()

    if cleaned.startswith("/agent"):
        parts = cleaned.split(maxsplit=2)
        if len(parts) >= 2:
            candidate = parts[1].lower().strip()
            if candidate not in available:
                raise UnknownAgentError(candidate, available)
            return candidate

    if cleaned.startswith("@"):
        first_token = cleaned.split()[0][1:].lower()
        if first_token not in available:
            raise UnknownAgentError(first_token, available)
        return first_token

    lower_text = cleaned.lower()
    signals = soul_store.get_routing_signals()
    for sig, aid in signals.items():
        if sig == "default":
            continue
        if re.search(r"\b" + re.escape(sig) + r"\b", lower_text):
            return aid

    return default_agent
