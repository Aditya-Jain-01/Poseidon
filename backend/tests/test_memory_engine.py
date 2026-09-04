"""Tests for MemoryEngine facade and 4-tier memory integration."""

import pytest
from app.memory.memory_engine import memory_engine


def test_memory_engine_hydrate_context():
    messages = memory_engine.hydrate_context(
        agent_id="poseidon",
        user_id="test_user_engine",
        user_text="What is my name?",
    )

    assert len(messages) >= 2
    system_msg = messages[0]
    human_msg = messages[-1]

    assert getattr(system_msg, "type", "") == "system"
    assert getattr(human_msg, "type", "") in ("human", "user")
    assert human_msg.content == "What is my name?"


def test_memory_engine_record_turn():
    user_id = "test_user_record"
    memory_engine.record_turn(
        user_id=user_id,
        user_text="I prefer dark mode.",
        reply="Noted, dark mode preference saved.",
        run_id="run_engine_001",
        channel="web",
    )

    history = memory_engine.session_store.get_history(user_id)
    assert len(history) == 2
    assert history[0].content == "I prefer dark mode."
    assert history[1].content == "Noted, dark mode preference saved."
