"""Durable pause and rate boundaries for the personal harness."""
import asyncio
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient
from langgraph.checkpoint.memory import InMemorySaver

from app.config import settings
from app.db.connection import connection
from app.db.migrations import apply_migrations
from app.gateway.telegram_adapter import deliver_reply, process_telegram_update
from app.main import app
from app.models import ActorContext, ConversationKey, InboundEvent
from app.orchestration.approval_store import ApprovalStore
from app.orchestration.graph import HarnessRuntime, HarnessServices, resume_approval, run_agent
from app.security.guardrails import GuardrailRateLimitError, GuardrailStore, HarnessPausedError, guardrail_store
from app.tools.registry import BASE_TOOL_REGISTRY, execute_tool


def test_documented_builtin_tiers_match_registry():
    doc = (Path(__file__).resolve().parents[2] / 'GUARDRAILS.md').read_text(encoding='utf-8')
    auto = doc.split('### Auto-run', 1)[1].split('### Guarded auto-run', 1)[0]
    guarded = doc.split('### Guarded auto-run', 1)[1].split('### Approval required', 1)[0]
    approval = doc.split('### Approval required', 1)[1].split('**No auto-trust promotion', 1)[0]
    sections = {'auto': auto, 'guarded_auto': guarded, 'approval_required': approval}
    for name, tool in BASE_TOOL_REGISTRY.items():
        assert f'- `{name}`' in sections[tool['base_tier']]


def test_pause_api_is_durable_and_blocks_direct_tool_execution():
    client = TestClient(app, client=('127.0.0.1', 50000))
    assert client.post('/security/guardrails/pause').json() == {'paused': True}
    assert GuardrailStore(settings.poseidon_db_path).is_paused()
    assert client.get('/security/guardrails').json()['paused'] is True
    with pytest.raises(HarnessPausedError):
        asyncio.run(execute_tool('crm_read', {'query': ''}))
    assert client.post('/security/guardrails/resume').json() == {'paused': False}
    with pytest.raises(PermissionError, match='read-only'):
        asyncio.run(execute_tool('calendar_create', {'title': 'No approval', 'starts_at': '2026-10-20T10:00:00Z'}))


def test_web_chat_pause_command_does_not_call_agent():
    client = TestClient(app, client=('127.0.0.1', 50000))
    with patch('app.gateway.web_adapter.run_agent', new_callable=AsyncMock) as run:
        paused = client.post('/chat', json={'text': '/pause', 'thread_id': 'control'})
        assert paused.status_code == 200
        assert guardrail_store.is_paused()
        assert client.post('/chat', json={'text': '/status', 'thread_id': 'control'}).status_code == 200
        resumed = client.post('/chat', json={'text': '/resume', 'thread_id': 'control'})
        assert resumed.status_code == 200
        assert not guardrail_store.is_paused()
        run.assert_not_awaited()


@pytest.mark.asyncio
async def test_pause_blocks_approval_grant_and_tool_execution():
    llm = AsyncMock(side_effect=[{'tool_calls': [{'id': 'c1', 'name': 'calendar_create',
                                                 'arguments': {'title': 'Meeting', 'starts_at': '2026-10-20T10:00:00Z'}}]},
                                 {'content': 'Action denied.'}])
    executor = AsyncMock(return_value={'ok': True})
    deps = HarnessServices(approvals=ApprovalStore(settings.poseidon_db_path), llm_call=llm,
                           tool_executor=executor,
                           tool_schemas=lambda _: [{'function': {'name': 'calendar_create'}}],
                           tool_tier=lambda _: 'approval_required')
    runtime = HarnessRuntime(InMemorySaver(), deps)
    event = InboundEvent(actor=ActorContext(owner_id='local_owner', is_operator=True),
                         conversation_key=ConversationKey(owner_id='local_owner', channel='web',
                                                          channel_account_id='local_browser', thread_id='pause-test'),
                         text='Create a meeting')
    first = await run_agent(event, 'pause-approval', runtime=runtime)
    aid = first['approval_request']['id']
    deps.guardrails.set_paused(True)
    with pytest.raises(HarnessPausedError):
        await resume_approval(aid, 'approved', runtime=runtime)
    assert deps.approvals.get(aid)['status'] == 'pending'
    executor.assert_not_awaited()
    await resume_approval(aid, 'denied', runtime=runtime)
    executor.assert_not_awaited()


def test_approval_limit_is_atomic_and_replays_do_not_count(tmp_path, monkeypatch):
    db = tmp_path / 'approval-limit.db'
    apply_migrations(db)
    monkeypatch.setattr(settings, 'poseidon_max_approval_requests_per_hour', 1)
    store = ApprovalStore(db)
    key = ConversationKey(owner_id='local_owner', channel='web', channel_account_id='local_browser', thread_id='limit')
    context = {'conversation_key': key.model_dump(), 'policy_decision': {'policy_version': '2'}}
    first_call = {'id': 'c1', 'name': 'calendar_create', 'arguments': {'title': 'One'}}
    first = store.park('r1', first_call, context)
    assert store.park('r1', first_call, context)['id'] == first['id']
    with pytest.raises(GuardrailRateLimitError):
        ApprovalStore(db).park('r2', {'id': 'c2', 'name': 'calendar_create', 'arguments': {}}, context)
    with pytest.raises(GuardrailRateLimitError):
        ApprovalStore(db).park('r3', {'id': 'c3', 'name': 'calendar_create', 'arguments': {}}, context)
    with connection(db) as conn:
        assert conn.execute("SELECT COUNT(*) FROM audit_events WHERE event_type='guardrail_limit'").fetchone()[0] == 1
        conn.execute("UPDATE approvals SET created_at='2000-01-01T00:00:00+00:00'")
        conn.commit()
    assert ApprovalStore(db).park('r2', {'id': 'c2', 'name': 'calendar_create', 'arguments': {}}, context)

    concurrent_db = tmp_path / 'concurrent-limit.db'
    apply_migrations(concurrent_db)
    def request(index):
        try:
            ApprovalStore(concurrent_db).park(f'run-{index}', {'id': f'call-{index}', 'name': 'calendar_create', 'arguments': {}}, context)
            return 'accepted'
        except GuardrailRateLimitError:
            return 'limited'
    with ThreadPoolExecutor(max_workers=2) as pool:
        assert sorted(pool.map(request, (1, 2))) == ['accepted', 'limited']


def test_outbound_limit_is_atomic_across_store_instances(tmp_path, monkeypatch):
    db = tmp_path / 'outbound-limit.db'
    apply_migrations(db)
    monkeypatch.setattr(settings, 'poseidon_outbound_msg_rate_limit', 1)
    def reserve(_index):
        try:
            GuardrailStore(db).reserve_outbound_attempt('telegram')
            return 'accepted'
        except GuardrailRateLimitError:
            return 'limited'
    with ThreadPoolExecutor(max_workers=2) as pool:
        assert sorted(pool.map(reserve, (1, 2))) == ['accepted', 'limited']
    with connection(db) as conn:
        assert conn.execute("SELECT COUNT(*) FROM audit_events WHERE event_type='guardrail_limit'").fetchone()[0] == 1


@pytest.mark.asyncio
async def test_telegram_send_limit_counts_failed_attempts_and_retries(monkeypatch):
    monkeypatch.setattr(settings, 'poseidon_outbound_msg_rate_limit', 1)
    with patch('app.gateway.telegram_adapter.send_telegram_reply', new_callable=AsyncMock) as send:
        send.return_value = False
        with pytest.raises(RuntimeError, match='delivery failed'):
            await deliver_reply('fake-token', 123, 'first')
        with pytest.raises(GuardrailRateLimitError):
            await deliver_reply('fake-token', 123, 'retry')
        send.assert_awaited_once()
    with connection(settings.poseidon_db_path) as conn:
        conn.execute("UPDATE outbound_attempts SET created_at='2000-01-01T00:00:00+00:00'")
        conn.commit()
    assert GuardrailStore(settings.poseidon_db_path).is_paused() is False
    guardrail_store.reserve_outbound_attempt('telegram')


@pytest.mark.asyncio
async def test_telegram_operator_can_pause_and_resume_without_running_agent(monkeypatch):
    monkeypatch.setattr(settings, 'telegram_allowed_user_ids', '12345')
    def update(text):
        return {'message': {'from': {'id': 12345}, 'chat': {'id': 12345}, 'text': text}}
    with patch('app.gateway.telegram_adapter.send_telegram_reply', new_callable=AsyncMock, return_value=True), \
         patch('app.gateway.telegram_adapter.run_agent', new_callable=AsyncMock) as run:
        paused = await process_telegram_update(update('/pause'), bot_token='fake-token')
        assert 'paused' in paused['reply']
        assert guardrail_store.is_paused()
        await process_telegram_update(update('/resume'), bot_token='fake-token')
        assert not guardrail_store.is_paused()
        run.assert_not_awaited()
