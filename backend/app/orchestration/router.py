"""Agent router — routes inbound text to an appropriate agent."""
from __future__ import annotations

import re
from typing import Any

from app.orchestration.graph import DEFAULT_PRIMARY_AGENT
from app.soul import soul_store


def route_request(user_text: str, default_agent: str = DEFAULT_PRIMARY_AGENT) -> str:
    """Resolve target agent from text directives (@agent, /agent <name>, routing signals) or default.

    Defaults to DEFAULT_PRIMARY_AGENT ('poseidon').
    """
    if not user_text:
        return default_agent

    cleaned = user_text.strip()

    # Direct command: /agent <name>
    if cleaned.startswith("/agent"):
        parts = cleaned.split(maxsplit=2)
        if len(parts) >= 2:
            candidate = parts[1].lower().strip()
            from app.llm_providers import DEFAULT_AGENT_OVERRIDES
            if soul_store.get_agent(candidate) or candidate in DEFAULT_AGENT_OVERRIDES:
                return candidate

    # Direct mention: @<name>
    if cleaned.startswith("@"):
        first_token = cleaned.split()[0][1:].lower()
        from app.llm_providers import DEFAULT_AGENT_OVERRIDES
        if soul_store.get_agent(first_token) or first_token in DEFAULT_AGENT_OVERRIDES:
            return first_token

    # Check keyword routing signals from agent registry
    lower_text = cleaned.lower()
    signals = soul_store.get_routing_signals()
    for sig, aid in signals.items():
        if sig == "default":
            continue
        # match whole word / phrase boundary
        if re.search(r"\b" + re.escape(sig) + r"\b", lower_text):
            return aid

    # Fallback to default
    return default_agent
