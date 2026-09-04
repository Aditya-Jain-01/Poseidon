"""Unit tests for Working Memory assembly (Person A — Stage 4)."""

import gc
import unittest
import tempfile
from pathlib import Path
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage

from app.memory.episodic_store import EpisodicStore
from app.memory.working_memory import assemble, session_store
from app.memory.memory_engine import memory_engine
import app.memory.working_memory as wm_module


class TestWorkingMemory(unittest.TestCase):
    """Test suite for Working Memory assembly."""

    def setUp(self):
        self.tmpdir = tempfile.TemporaryDirectory()
        self.test_db = Path(self.tmpdir.name) / "test_state.db"
        self.test_store = EpisodicStore(db_path=self.test_db)
        self._orig_store = memory_engine.episodic_store
        self._orig_wm_store = getattr(wm_module, "episodic_store", None)
        memory_engine.episodic_store = self.test_store
        wm_module.episodic_store = self.test_store
        session_store.clear()

    def tearDown(self):
        memory_engine.episodic_store = self._orig_store
        if self._orig_wm_store is not None:
            wm_module.episodic_store = self._orig_wm_store
        session_store.clear()
        del self.test_store
        gc.collect()
        self.tmpdir.cleanup()

    def test_working_memory_assembly_basic(self):
        """Test assembling working memory with base prompt and user text."""
        messages = assemble(user_text="Hello Poseidon!", user_id="test_user")

        self.assertEqual(len(messages), 2)
        self.assertIsInstance(messages[0], SystemMessage)
        self.assertIsInstance(messages[1], HumanMessage)
        self.assertEqual(messages[1].content, "Hello Poseidon!")
        # Soul is loaded from poseidon.soul.md — persona starts with "# Poseidon"
        self.assertIn("Poseidon", messages[0].content)

    def test_working_memory_with_session_history(self):
        """Test that session history is preserved in correct order."""
        session_store.append("user_abc", "My name is Alice.", "Nice to meet you, Alice!")

        messages = assemble(user_text="What is my name?", user_id="user_abc")

        self.assertEqual(len(messages), 4)
        self.assertIsInstance(messages[0], SystemMessage)
        self.assertIsInstance(messages[1], HumanMessage)
        self.assertEqual(messages[1].content, "My name is Alice.")
        self.assertIsInstance(messages[2], AIMessage)
        self.assertEqual(messages[2].content, "Nice to meet you, Alice!")
        self.assertIsInstance(messages[3], HumanMessage)
        self.assertEqual(messages[3].content, "What is my name?")

    def test_working_memory_integrates_episodic_memory(self):
        """Test that episodic memory retrieval is formatted and included in system context."""
        # Seed episodic memory
        self.test_store.log_event("user_xyz", "user", "I am allergic to peanuts.")
        self.test_store.log_event("user_xyz", "assistant", "I will remember that you have a peanut allergy.")

        # Patch retrieve to return deterministic results (real retrieve uses vector search
        # which requires embeddings that aren't available in temp test DB)
        self.test_store.retrieve = lambda user_id, query: [
            {"role": "user", "content": "I am allergic to peanuts.", "created_at": "2026-01-01"},
            {"role": "assistant", "content": "I will remember that you have a peanut allergy.", "created_at": "2026-01-01"},
        ]

        messages = assemble(user_text="Can I eat peanut butter cookies?", user_id="user_xyz")

        system_content = messages[0].content
        self.assertIn("=== PERSISTENT MEMORY CONTEXT ===", system_content)
        self.assertIn("Recalled Past Conversations & Events (Episodic Memory)", system_content)
        self.assertIn("I am allergic to peanuts.", system_content)


if __name__ == "__main__":
    unittest.main()
