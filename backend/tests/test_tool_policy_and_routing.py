"""Regression coverage for the M3/M5 authority boundaries."""
import pytest

from app.models import ActorContext, ConversationKey, ToolCall, ToolExecutionContext
from app.orchestration.router import UnknownAgentError, route_request
from app.tools.policy import ToolPolicyService


def context(tainted=False):
    return ToolExecutionContext(
        actor=ActorContext(owner_id='local_owner', is_operator=True),
        conversation_key=ConversationKey(owner_id='local_owner', channel='web', channel_account_id='local_browser', thread_id='policy-test'),
        run_id='policy-run', agent_id='poseidon', is_tainted=tainted,
    )


def test_policy_denies_unknown_and_unpermitted_tools():
    service = ToolPolicyService()
    assert service.evaluate(ToolCall(id='1', name='not_a_tool'), context(), agent_allowed_tools=['*'], calls_used=0, max_calls=5).decision == 'deny'
    assert service.evaluate(ToolCall(id='2', name='calendar_read'), context(), agent_allowed_tools=[], calls_used=0, max_calls=5).decision == 'deny'


def test_policy_requires_approval_for_tainted_side_effects():
    decision = ToolPolicyService().evaluate(
        ToolCall(id='1', name='notes_reminders_create', arguments={'kind': 'note', 'text': 'ordinary note'}),
        context(tainted=True), agent_allowed_tools=['notes_reminders_create'], calls_used=0, max_calls=5,
    )
    assert decision.decision == 'require_approval'


def test_explicit_unknown_agent_never_falls_back():
    with pytest.raises(UnknownAgentError):
        route_request('hello', explicit_agent_id='does-not-exist')
