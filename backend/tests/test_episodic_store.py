"""Unit and integration tests for EpisodicStore (Person A — Stage 1)."""

import gc
import unittest
import tempfile
from datetime import datetime, timedelta
from pathlib import Path

from app.memory.episodic_store import EpisodicStore


class TestEpisodicStore(unittest.TestCase):
    """Test suite for EpisodicStore SQLite & FTS5 operations."""

    def setUp(self):
        self.tmpdir = tempfile.TemporaryDirectory()
        self.db_path = Path(self.tmpdir.name) / "test_state.db"
        self.store = EpisodicStore(db_path=self.db_path)

    def tearDown(self):
        del self.store
        gc.collect()
        self.tmpdir.cleanup()

    def test_db_initialization(self):
        """Test that SQLite tables and FTS5 virtual table are created."""
        self.assertTrue(self.store.db_path.exists())

        with self.store._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
            tables = {row[0] for row in cursor.fetchall()}
            self.assertIn("episodic_events", tables)
            self.assertIn("episodic_fts", tables)

    def test_log_event_and_exchange(self):
        """Test logging single events and exchanges."""
        ev_id = self.store.log_event(
            user_id="user_1",
            role="user",
            content="I prefer dark roast coffee.",
            channel="telegram",
            run_id="run_101",
            metadata={"tokens": 15},
        )
        self.assertIsInstance(ev_id, int)
        self.assertGreater(ev_id, 0)

        user_id_int, ai_id_int = self.store.log_exchange(
            user_id="user_1",
            human_msg="What time is my flight tomorrow?",
            ai_msg="Your flight is at 10:00 AM.",
            channel="web",
            run_id="run_102",
        )
        self.assertGreater(user_id_int, ev_id)
        self.assertGreater(ai_id_int, user_id_int)

        recent = self.store.get_recent("user_1", limit=10)
        self.assertEqual(len(recent), 3)
        self.assertEqual(recent[0]["content"], "I prefer dark roast coffee.")
        self.assertEqual(recent[1]["content"], "What time is my flight tomorrow?")
        self.assertEqual(recent[2]["content"], "Your flight is at 10:00 AM.")

    def test_search_relevant_fts5(self):
        """Test FTS5 keyword relevance search."""
        self.store.log_event("user_1", "user", "I have a severe peanut allergy and cannot eat nuts.")
        self.store.log_event("user_1", "user", "My favorite color is blue.")
        self.store.log_event("user_1", "user", "Book a dentist appointment for tomorrow.")
        self.store.log_event("user_2", "user", "I also have a peanut allergy.")

        # Search for allergy for user_1
        results = self.store.search_relevant("user_1", "peanut allergy")
        self.assertGreaterEqual(len(results), 1)
        self.assertIn("peanut allergy", results[0]["content"])
        self.assertEqual(results[0]["user_id"], "user_1")

        # Ensure user isolation
        user2_results = self.store.search_relevant("user_2", "color")
        self.assertEqual(len(user2_results), 0)

    def test_retrieve_hybrid_deduplication(self):
        """Test combined retrieval of recency and relevance with deduplication."""
        past_time = (datetime.now() - timedelta(days=5)).isoformat()
        self.store.log_event(
            user_id="user_1",
            role="user",
            content="Remember that my passport number is A1234567.",
            created_at=past_time,
        )

        for i in range(10):
            self.store.log_event(
                user_id="user_1",
                role="user",
                content=f"Random chat message number {i}",
            )

        results = self.store.retrieve(
            user_id="user_1",
            query="what is my passport number?",
            recency_limit=3,
            relevance_limit=2,
        )

        contents = [r["content"] for r in results]
        self.assertTrue(any("passport number" in c for c in contents))
        self.assertTrue(any("Random chat message number 9" in c for c in contents))

        ids = [r["id"] for r in results]
        self.assertEqual(len(ids), len(set(ids)))

    def test_consolidation_tracking(self):
        """Test unconsolidated counter and marking."""
        self.assertEqual(self.store.count_unconsolidated("user_1"), 0)

        self.store.log_exchange("user_1", "Hello", "Hi there!")
        self.store.log_exchange("user_1", "How are you?", "I am doing well.")
        self.store.log_exchange("user_2", "Hey", "Hello user 2!")

        self.assertEqual(self.store.count_unconsolidated("user_1"), 4)
        self.assertEqual(self.store.count_unconsolidated("user_2"), 2)
        self.assertEqual(self.store.count_unconsolidated(), 6)

        recent_u1 = self.store.get_recent("user_1")
        u1_ids = [r["id"] for r in recent_u1]
        affected = self.store.mark_consolidated(event_ids=u1_ids)
        self.assertEqual(affected, 4)

        self.assertEqual(self.store.count_unconsolidated("user_1"), 0)
        self.assertEqual(self.store.count_unconsolidated("user_2"), 2)

    def test_disk_persistence_survives_reopen(self):
        """Test that data written persists to disk and can be read by a brand new EpisodicStore instance."""
        db_file = self.store.db_path
        self.store.log_event("user_1", "user", "My dog's name is Barnaby.")

        second_store = EpisodicStore(db_path=db_file)
        results = second_store.search_relevant("user_1", "Barnaby")
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["content"], "My dog's name is Barnaby.")
        del second_store


if __name__ == "__main__":
    unittest.main()
