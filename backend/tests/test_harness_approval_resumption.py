"""Tests for LangGraph approval parking and loop resumption."""

from datetime import datetime, timezone
import pytest
from unittest.mock import AsyncMock, patch

from app.orchestration.graph import run_agent, resume_approval
from app.orchestration.state import InboundEvent
from app.orchestration.approval_store import approval_store


@pytest.mark.asyncio
async def test_approval_parking_and_denial():
    # Mock LLM calling a tool that requires approval: calendar_create
    fake_tool_call = {
        "id": "call_mock_001",
        "name": "calendar_create",
        "arguments": {"title": "Team Standup", "starts_at": "2026-09-05T10:00:00Z"},
    }

    with patch("app.agents.qa_agent.call", new_callable=AsyncMock) as mock_llm:
        mock_llm.return_value = {
            "content": None,
            "tool_calls": [fake_tool_call],
        }

        event = InboundEvent(
            user_id="test_approval_user",
            channel="web",
            channel_thread_id="web_test",
            text="Schedule a standup meeting for tomorrow",
            timestamp=datetime.now(timezone.utc),
        )

        res = await run_agent(event, run_id="run_approval_test_001")
        assert res.get("approval_request") is not None
        req = res["approval_request"]
        approval_id = req["id"]
        assert req["tool_name"] == "calendar_create"

        # Deny the approval
        denied_res = await resume_approval(approval_id, decision="denied")
        assert "denied" in denied_res["reply"].lower()
        assert denied_res["approval_request"] is None


@pytest.mark.asyncio
async def test_approval_resumption_reenters_graph():
    fake_tool_call = {
        "id": "call_mock_002",
        "name": "calendar_create",
        "arguments": {"title": "Design Sync", "starts_at": "2026-09-05T14:00:00Z"},
    }

    with patch("app.agents.qa_agent.call", new_callable=AsyncMock) as mock_llm:
        # First call: LLM emits tool call
        # Second call (resumption): LLM sees ToolMessage and replies with confirmation
        mock_llm.side_effect = [
            {"content": None, "tool_calls": [fake_tool_call]},
            {"content": "I have successfully scheduled the Design Sync event.", "tool_calls": []},
        ]

        event = InboundEvent(
            user_id="test_approval_user_2",
            channel="web",
            channel_thread_id="web_test_2",
            text="Please schedule Design Sync",
            timestamp=datetime.now(timezone.utc),
        )

        res = await run_agent(event, run_id="run_approval_test_002")
        assert res.get("approval_request") is not None
        approval_id = res["approval_request"]["id"]

        # Approve action -> re-enters graph
        approved_res = await resume_approval(approval_id, decision="approved")
        assert "successfully scheduled" in approved_res["reply"]
        assert approved_res["approval_request"] is None
