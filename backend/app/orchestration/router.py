"""Routing seam for a future master orchestrator."""
from __future__ import annotations


async def route_request(user_text: str, agent_registry: list[dict]) -> str:
    text = user_text.lower()
    for agent in agent_registry:
        for signal in agent.get("routing_signals", []):
            if signal.lower() != "default" and signal.lower() in text:
                return agent["id"]
    for agent in agent_registry:
        if "default" in [str(signal).lower() for signal in agent.get("routing_signals", [])]:
            return agent["id"]
    return agent_registry[0]["id"] if agent_registry else "octavious"
