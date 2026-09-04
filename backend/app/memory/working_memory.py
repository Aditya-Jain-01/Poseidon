"""Working Memory — assembles the message list for each agent run.

Delegates to MemoryEngine while maintaining full backward compatibility.
"""

from pathlib import Path
from typing import Any
from langchain_core.messages import BaseMessage

from app.memory.memory_engine import memory_engine, session_store, SessionStore
from app.memory.episodic_store import episodic_store  # backward-compat re-export for tests


def assemble(user_text: str, user_id: str = "local_user") -> list[BaseMessage]:
    """Build the full Working Memory message list for one agent run."""
    return memory_engine.hydrate_context(agent_id="poseidon", user_id=user_id, user_text=user_text)
