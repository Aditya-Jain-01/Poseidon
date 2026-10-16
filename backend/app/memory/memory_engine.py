"""MemoryEngine — Unified deep facade for Poseidon's 4-tier memory architecture.

Preserves the four distinct operational tiers:
1. Working Memory (in-process active session context)
2. Procedural Memory (*.SKILL.md flat playbooks)
3. Semantic Memory (MEMORY.md + SQLite FTS5 BM25 keyword index)
4. Episodic Memory (SQLite structured logs + sqlite-vec vector store)
+ Background Consolidation (triggered after N turns)

Callers interact through two clean methods:
- hydrate_context(agent_id, user_id, user_text) -> HydratedContext
- record_turn(user_id, user_text, reply, run_id, channel)
"""

from __future__ import annotations

import asyncio
import json
from dataclasses import dataclass
from app.models import ConversationKey
from app.db.connection import connection
from app.orchestration.approval_store import canonical_json
from pathlib import Path
from typing import Any
from langchain_core.messages import BaseMessage, SystemMessage, HumanMessage, AIMessage

from app.config import settings
from app.memory.episodic_store import episodic_store
from app.memory.semantic_store import semantic_store
from app.memory.procedural_store import procedural_store
from app.soul import soul_store


@dataclass(frozen=True)
class HydratedContext:
    messages: tuple[BaseMessage, ...]
    telemetry_json: str

    @property
    def telemetry(self):
        # Every caller receives its own copy; the stored telemetry is immutable.
        return json.loads(self.telemetry_json)


class SessionStore:
    """Conversation-keyed working history; legacy strings mean the default web thread."""
    def __init__(self):
        self._sessions: dict[ConversationKey, list[BaseMessage]] = {}

    @staticmethod
    def key(value):
        return value if isinstance(value, ConversationKey) else ConversationKey(owner_id=value, channel='web', channel_account_id='local_browser', thread_id='default')

    def get_history(self, key):
        return list(self._sessions.get(self.key(key), []))

    def append(self, key, human_msg, ai_msg):
        messages = self._sessions.setdefault(self.key(key), [])
        messages.extend([HumanMessage(content=human_msg), AIMessage(content=ai_msg)])
        del messages[:-2 * settings.poseidon_recent_turns]

    def clear(self, key=None):
        if key is None:
            self._sessions.clear()
        else:
            self._sessions.pop(self.key(key), None)


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
        conversation_key: ConversationKey | None = None,
    ) -> HydratedContext:
        """Assemble Working Memory context for an agent turn.

        Retrieves episodic, semantic, and procedural memories, binds the agent persona,
        and appends session chat history and the current user message.
        """
        persona = soul_store.build_system_prompt(agent_id) if agent_id else "You are Poseidon, a personal AI agent with persistent memory."

        episodic_events = self.episodic_store.retrieve(user_id=user_id, query=user_text) or []
        episodic_block = self._format_episodic(episodic_events)
        semantic_facts = self._get_raw_semantic(user_id, user_text)
        semantic_block = '## Recalled Facts & User Profile (Semantic Memory):\n' + '\n'.join(f'- {fact}' for fact in semantic_facts) if semantic_facts else ''
        skills = self.procedural_store.retrieve(task_query=user_text) or []
        procedural_block = '## Active Procedural Playbooks (Skills):\n' + '\n\n'.join(str(skill) for skill in skills) if skills else ''

        telemetry = {
            "semantic_facts": semantic_facts,
            "episodic_events": [
                {
                    "role": ev.get("role", "user"),
                    "content": ev.get("content", ""),
                    "created_at": ev.get("created_at", ""),
                }
                for ev in episodic_events
            ],
            "procedural_skills": [skill.get('name', str(skill)) if isinstance(skill, dict) else getattr(skill, 'name', str(skill)) for skill in skills],
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

        key = conversation_key or self.session_store.key(user_id)
        history = self.session_store.get_history(key)[-2 * settings.poseidon_recent_turns:]
        if conversation_key is not None:
            # Durable completed conversations survive application reconstruction.
            self.episodic_store.init_db()
            with connection(self.episodic_store.db_path) as conn:
                turns = conn.execute('SELECT user_text,reply FROM completed_turns WHERE conversation_key_json=? ORDER BY rowid DESC LIMIT ?',
                                     (canonical_json(key.model_dump()), settings.poseidon_recent_turns)).fetchall()
            history = [message for row in reversed(turns) for message in (HumanMessage(content=row['user_text']), AIMessage(content=row['reply']))]
        messages = [
            SystemMessage(content=full_system_prompt),
            *history,
            HumanMessage(content=user_text),
        ]
        return HydratedContext(tuple(messages), json.dumps(telemetry))

    def record_turn(
        self,
        user_id: str,
        user_text: str,
        reply: str,
        run_id: str,
        channel: str = "web",
        conversation_key: ConversationKey | None = None,
    ) -> None:
        """Persist exchange to Working Memory session and Episodic store."""
        key = conversation_key or self.session_store.key(user_id)
        self.episodic_store.init_db()
        with connection(self.episodic_store.db_path) as conn:
            if conn.execute('SELECT 1 FROM completed_turns WHERE run_id=?', (run_id,)).fetchone():
                return

        recorded = self.episodic_store.record_completed_turn(
            conversation_key_json=canonical_json(key.model_dump()),
            user_id=user_id,
            user_text=user_text,
            reply=reply,
            channel=channel,
            run_id=run_id,
        )
        if not recorded:
            return
        self.session_store.append(key, user_text, reply)
        self._maybe_trigger_consolidation(user_id)

    def _maybe_trigger_consolidation(self, user_id: str) -> None:
        """Fire-and-forget background task: once unconsolidated event count
        hits the threshold, the SummarizerAgent distills episodic events
        into durable semantic facts and procedural skills.
        """
        try:
            from app.memory.consolidation import check_and_trigger_consolidation
            threshold = getattr(settings, "poseidon_consolidation_threshold", 30)
            if self.episodic_store.count_unconsolidated(user_id=user_id) >= threshold:
                try:
                    loop = asyncio.get_running_loop()
                    async def _safe_consolidate():
                        try:
                            await check_and_trigger_consolidation(user_id=user_id, limit=max(50, threshold))
                        except Exception as err:
                            print(f"[MemoryEngine] Background consolidation task error: {err}")
                    loop.create_task(_safe_consolidate())
                except RuntimeError:
                    pass
        except Exception as exc:
            print(f"[MemoryEngine] Consolidation trigger check error: {exc}")


memory_engine = MemoryEngine()
