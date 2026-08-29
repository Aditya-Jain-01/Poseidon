"""Unit tests for Memory Consolidation pipeline (Person C — Stage 5)."""

import gc
import tempfile
import unittest
from pathlib import Path
from unittest.mock import AsyncMock, patch

from app.memory.episodic_store import EpisodicStore
from app.memory.semantic_store import SemanticStore
from app.memory.procedural_store import ProceduralStore
from app.memory.consolidation import (
    get_unconsolidated_events,
    get_consolidation_status,
    check_and_trigger_consolidation,
)
import app.memory.consolidation as consol_module
import app.agents.summarizer_agent as summarizer_module


class TestConsolidation(unittest.IsolatedAsyncioTestCase):
    """Test suite for memory consolidation manager."""

    async def asyncSetUp(self):
        self.tmpdir = tempfile.TemporaryDirectory()
        self.test_db = Path(self.tmpdir.name) / "test_state.db"
        self.test_md = Path(self.tmpdir.name) / "memory" / "MEMORY.md"
        self.test_skills_dir = Path(self.tmpdir.name) / "skills"

        self.episodic = EpisodicStore(db_path=self.test_db)
        self.semantic = SemanticStore(db_path=self.test_db, memory_md_path=self.test_md)
        self.procedural = ProceduralStore(skills_dir=self.test_skills_dir)

        # Patch singletons
        self._orig_epi = consol_module.episodic_store
        self._orig_sum_epi = summarizer_module.episodic_store
        self._orig_sum_sem = summarizer_module.semantic_store
        self._orig_sum_proc = summarizer_module.procedural_store

        consol_module.episodic_store = self.episodic
        summarizer_module.episodic_store = self.episodic
        summarizer_module.semantic_store = self.semantic
        summarizer_module.procedural_store = self.procedural

    async def asyncTearDown(self):
        consol_module.episodic_store = self._orig_epi
        summarizer_module.episodic_store = self._orig_sum_epi
        summarizer_module.semantic_store = self._orig_sum_sem
        summarizer_module.procedural_store = self._orig_sum_proc

        del self.episodic
        del self.semantic
        del self.procedural
        gc.collect()
        self.tmpdir.cleanup()

    async def test_unconsolidated_retrieval(self):
        """Test fetching unconsolidated events."""
        self.episodic.log_event("user1", "user", "I live in Seattle.")
        self.episodic.log_event("user1", "assistant", "Noted that you live in Seattle.")

        events = get_unconsolidated_events("user1")
        self.assertEqual(len(events), 2)
        self.assertEqual(events[0]["content"], "I live in Seattle.")

    async def test_consolidation_status(self):
        """Test checking consolidation status and progress."""
        self.episodic.log_event("user1", "user", "Fact 1")
        status = get_consolidation_status("user1")

        self.assertEqual(status["user_id"], "user1")
        self.assertEqual(status["unconsolidated_count"], 1)
        self.assertFalse(status["ready"])

    @patch("app.agents.summarizer_agent.summarize_events")
    async def test_threshold_not_reached_without_force(self, mock_summarize):
        """When count < threshold and force=False, consolidation does not run."""
        self.episodic.log_event("user1", "user", "My favorite color is navy blue.")

        with patch("app.memory.consolidation.settings.poseidon_consolidation_threshold", 10):
            result = await check_and_trigger_consolidation("user1", force=False)
            self.assertFalse(result["consolidated"])
            self.assertEqual(result["reason"], "threshold_not_reached")
            mock_summarize.assert_not_called()

    @patch("app.agents.summarizer_agent.summarize_events")
    async def test_forced_consolidation_success(self, mock_summarize):
        """Forced consolidation runs regardless of threshold."""
        self.episodic.log_event("user1", "user", "I work at SpaceX on Starship.")
        self.episodic.log_event("user1", "assistant", "Great, noted!")

        mock_summarize.return_value = {
            "facts": [
                {"fact": "User works at SpaceX on Starship", "category": "profile"}
            ],
            "skills": [
                {
                    "name": "rocket_test",
                    "description": "Starship test checklist",
                    "triggers": ["starship test"],
                    "content": "Step 1: Fuel prep\nStep 2: Ignition",
                }
            ],
        }

        result = await check_and_trigger_consolidation("user1", force=True)

        self.assertTrue(result["consolidated"])
        self.assertEqual(result["events_processed"], 2)
        self.assertEqual(result["facts_added"], 1)
        self.assertEqual(result["skills_added"], 1)

        # Verify semantic store has fact
        facts = self.semantic.get_all_facts("user1")
        self.assertEqual(len(facts), 1)
        self.assertEqual(facts[0]["fact"], "User works at SpaceX on Starship")
        self.assertEqual(facts[0]["category"], "profile")

        # Verify procedural store has skill
        skills = self.procedural.get_all_skills()
        self.assertEqual(len(skills), 1)
        self.assertEqual(skills[0].name, "rocket_test")

        # Verify episodic records are marked consolidated
        self.assertEqual(self.episodic.count_unconsolidated("user1"), 0)


if __name__ == "__main__":
    unittest.main()
