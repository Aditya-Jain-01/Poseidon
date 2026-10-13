import asyncio
import json
from unittest.mock import AsyncMock
import pytest
from langgraph.checkpoint.memory import InMemorySaver
from langchain_core.messages import ToolMessage
from app.models import ConversationKey, ActorContext, InboundEvent
from app.orchestration.graph import HarnessRuntime, HarnessServices, run_agent, resume_approval
from app.orchestration.approval_store import ApprovalStore, ExecutionStore


def event(thread='test-thread', text='hello'):
    return InboundEvent(actor=ActorContext(owner_id='local_owner', is_operator=True),
                        conversation_key=ConversationKey(owner_id='local_owner', channel='web', channel_account_id='local_browser', thread_id=thread), text=text)


def call(name='calendar_create', id='c1', **arguments):
    return {'id': id, 'name': name, 'arguments': arguments}


def services(db, llm, executor=None, schemas=None, tier=None):
    allowed = schemas or ['calendar_create', 'calendar_read', 'crm_read', 'notes_reminders_create']
    return HarnessServices(approvals=ApprovalStore(db), llm_call=llm,
                           tool_executor=executor or AsyncMock(return_value={'ok': True}),
                           tool_schemas=lambda agent: [{'function': {'name': name}} for name in allowed],
                           tool_tier=tier or (lambda name: 'approval_required' if name == 'calendar_create' else 'guarded_auto' if name == 'notes_reminders_create' else 'auto'))


@pytest.mark.asyncio
async def test_multi_tool_order_pause_resume_and_replay(tmp_path):
    calls = [call('calendar_read', 'c1'), call('calendar_create', 'c2', title='Meeting'), call('crm_read', 'c3')]
    llm = AsyncMock(side_effect=[{'tool_calls': calls}, {'content': 'done'}])
    executor = AsyncMock(return_value={'ok': True})
    runtime = HarnessRuntime(InMemorySaver(), services(tmp_path / 'run.db', llm, executor))
    first = await run_agent(event(), 'ordered-run', runtime=runtime)
    assert first['approval_request']['tool_call_id'] == 'c2'
    assert executor.await_count == 1
    resumed = await resume_approval(first['approval_request']['id'], 'approved', runtime=runtime)
    assert resumed['reply'] == 'done'
    assert [c.args[0] for c in executor.await_args_list] == ['calendar_read', 'calendar_create', 'crm_read']
    tool_messages = [m for m in llm.await_args_list[-1].args[1] if isinstance(m, ToolMessage)]
    assert [m.tool_call_id for m in tool_messages] == ['c1', 'c2', 'c3']
    with pytest.raises(ValueError):
        await resume_approval(first['approval_request']['id'], 'approved', runtime=runtime)
    assert executor.await_count == 3
    await run_agent(event(), 'ordered-run', runtime=runtime)
    assert executor.await_count == 3


@pytest.mark.asyncio
async def test_denial_emits_matching_result_and_continues_queue(tmp_path):
    llm = AsyncMock(side_effect=[{'tool_calls': [call(id='denied-call'), call('crm_read', 'read-call')]}, {'content': 'Action denied.'}])
    executor = AsyncMock(return_value={})
    runtime = HarnessRuntime(InMemorySaver(), services(tmp_path / 'run.db', llm, executor))
    first = await run_agent(event(), 'denial-run', runtime=runtime)
    result = await resume_approval(first['approval_request']['id'], 'denied', runtime=runtime)
    assert result['approval_request'] is None
    assert [c.args[0] for c in executor.await_args_list] == ['crm_read']
    tool_messages = [m for m in llm.await_args_list[-1].args[1] if isinstance(m, ToolMessage)]
    assert tool_messages[0].tool_call_id == 'denied-call'
    assert json.loads(tool_messages[0].content)['error'] == 'denied'


@pytest.mark.asyncio
async def test_suspicious_note_interrupts_before_executor_or_next_llm(tmp_path):
    llm = AsyncMock(side_effect=[{'tool_calls': [call('notes_reminders_create', text='See https://example.com', kind='note')]}, {'content': 'saved'}])
    executor = AsyncMock(return_value={'created': True})
    runtime = HarnessRuntime(InMemorySaver(), services(tmp_path / 'note.db', llm, executor))
    first = await run_agent(event(), 'note-run', runtime=runtime)
    assert first['approval_request']
    assert llm.await_count == 1 and executor.await_count == 0
    await resume_approval(first['approval_request']['id'], 'approved', runtime=runtime)
    assert executor.await_args.args[1]['_operator_approved'] is True


@pytest.mark.asyncio
async def test_expiry_owner_and_argument_binding(tmp_path):
    from app.db.connection import connection
    llm = AsyncMock(return_value={'tool_calls': [call(title='Original')]})
    executor = AsyncMock()
    runtime = HarnessRuntime(InMemorySaver(), services(tmp_path / 'binding.db', llm, executor))
    first = await run_agent(event(), 'binding-run', runtime=runtime)
    aid = first['approval_request']['id']
    with pytest.raises(ValueError, match='owner'):
        await resume_approval(aid, 'approved', owner_id='forged', runtime=runtime)
    with pytest.raises(ValueError, match='conversation'):
        await resume_approval(aid, 'approved', conversation_key=event('other-thread').conversation_key, runtime=runtime)
    row = runtime.services.approvals.get(aid)
    with pytest.raises(ValueError, match='arguments'):
        runtime.services.approvals.validate(row, 'local_owner', call(title='Substituted'), event().conversation_key.model_dump())
    with connection(runtime.services.approvals.db_path) as conn:
        conn.execute("UPDATE approvals SET expires_at='2000-01-01T00:00:00+00:00'")
        conn.commit()
    with pytest.raises(ValueError, match='expired'):
        await resume_approval(aid, 'approved', runtime=runtime)
    executor.assert_not_awaited()


def test_execution_repository_survives_reconstruction_and_checks_arguments(tmp_path):
    db = tmp_path / 'execution.db'
    first = ExecutionStore(db)
    tc = call(title='Meeting')
    assert first.claim('r', tc)
    first.complete('r', tc, {'created': 'one-record'})
    second = ExecutionStore(db)
    assert not second.claim('r', tc)
    assert json.loads(second.get('r', tc)['result_json']) == {'created': 'one-record'}
    with pytest.raises(ValueError, match='changed'):
        second.get('r', call(title='Different'))


@pytest.mark.asyncio
async def test_tool_limit_closes_protocol_for_every_call(tmp_path, monkeypatch):
    from app.config import settings
    monkeypatch.setattr(settings, 'poseidon_max_tool_calls', 1)
    llm = AsyncMock(return_value={'tool_calls': [call('crm_read', f'c{i}') for i in range(3)]})
    executor = AsyncMock(return_value={})
    runtime = HarnessRuntime(InMemorySaver(), services(tmp_path / 'limit.db', llm, executor))
    result = await run_agent(event(), 'limit-run', runtime=runtime)
    snapshot = await runtime.graph.aget_state(runtime.config('limit-run'))
    assert [m.tool_call_id for m in snapshot.values['messages'] if isinstance(m, ToolMessage)] == ['c0', 'c1', 'c2']
    assert executor.await_count == 1
    assert 'limit' in result['reply']


@pytest.mark.asyncio
async def test_concurrent_memory_telemetry_is_request_local(tmp_path, monkeypatch):
    from app.memory.memory_engine import memory_engine
    monkeypatch.setattr(memory_engine.semantic_store, 'retrieve', lambda user_id, query: [{'fact': query}])
    monkeypatch.setattr(memory_engine.episodic_store, 'retrieve', lambda **kwargs: [])
    async def fake_llm(*args, **kwargs):
        await asyncio.sleep(0)
        return {'content': 'done'}
    runtime = HarnessRuntime(InMemorySaver(), services(tmp_path / 'concurrent.db', fake_llm))
    results = await asyncio.gather(run_agent(event('a', 'alpha'), 'ra', runtime=runtime), run_agent(event('b', 'beta'), 'rb', runtime=runtime))
    assert results[0]['memory_context']['semantic_facts'] == ['alpha']
    assert results[1]['memory_context']['semantic_facts'] == ['beta']
    assert not hasattr(memory_engine, '_last_context')


@pytest.mark.asyncio
async def test_conversation_history_isolated_and_recording_idempotent(tmp_path, monkeypatch):
    from app.memory.memory_engine import memory_engine
    from app.db.connection import connection
    monkeypatch.setattr(memory_engine.episodic_store, 'retrieve', lambda **kwargs: [])
    llm = AsyncMock(return_value={'content': 'first reply'})
    runtime = HarnessRuntime(InMemorySaver(), services(tmp_path / 'sessions.db', llm))
    await run_agent(event('a', 'session a message'), 'session-a-run', runtime=runtime)
    await run_agent(event('a', 'session a message'), 'session-a-run', runtime=runtime)
    hydrated_a = memory_engine.hydrate_context(user_id='local_owner', user_text='next', conversation_key=event('a').conversation_key)
    hydrated_b = memory_engine.hydrate_context(user_id='local_owner', user_text='next', conversation_key=event('b').conversation_key)
    assert [m.content for m in hydrated_a.messages[1:]] == ['session a message', 'first reply', 'next']
    assert [m.content for m in hydrated_b.messages[1:]] == ['next']
    with connection(memory_engine.episodic_store.db_path) as conn:
        assert conn.execute("SELECT COUNT(*) FROM episodic_events WHERE run_id='session-a-run'").fetchone()[0] == 2


@pytest.mark.asyncio
async def test_orphaned_approval_is_invalidated(tmp_path):
    store = ApprovalStore(tmp_path / 'orphan.db')
    request = store.park('missing-checkpoint', call(), {'conversation_key': event().conversation_key.model_dump()})
    runtime = HarnessRuntime(InMemorySaver(), services(store.db_path, AsyncMock()))
    await runtime.reconcile_approvals()
    assert store.get(request['id'])['status'] == 'expired'


@pytest.mark.asyncio
async def test_permission_revoked_before_resume_prevents_execution(tmp_path):
    permitted = ['calendar_create']
    deps = services(tmp_path / 'permissions.db', AsyncMock(side_effect=[{'tool_calls': [call()]}, {'content': 'Denied after revocation'}]))
    deps.tool_schemas = lambda agent: [{'function': {'name': name}} for name in permitted]
    runtime = HarnessRuntime(InMemorySaver(), deps)
    first = await run_agent(event(), 'permission-run', runtime=runtime)
    permitted.clear()
    await resume_approval(first['approval_request']['id'], 'approved', runtime=runtime)
    deps.tool_executor.assert_not_awaited()


def test_hydration_telemetry_cannot_mutate_other_requests(monkeypatch):
    from app.memory.memory_engine import memory_engine
    monkeypatch.setattr(memory_engine.episodic_store, 'retrieve', lambda **kwargs: [])
    monkeypatch.setattr(memory_engine.semantic_store, 'retrieve', lambda user_id, query: [{'fact': query}])
    hydrated = memory_engine.hydrate_context(user_text='alpha')
    modified = hydrated.telemetry
    modified['semantic_facts'].append('injected')
    assert hydrated.telemetry['semantic_facts'] == ['alpha']


@pytest.mark.asyncio
async def test_async_sqlite_interrupt_restart_resume_executes_once(tmp_path):
    sqlite = pytest.importorskip('langgraph.checkpoint.sqlite.aio', reason='SQLite checkpoint package is not installed in the supplied venv')
    db = tmp_path / 'restart.db'
    executor = AsyncMock(return_value={'created': 'one'})
    first_llm = AsyncMock(return_value={'tool_calls': [call(title='Meeting')]})
    async with sqlite.AsyncSqliteSaver.from_conn_string(str(db)) as saver:
        await saver.setup()
        runtime = HarnessRuntime(saver, services(db, first_llm, executor))
        first = await run_agent(event(), 'restart-run', runtime=runtime)
        aid = first['approval_request']['id']
        executor.assert_not_awaited()
    second_llm = AsyncMock(return_value={'content': 'Created after restart'})
    async with sqlite.AsyncSqliteSaver.from_conn_string(str(db)) as saver:
        await saver.setup()
        runtime = HarnessRuntime(saver, services(db, second_llm, executor))
        result = await resume_approval(aid, 'approved', runtime=runtime)
        assert result['reply'] == 'Created after restart'
        assert executor.await_count == 1
        with pytest.raises(ValueError):
            await resume_approval(aid, 'approved', runtime=runtime)
        assert executor.await_count == 1
