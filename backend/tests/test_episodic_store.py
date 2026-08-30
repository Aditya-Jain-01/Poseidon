"""Unit and integration tests for EpisodicStore (Vector RAG via sqlite-vec)."""

import gc
import json
import random
import unittest
import tempfile
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import MagicMock

from app.memory.episodic_store import EpisodicStore


class FakeEmbeddingService:
    """A lightweight mock embedding service for testing.

    Uses a simple deterministic hash-based approach to generate
    consistent 384-dim vectors for the same input text.
    """

    def __init__(self, dim: int = 384):
        self.dim = dim

    def embed_text(self, text: str) -> list[float]:
        """Generate a deterministic pseudo-random vector from the text."""
        rng = random.Random(text)
        vec = [rng.gauss(0, 1) for _ in range(self.dim)]
        # Normalize to unit length
        norm = sum(v * v for v in vec) ** 0.5
        return [v / norm for v in vec]

    def embed_batch(self, texts: list[str]) -> list[list[float]]:
        return [self.embed_text(t) for t in texts]


class TestEpisodicStore(unittest.TestCase):
    """Test suite for EpisodicStore SQLite & sqlite-vec operations."""

    def setUp(self):
        self.tmpdir = tempfile.TemporaryDirectory()
        self.db_path = Path(self.tmpdir.name) / "test_state.db"
        self.fake_embed = FakeEmbeddingService()
        self.store = EpisodicStore(db_path=self.db_path, embed_svc=self.fake_embed)

    def tearDown(self):
        del self.store
        gc.collect()
        self.tmpdir.cleanup()

    def test_db_initialization(self):
        """Test that SQLite tables and vec0 virtual table are created."""
        self.assertTrue(self.store.db_path.exists())

        with self.store._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
            tables = {row[0] for row in cursor.fetchall()}
            self.assertIn("episodic_events", tables)
            self.assertIn("vec_episodes", tables)

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

    def test_vector_embedding_stored(self):
        """Test that a vector is inserted into vec_episodes alongside the event."""
        ev_id = self.store.log_event("user_1", "user", "Test vector storage")

        with self.store._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT rowid FROM vec_episodes WHERE rowid = ?", (ev_id,))
            row = cursor.fetchone()
            self.assertIsNotNone(row)

    def test_search_relevant_vector_knn(self):
        """Test vector KNN relevance search returns results."""
        self.store.log_event("user_1", "user", "I have a severe peanut allergy and cannot eat nuts.")
        self.store.log_event("user_1", "user", "My favorite color is blue.")
        self.store.log_event("user_1", "user", "Book a dentist appointment for tomorrow.")
        self.store.log_event("user_2", "user", "I also have a peanut allergy.")

        # Search for user_1 — should return results (exact content depends on fake embeddings)
        results = self.store.search_relevant("user_1", "peanut allergy")
        self.assertGreaterEqual(len(results), 1)
        # All results must belong to user_1
        for r in results:
            self.assertEqual(r["user_id"], "user_1")

    def test_search_relevant_empty_query(self):
        """Test that an empty query returns no results."""
        self.store.log_event("user_1", "user", "Some content")
        results = self.store.search_relevant("user_1", "")
        self.assertEqual(len(results), 0)

    def test_search_relevant_user_isolation(self):
        """Test that vector search respects user_id boundaries."""
        self.store.log_event("user_1", "user", "Secret info for user 1")
        self.store.log_event("user_2", "user", "Secret info for user 2")

        results = self.store.search_relevant("user_1", "secret info")
        for r in results:
            self.assertEqual(r["user_id"], "user_1")

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

        # Verify deduplication
        ids = [r["id"] for r in results]
        self.assertEqual(len(ids), len(set(ids)))

        # Should have both recent and relevant results
        self.assertGreaterEqual(len(results), 2)

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
        """Test that data persists to disk and can be read by a new EpisodicStore instance."""
        db_file = self.store.db_path
        self.store.log_event("user_1", "user", "My dog's name is Barnaby.")

        second_store = EpisodicStore(db_path=db_file, embed_svc=self.fake_embed)
        results = second_store.search_relevant("user_1", "Barnaby")
        self.assertGreaterEqual(len(results), 1)
        del second_store

    def test_clear(self):
        """Test clearing events and their vectors."""
        self.store.log_event("user_1", "user", "Message 1")
        self.store.log_event("user_1", "user", "Message 2")
        self.store.log_event("user_2", "user", "User 2 message")

        self.store.clear("user_1")

        recent_u1 = self.store.get_recent("user_1")
        self.assertEqual(len(recent_u1), 0)

        recent_u2 = self.store.get_recent("user_2")
        self.assertEqual(len(recent_u2), 1)

    def test_clear_all(self):
        """Test clearing all events."""
        self.store.log_event("user_1", "user", "Message 1")
        self.store.log_event("user_2", "user", "Message 2")

        self.store.clear()

        self.assertEqual(len(self.store.get_recent("user_1")), 0)
        self.assertEqual(len(self.store.get_recent("user_2")), 0)


if __name__ == "__main__":
    unittest.main()
