"""Working Memory — assembles the message list for each agent run.

Sprint 1: system prompt + in-session chat history + user message.
No persistent memory retrieval yet (procedural/semantic/episodic come in Sprint 2).
"""

from pathlib import Path
from langchain_core.messages import BaseMessage, SystemMessage, HumanMessage, AIMessage


_PROMPT_DIR = Path(__file__).resolve().parent.parent / "prompts"
_system_prompt: str | None = None


def _load_system_prompt() -> str:
    global _system_prompt
    if _system_prompt is None:
        path = _PROMPT_DIR / "system_prompt.md"
        _system_prompt = path.read_text(encoding="utf-8").strip()
    return _system_prompt


class SessionStore:
    """In-memory per-user chat history. Lost on restart — Sprint 1 scope."""

    def __init__(self) -> None:
        self._sessions: dict[str, list[BaseMessage]] = {}

    def get_history(self, user_id: str) -> list[BaseMessage]:
        return list(self._sessions.get(user_id, []))

    def append(self, user_id: str, human_msg: str, ai_msg: str) -> None:
        if user_id not in self._sessions:
            self._sessions[user_id] = []
        self._sessions[user_id].append(HumanMessage(content=human_msg))
        self._sessions[user_id].append(AIMessage(content=ai_msg))


# Singleton session store
session_store = SessionStore()


def assemble(user_text: str, user_id: str) -> list[BaseMessage]:
    """Build the full message list for one agent run.

    Returns [SystemMessage, *chat_history, HumanMessage].
    """
    prompt = _load_system_prompt()
    history = session_store.get_history(user_id)
    return [
        SystemMessage(content=prompt),
        *history,
        HumanMessage(content=user_text),
    ]
