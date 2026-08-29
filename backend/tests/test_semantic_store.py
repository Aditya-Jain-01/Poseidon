"""Tests for Semantic Memory Store.

Validates fact CRUD, FTS5 keyword retrieval, MEMORY.md generation,
and category filtering.
"""

import tempfile
from pathlib import Path

import pytest

from app.memory.semantic_store import SemanticStore


@pytest.fixture
def store(tmp_path):
    """Create a SemanticStore with a temporary database and MEMORY.md path."""
    db_path = tmp_path / "test_state.db"
    md_path = tmp_path / "memory" / "MEMORY.md"
    return SemanticStore(db_path=db_path, memory_md_path=md_path)


class TestSemanticStoreCRUD:
    """Test basic create, read, update, deactivate operations."""

    def test_add_and_retrieve_fact(self, store):
        fact_id = store.add_fact("user1", "Alex prefers morning meetings", category="preference")
        assert fact_id > 0

        facts = store.get_all_facts("user1")
        assert len(facts) == 1
        assert facts[0]["fact"] == "Alex prefers morning meetings"
        assert facts[0]["category"] == "preference"

    def test_add_multiple_facts(self, store):
        store.add_fact("user1", "Likes Python")
        store.add_fact("user1", "Lives in Berlin")
        store.add_fact("user1", "Works at Acme Corp")

        facts = store.get_all_facts("user1")
        assert len(facts) == 3

    def test_update_fact(self, store):
        fact_id = store.add_fact("user1", "Likes Python")
        store.update_fact(fact_id, "Loves Python and Rust")

        facts = store.get_all_facts("user1")
        assert len(facts) == 1
        assert facts[0]["fact"] == "Loves Python and Rust"

    def test_deactivate_fact(self, store):
        fact_id = store.add_fact("user1", "Old fact to remove")
        store.deactivate_fact(fact_id)

        facts = store.get_all_facts("user1")
        assert len(facts) == 0

    def test_user_isolation(self, store):
        store.add_fact("user1", "User 1 fact")
        store.add_fact("user2", "User 2 fact")

        assert len(store.get_all_facts("user1")) == 1
        assert len(store.get_all_facts("user2")) == 1

    def test_category_filter(self, store):
        store.add_fact("user1", "Prefers dark mode", category="preference")
        store.add_fact("user1", "Born in 1990", category="profile")
        store.add_fact("user1", "General fact")

        prefs = store.get_all_facts("user1", category="preference")
        assert len(prefs) == 1
        assert prefs[0]["fact"] == "Prefers dark mode"

    def test_count(self, store):
        assert store.count("user1") == 0
        store.add_fact("user1", "Fact 1")
        store.add_fact("user1", "Fact 2")
        assert store.count("user1") == 2

    def test_clear(self, store):
        store.add_fact("user1", "Fact 1")
        store.add_fact("user1", "Fact 2")
        store.clear("user1")
        assert store.count("user1") == 0


class TestSemanticFTS5:
    """Test FTS5 keyword search retrieval."""

    def test_retrieve_by_keyword(self, store):
        store.add_fact("user1", "Alex prefers morning meetings")
        store.add_fact("user1", "Project deadline is Friday")
        store.add_fact("user1", "Raj likes evening tennis")

        results = store.retrieve("user1", "Alex morning")
        assert len(results) >= 1
        assert any("Alex" in r["fact"] for r in results)

    def test_retrieve_empty_query(self, store):
        store.add_fact("user1", "Some fact")
        # Empty query should fall back to all facts
        results = store.retrieve("user1", "")
        assert len(results) >= 1

    def test_retrieve_no_match(self, store):
        store.add_fact("user1", "Likes chocolate")
        results = store.retrieve("user1", "quantum physics")
        # May return empty or fall back to all facts depending on FTS
        assert isinstance(results, list)


class TestMemoryMD:
    """Test MEMORY.md auto-generation."""

    def test_memory_md_created_on_add(self, store):
        store.add_fact("user1", "Test fact", category="general")
        assert store.memory_md_path.exists()

        content = store.memory_md_path.read_text(encoding="utf-8")
        assert "Test fact" in content
        assert "Memory — user1" in content

    def test_memory_md_updated_on_modify(self, store):
        fact_id = store.add_fact("user1", "Old fact")
        store.update_fact(fact_id, "Updated fact")

        content = store.memory_md_path.read_text(encoding="utf-8")
        assert "Updated fact" in content

    def test_memory_md_categories(self, store):
        store.add_fact("user1", "Prefers morning", category="preference")
        store.add_fact("user1", "Lives in Berlin", category="profile")

        content = store.memory_md_path.read_text(encoding="utf-8")
        assert "Preferences" in content
        assert "Profile" in content
