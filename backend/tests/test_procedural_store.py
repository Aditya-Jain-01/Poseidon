"""Tests for Procedural Memory Store.

Validates SKILL.md loading, frontmatter parsing, trigger matching,
skill creation, and retrieval.
"""

import tempfile
from pathlib import Path

import pytest

from app.memory.procedural_store import ProceduralStore, _parse_frontmatter, Skill


@pytest.fixture
def skills_dir(tmp_path):
    """Create a temporary skills directory with sample SKILL.md files."""
    d = tmp_path / "skills"
    d.mkdir()

    # Skill 1: Schedule Meeting
    (d / "schedule_meeting.SKILL.md").write_text(
        "---\n"
        "name: Schedule Meeting\n"
        "description: How to schedule a meeting or event\n"
        "triggers: [schedule, meeting, book, appointment]\n"
        "---\n\n"
        "When the user asks to schedule a meeting:\n"
        "1. Extract the details\n"
        "2. Check for conflicts\n"
        "3. Create the event\n",
        encoding="utf-8",
    )

    # Skill 2: Send Message
    (d / "send_message.SKILL.md").write_text(
        "---\n"
        "name: Send Message\n"
        "description: How to send a message to a contact\n"
        "triggers: [message, text, send, notify]\n"
        "---\n\n"
        "When the user wants to send a message:\n"
        "1. Identify the recipient\n"
        "2. Compose the message\n"
        "3. Send via the appropriate channel\n",
        encoding="utf-8",
    )

    return d


@pytest.fixture
def store(skills_dir):
    """Create a ProceduralStore with sample skills."""
    return ProceduralStore(skills_dir=skills_dir)


class TestFrontmatterParsing:
    """Test YAML frontmatter parsing."""

    def test_parse_basic(self):
        text = "---\nname: Test\ndescription: A test skill\ntriggers: [foo, bar]\n---\n\nBody content."
        fm, body = _parse_frontmatter(text)
        assert fm["name"] == "Test"
        assert fm["description"] == "A test skill"
        assert fm["triggers"] == ["foo", "bar"]
        assert body == "Body content."

    def test_parse_no_frontmatter(self):
        text = "Just plain content without frontmatter."
        fm, body = _parse_frontmatter(text)
        assert fm == {}
        assert body == text

    def test_parse_quoted_values(self):
        text = '---\nname: "Quoted Name"\ntriggers: ["item1", "item2"]\n---\n\nBody.'
        fm, body = _parse_frontmatter(text)
        assert fm["name"] == "Quoted Name"
        assert fm["triggers"] == ["item1", "item2"]


class TestProceduralStoreLoading:
    """Test skill loading from disk."""

    def test_loads_skills(self, store):
        assert store.count() == 2

    def test_skill_names(self, store):
        skills = store.get_all_skills()
        names = {s.name for s in skills}
        assert "Schedule Meeting" in names
        assert "Send Message" in names

    def test_get_by_name(self, store):
        skill = store.get_skill_by_name("Schedule Meeting")
        assert skill is not None
        assert "schedule" in [t.lower() for t in skill.triggers]

    def test_get_by_name_not_found(self, store):
        skill = store.get_skill_by_name("Nonexistent Skill")
        assert skill is None

    def test_empty_directory(self, tmp_path):
        empty_dir = tmp_path / "empty_skills"
        s = ProceduralStore(skills_dir=empty_dir)
        assert s.count() == 0
        assert empty_dir.exists()  # should be auto-created


class TestTriggerMatching:
    """Test skill retrieval by trigger keyword matching."""

    def test_match_single_trigger(self, store):
        results = store.retrieve("I want to schedule a call")
        assert len(results) >= 1
        assert any(s.name == "Schedule Meeting" for s in results)

    def test_match_different_trigger(self, store):
        results = store.retrieve("Book an appointment for Monday")
        assert len(results) >= 1
        assert any(s.name == "Schedule Meeting" for s in results)

    def test_match_messaging(self, store):
        results = store.retrieve("Send a message to Alex")
        assert len(results) >= 1
        assert any(s.name == "Send Message" for s in results)

    def test_no_match(self, store):
        results = store.retrieve("What is the weather today?")
        assert len(results) == 0

    def test_case_insensitive(self, store):
        results = store.retrieve("SCHEDULE a MEETING")
        assert len(results) >= 1


class TestSkillCreation:
    """Test creating new skills programmatically."""

    def test_create_skill(self, store, skills_dir):
        path = store.create_skill(
            name="Take Notes",
            description="How to take and organize notes",
            triggers=["note", "remember", "write down"],
            content="When asked to take a note:\n1. Save it\n2. Confirm",
        )

        assert path.exists()
        assert store.count() == 3  # 2 original + 1 new

        skill = store.get_skill_by_name("Take Notes")
        assert skill is not None
        assert "note" in skill.triggers

    def test_created_skill_matches(self, store):
        store.create_skill(
            name="Research",
            description="How to research a topic",
            triggers=["research", "look up", "find out"],
            content="Steps for research.",
        )

        results = store.retrieve("Research the latest AI papers")
        assert len(results) >= 1


class TestSkillFormatting:
    """Test the prompt block formatting."""

    def test_to_prompt_block(self, store):
        skill = store.get_skill_by_name("Schedule Meeting")
        block = skill.to_prompt_block()
        assert "### Skill: Schedule Meeting" in block
        assert "Extract the details" in block
