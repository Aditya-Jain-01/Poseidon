"""MemoryEngine — Unified deep facade for Poseidon's 4-tier memory architecture.

Preserves the four distinct operational tiers:
1. Working Memory (in-process active session context)
2. Procedural Memory (*.SKILL.md flat playbooks)
3. Semantic Memory (MEMORY.md + SQLite FTS5 BM25 keyword index)
4. Episodic Memory (SQLite structured logs + sqlite-vec vector store)
+ Background Consolidation (triggered after N turns)

Callers interact through two clean methods:
- hydrate_context(agent_id, user_id, user_text) -> list[BaseMessage]
- record_turn(user_id, user_text, reply, run_id, channel)
"""

from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Any
from langchain_core.messages import BaseMessage, SystemMessage, HumanMessage, AIMessage

from app.config import settings
from app.memory.episodic_store import episodic_store
from app.memory.semantic_store import semantic_store
from app.memory.procedural_store import procedural_store
from app.soul import soul_store


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


session_store = SessionStore()


class MemoryEngine:
    """Facade unifying the 4-tier cognitive memory architecture.

    hydrate_context() assembles the Working Memory message list for each
    agent turn by combining: soul persona + procedural skills + semantic
    facts + episodic recall + session history + current user message.
    """

    def __init__(self) -> None:
        self.session_store = session_store
        self.episodic_store = episodic_store
        self.semantic_store = semantic_store
        self.procedural_store = procedural_store
        self._last_context: dict[str, Any] = {
            "semantic_facts": [],
            "episodic_events": [],
            "procedural_skills": [],
        }

    def get_last_memory_context(self) -> dict[str, Any]:
        """Return the structured memory slices retrieved during the most recent hydration."""
        return dict(self._last_context)

    def _format_episodic(self, events: list[dict[str, Any]]) -> str:
        if not events:
            return ""
        lines = ["## Recalled Past Conversations & Events (Episodic Memory):"]
        for ev in events:
            role = ev.get("role", "unknown")
            content = ev.get("content", "")
            ts = ev.get("created_at", "")
            lines.append(f"[{ts}] {role}: {content}")
        return "\n".join(lines)

    def _get_raw_semantic(self, user_id: str, user_text: str) -> list[str]:
        try:
            results = self.semantic_store.retrieve(user_id=user_id, query=user_text)
            if not results:
                return []
            if isinstance(results, list):
                return [r if isinstance(r, str) else r.get("fact", str(r)) for r in results]
            return [str(results)]
        except Exception:
            return []

    def _format_semantic(self, user_id: str, user_text: str) -> str:
        try:
            results = self.semantic_store.retrieve(user_id=user_id, query=user_text)
            if not results:
                return ""
            if isinstance(results, list):
                return "## Recalled Facts & User Profile (Semantic Memory):\n" + "\n".join(
                    f"- {r}" if isinstance(r, str) else f"- {r.get('fact', str(r))}" for r in results
                )
            return f"## Recalled Facts & User Profile (Semantic Memory):\n{results}"
        except Exception:
            return ""

    def _get_raw_procedural(self, user_text: str) -> list[str]:
        try:
            results = self.procedural_store.retrieve(task_query=user_text)
            if not results:
                return []
            if isinstance(results, list):
                return [
                    s.get("name", str(s)) if isinstance(s, dict) else getattr(s, "name", str(s))
                    for s in results
                ]
            return [str(results)]
        except Exception:
            return []

    def _format_procedural(self, user_text: str) -> str:
        try:
            results = self.procedural_store.retrieve(task_query=user_text)
            if not results:
                return ""
            if isinstance(results, list):
                return "## Active Procedural Playbooks (Skills):\n" + "\n\n".join(str(s) for s in results)
            return f"## Active Procedural Playbooks (Skills):\n{results}"
        except Exception:
            return ""

    def hydrate_context(
        self,
        agent_id: str = "poseidon",
        user_id: str = "local_user",
        user_text: str = "",
    ) -> list[BaseMessage]:
        """Assemble Working Memory context for an agent turn.

        Retrieves episodic, semantic, and procedural memories, binds the agent persona,
        and appends session chat history and the current user message.
        """
        persona = soul_store.build_system_prompt(agent_id) if agent_id else "You are Poseidon, a personal AI agent with persistent memory."

        episodic_events = self.episodic_store.retrieve(user_id=user_id, query=user_text) or []
        episodic_block = self._format_episodic(episodic_events)
        semantic_block = self._format_semantic(user_id=user_id, user_text=user_text)
        procedural_block = self._format_procedural(user_text=user_text)

        self._last_context = {
            "semantic_facts": self._get_raw_semantic(user_id, user_text),
            "episodic_events": [
                {
                    "role": ev.get("role", "user"),
                    "content": ev.get("content", ""),
                    "created_at": ev.get("created_at", ""),
                }
                for ev in episodic_events
            ],
            "procedural_skills": self._get_raw_procedural(user_text),
        }

        memory_blocks = [b for b in [procedural_block, semantic_block, episodic_block] if b]

        # Inject persistent memory behind a delimiter so _inject_agent_soul
        # (in qa_agent.py) can detect and preserve it across re-hydrations
        if memory_blocks:
            memory_section = "\n\n".join(memory_blocks)
            full_system_prompt = (
                f"{persona}\n\n"
                f"=== PERSISTENT MEMORY CONTEXT ===\n"
                f"{memory_section}\n"
                f"================================="
            )
        else:
            full_system_prompt = persona

        history = self.session_store.get_history(user_id)
        return [
            SystemMessage(content=full_system_prompt),
            *history,
            HumanMessage(content=user_text),
        ]

    def record_turn(
        self,
        user_id: str,
        user_text: str,
        reply: str,
        run_id: str,
        channel: str = "web",
    ) -> None:
        """Persist exchange to Working Memory session and Episodic store."""
        self.session_store.append(user_id, user_text, reply)

        self.episodic_store.log_exchange(
            user_id=user_id,
            human_msg=user_text,
            ai_msg=reply,
            channel=channel,
            run_id=run_id,
        )

        self._maybe_trigger_consolidation(user_id)

    def _maybe_trigger_consolidation(self, user_id: str) -> None:
        """Fire-and-forget background task: once unconsolidated turn count
        hits the threshold, the SummarizerAgent distills episodic events
        into durable semantic facts and procedural skills.
        """
        try:
            from app.memory.consolidation import get_unconsolidated_events
            unconsolidated = get_unconsolidated_events(user_id=user_id, limit=50)
            threshold = getattr(settings, "poseidon_consolidation_threshold", 30)
            if len(unconsolidated) >= threshold:
                from app.agents.summarizer_agent import summarize_and_consolidate
                try:
                    loop = asyncio.get_running_loop()
                    async def _safe_consolidate():
                        try:
                            await summarize_and_consolidate(user_id=user_id, events=unconsolidated)
                        except Exception as err:
                            print(f"[MemoryEngine] Background consolidation task error: {err}")
                    loop.create_task(_safe_consolidate())
                except RuntimeError:
                    pass
        except Exception as exc:
            print(f"[MemoryEngine] Consolidation trigger check error: {exc}")


memory_engine = MemoryEngine()
