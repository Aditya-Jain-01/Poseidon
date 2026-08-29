"""Working Memory — assembles the message list for each agent run.

Sprint 2 (Person A — Stage 4):
- System prompt + persistent memory retrieval (Episodic + dynamic hooks for Semantic & Procedural)
  + in-session chat history + user message.
"""

from pathlib import Path
from typing import Any
from langchain_core.messages import BaseMessage, SystemMessage, HumanMessage, AIMessage

from app.memory.episodic_store import episodic_store


_PROMPT_DIR = Path(__file__).resolve().parent.parent / "prompts"
_system_prompt: str | None = None


def _load_system_prompt() -> str:
    global _system_prompt
    if _system_prompt is None:
        path = _PROMPT_DIR / "system_prompt.md"
        _system_prompt = path.read_text(encoding="utf-8").strip()
    return _system_prompt


class SessionStore:
    """In-memory per-user chat history for the active session."""

    def __init__(self) -> None:
        self._sessions: dict[str, list[BaseMessage]] = {}

    def get_history(self, user_id: str) -> list[BaseMessage]:
        return list(self._sessions.get(user_id, []))

    def append(self, user_id: str, human_msg: str, ai_msg: str) -> None:
        if user_id not in self._sessions:
            self._sessions[user_id] = []
        self._sessions[user_id].append(HumanMessage(content=human_msg))
        self._sessions[user_id].append(AIMessage(content=ai_msg))

    def clear(self, user_id: str | None = None) -> None:
        if user_id:
            self._sessions.pop(user_id, None)
        else:
            self._sessions.clear()


# Singleton session store
session_store = SessionStore()


def _format_episodic_memory(events: list[dict[str, Any]]) -> str:
    """Format retrieved episodic events into a readable context block."""
    if not events:
        return ""
    lines = ["## Recalled Past Conversations & Events (Episodic Memory):"]
    for ev in events:
        role = ev.get("role", "unknown")
        content = ev.get("content", "")
        ts = ev.get("created_at", "")
        lines.append(f"[{ts}] {role}: {content}")
    return "\n".join(lines)


def _get_semantic_context(user_id: str, user_text: str) -> str:
    """Retrieve semantic memory if semantic_store is available (Person B)."""
    try:
        from app.memory.semantic_store import semantic_store  # type: ignore
        if hasattr(semantic_store, "retrieve"):
            results = semantic_store.retrieve(user_id=user_id, query=user_text)
            if results:
                if isinstance(results, list):
                    return "## Recalled Facts & User Profile (Semantic Memory):\n" + "\n".join(
                        f"- {r}" if isinstance(r, str) else f"- {r.get('fact', str(r))}" for r in results
                    )
                return f"## Recalled Facts & User Profile (Semantic Memory):\n{results}"
    except ImportError:
        pass
    except Exception:
        pass
    return ""


def _get_procedural_context(user_text: str) -> str:
    """Retrieve procedural skills if procedural_store is available (Person B)."""
    try:
        from app.memory.procedural_store import procedural_store  # type: ignore
        if hasattr(procedural_store, "retrieve"):
            results = procedural_store.retrieve(task_query=user_text)
            if results:
                if isinstance(results, list):
                    return "## Active Procedural Playbooks (Skills):\n" + "\n\n".join(str(s) for s in results)
                return f"## Active Procedural Playbooks (Skills):\n{results}"
    except ImportError:
        pass
    except Exception:
        pass
    return ""


def assemble(user_text: str, user_id: str) -> list[BaseMessage]:
    """Build the full Working Memory message list for one agent run.

    Retrieves episodic memory (+ hooks for semantic & procedural memory),
    assembles system prompt with memory context, appends active session history,
    and finishes with the current user prompt.

    Returns [SystemMessage, *chat_history, HumanMessage].
    """
    base_prompt = _load_system_prompt()

    # 1. Retrieve persistent memories
    episodic_events = episodic_store.retrieve(user_id=user_id, query=user_text)
    episodic_context = _format_episodic_memory(episodic_events)
    semantic_context = _get_semantic_context(user_id=user_id, user_text=user_text)
    procedural_context = _get_procedural_context(user_text=user_text)

    # 2. Combine memory blocks
    memory_blocks = [block for block in [procedural_context, semantic_context, episodic_context] if block]

    if memory_blocks:
        memory_section = "\n\n".join(memory_blocks)
        full_system_prompt = (
            f"{base_prompt}\n\n"
            f"=== PERSISTENT MEMORY CONTEXT ===\n"
            f"{memory_section}\n"
            f"================================="
        )
    else:
        full_system_prompt = base_prompt

    # 3. Assemble message list
    history = session_store.get_history(user_id)
    return [
        SystemMessage(content=full_system_prompt),
        *history,
        HumanMessage(content=user_text),
    ]
