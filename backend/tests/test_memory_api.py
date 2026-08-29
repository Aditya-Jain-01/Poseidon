"""Integration tests for Memory API endpoints (Person C — Stage 6)."""

import gc
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from fastapi.testclient import TestClient

from app.main import app
from app.memory.episodic_store import EpisodicStore
from app.memory.semantic_store import SemanticStore
from app.memory.procedural_store import ProceduralStore
import app.gateway.memory_adapter as adapter_module
import app.agents.summarizer_agent as summarizer_module
import app.memory.consolidation as consol_module


class TestMemoryAPI(unittest.TestCase):
    """Test suite for /memory/* REST endpoints."""

    def setUp(self):
        self.tmpdir = tempfile.TemporaryDirectory()
        self.test_db = Path(self.tmpdir.name) / "test_state.db"
        self.test_md = Path(self.tmpdir.name) / "memory" / "MEMORY.md"
        self.test_skills_dir = Path(self.tmpdir.name) / "skills"

        self.episodic = EpisodicStore(db_path=self.test_db)
        self.semantic = SemanticStore(db_path=self.test_db, memory_md_path=self.test_md)
        self.procedural = ProceduralStore(skills_dir=self.test_skills_dir)

        # Patch singletons
        self._orig_epi = adapter_module.episodic_store
        self._orig_sem = adapter_module.semantic_store
        self._orig_proc = adapter_module.procedural_store
        self._orig_consol_epi = consol_module.episodic_store
        self._orig_sum_sem = summarizer_module.semantic_store
        self._orig_sum_epi = summarizer_module.episodic_store
        self._orig_sum_proc = summarizer_module.procedural_store

        adapter_module.episodic_store = self.episodic
        adapter_module.semantic_store = self.semantic
        adapter_module.procedural_store = self.procedural
        consol_module.episodic_store = self.episodic
        summarizer_module.semantic_store = self.semantic
        summarizer_module.episodic_store = self.episodic
        summarizer_module.procedural_store = self.procedural

        self.client = TestClient(app)

    def tearDown(self):
        adapter_module.episodic_store = self._orig_epi
        adapter_module.semantic_store = self._orig_sem
        adapter_module.procedural_store = self._orig_proc
        consol_module.episodic_store = self._orig_consol_epi
        summarizer_module.semantic_store = self._orig_sum_sem
        summarizer_module.episodic_store = self._orig_sum_epi
        summarizer_module.procedural_store = self._orig_sum_proc

        del self.episodic
        del self.semantic
        del self.procedural
        gc.collect()
        self.tmpdir.cleanup()

    def test_semantic_memory_endpoint(self):
        """GET /memory/semantic retrieves facts."""
        self.semantic.add_fact("local_user", "Prefers TypeScript", category="preference")
        self.semantic.add_fact("local_user", "Lives in SF", category="profile")

        res = self.client.get("/memory/semantic?user_id=local_user")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data["count"], 2)
        self.assertEqual(data["total_facts"], 2)
        self.assertEqual(len(data["facts"]), 2)

    def test_semantic_category_filter(self):
        """GET /memory/semantic with category filter."""
        self.semantic.add_fact("local_user", "Prefers TypeScript", category="preference")
        self.semantic.add_fact("local_user", "Lives in SF", category="profile")

        res = self.client.get("/memory/semantic?user_id=local_user&category=preference")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data["count"], 1)
        self.assertEqual(data["facts"][0]["category"], "preference")

    def test_episodic_memory_endpoint(self):
        """GET /memory/episodic retrieves history."""
        self.episodic.log_event("local_user", "user", "What is the weather?")
        self.episodic.log_event("local_user", "assistant", "Sunny and 72F.")

        res = self.client.get("/memory/episodic?user_id=local_user")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data["count"], 2)
        self.assertEqual(data["unconsolidated_count"], 2)

    def test_procedural_memory_endpoint(self):
        """GET /memory/procedural retrieves skills."""
        self.procedural.create_skill(
            name="deploy_app",
            description="Deploy production app",
            triggers=["deploy app", "ship to prod"],
            content="Step 1: run build\nStep 2: run migrate",
        )

        res = self.client.get("/memory/procedural")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data["count"], 1)
        self.assertEqual(data["skills"][0]["name"], "deploy_app")

    def test_memory_status_endpoint(self):
        """GET /memory/status returns status summary."""
        self.semantic.add_fact("local_user", "A fact")
        self.episodic.log_event("local_user", "user", "Hello")

        res = self.client.get("/memory/status?user_id=local_user")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data["semantic_facts_count"], 1)
        self.assertIn("consolidation", data)
        self.assertEqual(data["consolidation"]["unconsolidated_count"], 1)

    @patch("app.agents.summarizer_agent.summarize_events")
    def test_post_consolidate_endpoint(self, mock_summarize):
        """POST /memory/consolidate triggers distillation."""
        self.episodic.log_event("local_user", "user", "My dog is named Cooper.")
        mock_summarize.return_value = {
            "facts": [{"fact": "User has a dog named Cooper", "category": "relationship"}],
            "skills": [],
        }

        res = self.client.post("/memory/consolidate", json={"user_id": "local_user", "force": True})
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertTrue(data["consolidated"])
        self.assertEqual(data["facts_added"], 1)


if __name__ == "__main__":
    unittest.main()
