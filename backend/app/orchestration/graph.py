"""Injected, checkpointed LangGraph runtime with native interrupt/resume."""
from __future__ import annotations
import asyncio
from dataclasses import dataclass, field
import json
from typing import Any, Callable
from langchain_core.messages import AIMessage, ToolMessage
from langgraph.graph import END, START, StateGraph
from langgraph.types import Command, interrupt
from app.agents import qa_agent
from app.config import settings
from app.models import InboundEvent, ConversationKey, ToolCall, ToolExecutionContext, ApprovalDecision, RunResult
from app.memory.memory_engine import memory_engine
from app.orchestration.approval_store import ApprovalStore, ExecutionStore
from app.orchestration.state import AgentState
from app.orchestration.trajectory import trajectory_store
from app.security.risk_analyzer import RiskAnalyzer
from app.security.note_guard import NoteGuard
from app.security.secrets import redact
from app.security.sandbox import ExecutionTimeoutError
from app.security.taint import is_channel_untrusted
from app.tools.registry import get_tool, get_tools_for_agent
from app.tools.policy import ToolPolicyService
from app.tools.execution import ToolExecutionService

DEFAULT_PRIMARY_AGENT = 'poseidon'


@dataclass
class HarnessServices:
    memory: Any = field(default_factory=lambda: memory_engine)
    approvals: ApprovalStore = field(default_factory=ApprovalStore)
    executions: ExecutionStore | None = None
    llm_call: Callable | None = None
    tool_executor: Callable | None = None
    tool_schemas: Callable | None = None
    tool_tier: Callable | None = None
    tool_policy: ToolPolicyService = field(default_factory=ToolPolicyService)
    tool_execution_service: ToolExecutionService = field(default_factory=ToolExecutionService)

    def __post_init__(self):
        if self.executions is None:
            self.executions = ExecutionStore(self.approvals.db_path)


def _allowed(services, agent_id, name):
    schemas = (services.tool_schemas or get_tools_for_agent)(agent_id)
    return name in {s['function']['name'] for s in schemas}


def _allowed_names(services, agent_id):
    return [s['function']['name'] for s in (services.tool_schemas or get_tools_for_agent)(agent_id)]


def _tool_message(call, result):
    return ToolMessage(content=json.dumps(result, default=str), tool_call_id=call['id'], name=call['name'], id=f"result:{call['id']}")


def _finish_call(state, result, *, external_result=False, uncertain=False):
    call = state['current_tool_call']
    messages = [_tool_message(call, result)]
    if uncertain:
        messages.append(AIMessage(content='The tool outcome is uncertain. Check whether the action happened before trying it again.'))
    return {'messages': messages, 'tool_results': [*state['tool_results'], {'tool_call_id': call['id'], 'tool_name': call['name'], 'result': result}],
            'tool_call_count': state['tool_call_count'] + 1, 'current_tool_call': None, 'approval_status': '', 'policy_decision': {},
            'is_tainted': state['is_tainted'] or external_result,
            'taint_sources': list(dict.fromkeys([*state['taint_sources'], *([call['name']] if external_result else [])]))}


def build_graph(checkpointer, services):
    """Every runtime receives its saver and dependencies explicitly."""
    if checkpointer is None:
        raise ValueError('A checkpointer is required; tests must inject a deliberate saver')

    async def agent_node(state):
        if state['iteration_count'] >= settings.poseidon_max_iterations:
            return {'messages': [AIMessage(content='I stopped because this request exceeded the configured execution limit.')], 'pending_tool_calls': [], 'current_tool_call': None}
        result = await (services.llm_call or qa_agent.call)(state['active_agent'], state['messages'], tools=(services.tool_schemas or get_tools_for_agent)(state['active_agent']))
        calls = []
        for call in result.get('tool_calls') or []:
            calls.append(ToolCall.model_validate(call).model_dump())
        if len({c['id'] for c in calls}) != len(calls):
            raise ValueError('Duplicate tool-call IDs in a model response')
        previous_ids = {r['tool_call_id'] for r in state['tool_results']}
        if previous_ids.intersection(c['id'] for c in calls):
            raise ValueError('Tool-call IDs must be unique within a run')
        message = AIMessage(content=result.get('content') or '', tool_calls=[{'id': c['id'], 'name': c['name'], 'args': c['arguments'], 'type': 'tool_call'} for c in calls])
        trajectory_store.record(state['run_id'], 'agent', agent_id=state['active_agent'], conversation_key=state['conversation_key'], tool_calls=len(calls))
        return {'messages': [message], 'iteration_count': state['iteration_count'] + 1, 'pending_tool_calls': calls, 'current_tool_call': None}

    async def select_call(state):
        queue = list(state.get('pending_tool_calls', []))
        if not queue:
            return {'current_tool_call': None}
        if state['tool_call_count'] >= settings.poseidon_max_tool_calls:
            # Close the model protocol for every unexecuted call before stopping.
            result = {'error': 'tool_call_limit', 'detail': 'Configured tool-call limit reached'}
            return {'messages': [*[_tool_message(c, result) for c in queue], AIMessage(content='I stopped because this request exceeded the configured tool-call limit.')],
                    'tool_results': [*state['tool_results'], *[{'tool_call_id': c['id'], 'tool_name': c['name'], 'result': result} for c in queue]],
                    'pending_tool_calls': [], 'current_tool_call': None, 'policy_decision': {'decision': 'limit'}}
        call = queue.pop(0)
        context = ToolExecutionContext(actor=state['actor'], conversation_key=state['conversation_key'], run_id=state['run_id'], agent_id=state['active_agent'], is_tainted=state['is_tainted'], taint_sources=state['taint_sources'])
        # Tests may deliberately inject a policy-tier double. Production has
        # no override and always uses the authoritative ToolPolicyService.
        if services.tool_tier is not None:
            tier = services.tool_tier(call['name'])
            policy = {'decision': 'require_approval' if tier == 'approval_required' else 'allow', 'reasons': [], 'policy_version': 'test-adapter'}
            if tier == 'guarded_auto' and call['name'] == 'notes_reminders_create':
                verdict = NoteGuard.inspect(call['arguments'].get('text', ''))
                if verdict.verdict == 'reject':
                    policy = {'decision': 'deny', 'reasons': verdict.reasons, 'policy_version': 'test-adapter'}
                elif verdict.verdict == 'suspicious':
                    policy = {'decision': 'require_approval', 'reasons': verdict.reasons, 'policy_version': 'test-adapter'}
        else:
            policy = services.tool_policy.evaluate(call, context, agent_allowed_tools=_allowed_names(services, state['active_agent']), calls_used=state['tool_call_count'], max_calls=settings.poseidon_max_tool_calls).model_dump()
        return {'pending_tool_calls': queue, 'current_tool_call': call, 'policy_decision': policy, 'approval_status': ''}

    def route_call(state):
        if not state.get('current_tool_call'):
            return 'limit' if state.get('policy_decision', {}).get('decision') == 'limit' else 'end'
        return 'approval' if state['policy_decision']['decision'] == 'require_approval' else 'execute'

    async def approval_gate(state):
        call = state['current_tool_call']
        request = services.approvals.park(state['run_id'], call, state)
        request.update(redact(RiskAnalyzer.analyze_tool_call(call['name'], call['arguments'], state['is_tainted'])))
        request['reasons'] = redact(state['policy_decision'].get('reasons', []))
        # LangGraph replays this node on resume. Persisting the request is idempotent;
        # all tool side effects occur in the following node, after the interrupt.
        decision = ApprovalDecision.model_validate(interrupt(request))
        if decision.approval_id != request['id']:
            raise ValueError('Resume decision does not match the interrupted approval')
        row = services.approvals.get(request['id'])
        services.approvals.validate(row, state['user_id'], call, state['conversation_key'], policy_version=state['policy_decision'].get('policy_version'))
        if row['status'] not in {decision.decision, 'consumed' if decision.decision == 'approved' else 'denied'}:
            raise ValueError('Approval decision was not resolved by the trusted endpoint')
        if not _allowed(services, state['active_agent'], call['name']):
            return {'approval_status': 'denied', 'policy_decision': {'decision': 'deny', 'reasons': ['Agent permission revoked']}}
        return {'approval_status': decision.decision, 'pending_approvals': []}

    async def tool_executor(state):
        call = state['current_tool_call']
        tool = get_tool(call['name'])
        external_result = bool(tool and tool['trusted_provenance'] != 'built_in')
        if state['policy_decision']['decision'] == 'deny' or state.get('approval_status') == 'denied':
            return _finish_call(state, {'error': 'denied', 'detail': 'Action denied. No changes were made.'})
        if not _allowed(services, state['active_agent'], call['name']):
            return _finish_call(state, {'error': 'permission_denied'})
        if state['tool_call_count'] >= settings.poseidon_max_tool_calls:
            return _finish_call(state, {'error': 'tool_call_limit'})
        previous = services.executions.get(state['run_id'], call)
        if previous and previous['status'] in {'completed', 'failed'}:
            return _finish_call(state, json.loads(previous['result_json']), external_result=external_result)
        if state.get('approval_status') == 'approved':
            request = services.approvals.park(state['run_id'], call, state)
            services.approvals.consume(request['id'], state['user_id'], call, state['conversation_key'], policy_version=state['policy_decision'].get('policy_version'))
        if not services.executions.claim(state['run_id'], call):
            previous = services.executions.get(state['run_id'], call)
            result = json.loads(previous['result_json']) if previous and previous['result_json'] else {'error': 'execution_uncertain', 'detail': 'An earlier execution has no durable terminal result; it will not be repeated automatically.'}
            return _finish_call(state, result, external_result=external_result if previous and previous['result_json'] else False, uncertain=result.get('error') == 'execution_uncertain')
        arguments = dict(call['arguments'])
        # Legacy NoteGuard expects this internal flag. It is never model-visible.
        if call['name'] == 'notes_reminders_create' and state.get('approval_status') == 'approved':
            arguments['_operator_approved'] = True
        uncertain = False
        try:
            if services.tool_executor:
                result = await services.tool_executor(call['name'], arguments)
            else:
                context = ToolExecutionContext(actor=state['actor'], conversation_key=state['conversation_key'], run_id=state['run_id'], agent_id=state['active_agent'], is_tainted=state['is_tainted'], taint_sources=state['taint_sources'])
                result = await services.tool_execution_service.execute(call, context, approval_granted=state.get('approval_status') == 'approved')
            result = json.loads(json.dumps(result, default=str))
        except ExecutionTimeoutError:
            uncertain = True
            result = {'error': 'execution_uncertain', 'detail': 'The tool timed out; its outcome is unknown. Check before trying again.'}
        except Exception as exc:
            uncertain = bool(tool and tool['has_side_effects'])
            result = ({'error': 'execution_uncertain', 'detail': 'The tool failed after execution began; its outcome is unknown. Check before trying again.'}
                      if uncertain else {'error': type(exc).__name__, 'detail': redact(str(exc))})
        result = redact(result)
        if not uncertain:
            services.executions.complete(state['run_id'], call, result)
        trajectory_store.record(state['run_id'], 'tool_uncertain' if uncertain else 'tool_executed', agent_id=state['active_agent'], conversation_key=state['conversation_key'], tool_name=call['name'], tool_result=result)
        return _finish_call(state, result, external_result=external_result and not uncertain, uncertain=uncertain)

    def after_tool(state):
        last_result = state['tool_results'][-1]['result']
        if isinstance(last_result, dict) and last_result.get('error') == 'execution_uncertain':
            return 'end'
        return 'select' if state.get('pending_tool_calls') else 'agent'

    builder = StateGraph(AgentState)
    builder.add_node('agent', agent_node)
    builder.add_node('select', select_call)
    builder.add_node('approval', approval_gate)
    builder.add_node('execute', tool_executor)
    builder.add_edge(START, 'agent')
    builder.add_conditional_edges('agent', lambda s: 'select' if s.get('pending_tool_calls') else 'end', {'select': 'select', 'end': END})
    builder.add_conditional_edges('select', route_call, {'approval': 'approval', 'execute': 'execute', 'end': END, 'limit': END})
    builder.add_edge('approval', 'execute')
    builder.add_conditional_edges('execute', after_tool, {'select': 'select', 'agent': 'agent', 'end': END})
    return builder.compile(checkpointer=checkpointer)


class HarnessRuntime:
    def __init__(self, checkpointer, services=None):
        self.services = services or HarnessServices()
        self.graph = build_graph(checkpointer, self.services)
        self._locks: dict[str, asyncio.Lock] = {}

    def lock(self, run_id):
        return self._locks.setdefault(run_id, asyncio.Lock())

    @staticmethod
    def config(run_id):
        return {'configurable': {'thread_id': run_id}, 'recursion_limit': 20 + settings.poseidon_max_iterations * (settings.poseidon_max_tool_calls + 2) * 5}

    async def reconcile_approvals(self):
        for request in self.services.approvals.pending():
            snapshot = await self.graph.aget_state(self.config(request['run_id']))
            if not snapshot.next or not snapshot.values:
                self.services.approvals.invalidate(request['approval_id'])


_runtime: HarnessRuntime | None = None


def set_runtime(runtime):
    """Application lifespan (or a deliberate test fixture) installs the runtime."""
    global _runtime
    _runtime = runtime


def get_runtime(runtime=None):
    resolved = runtime or _runtime
    if resolved is None:
        raise RuntimeError('Harness runtime is unavailable; start the application lifespan')
    return resolved


def _initial_state(event, run_id, agent_id, services):
    hydrated = services.memory.hydrate_context(agent_id=agent_id, user_id=event.user_id, user_text=event.text, conversation_key=event.conversation_key)
    tainted = event.is_tainted or is_channel_untrusted(event.channel)
    return {'messages': list(hydrated.messages), 'user_id': event.user_id, 'channel': event.channel, 'run_id': run_id,
            'conversation_key': event.conversation_key.model_dump(), 'actor': event.actor.model_dump(), 'user_text': event.text,
            'iteration_count': 0, 'tool_call_count': 0, 'is_tainted': tainted,
            'taint_sources': list(dict.fromkeys([*event.taint_sources, *([event.channel] if tainted else [])])),
            'pending_approvals': [], 'active_agent': agent_id, 'tool_results': [], 'approval_status': '',
            'current_tool_call': None, 'pending_tool_calls': [], 'memory_context': hydrated.telemetry, 'policy_decision': {}}


def _response(result, runtime):
    interrupts = result.get('__interrupt__', ())
    request = redact(interrupts[0].value) if interrupts else None
    safe = 'Awaiting your approval to continue.' if request else redact(str(result['messages'][-1].content))
    key = ConversationKey.model_validate(result['conversation_key'])
    if request is None:
        runtime.services.memory.record_turn(user_id=result['user_id'], user_text=result['user_text'], reply=safe, run_id=result['run_id'], channel=result['channel'], conversation_key=key)
    return RunResult(reply=safe, run_id=result['run_id'], active_agent=result['active_agent'], thread_id=key.thread_id,
                     conversation_key=key, approval_request=request, memory_context=result['memory_context'], trajectory=trajectory_store.get(result['run_id'])).model_dump()


async def run_agent(event: InboundEvent, run_id: str, agent_id=DEFAULT_PRIMARY_AGENT, *, runtime=None):
    runtime = get_runtime(runtime)
    async with runtime.lock(run_id):
        config = runtime.config(run_id)
        snapshot = await runtime.graph.aget_state(config)
        if snapshot.values:
            if snapshot.values['conversation_key'] != event.conversation_key.model_dump() or snapshot.values['user_text'] != event.text or snapshot.values['active_agent'] != agent_id:
                raise ValueError('Run ID already belongs to another request')
            result = await runtime.graph.ainvoke(None, config) if snapshot.next else snapshot.values
        else:
            trajectory_store.record(run_id, 'route', agent_id=agent_id, conversation_key=event.conversation_key.model_dump())
            result = await runtime.graph.ainvoke(_initial_state(event, run_id, agent_id, runtime.services), config)
        return _response(result, runtime)


async def resume_approval(approval_id, decision, *, owner_id='local_owner', conversation_key=None, runtime=None):
    runtime = get_runtime(runtime)
    request = runtime.services.approvals.get(approval_id)
    async with runtime.lock(request['run_id']):
        request = runtime.services.approvals.get(approval_id)
        config = runtime.config(request['run_id'])
        snapshot = await runtime.graph.aget_state(config)
        if not snapshot.next or not snapshot.values or not snapshot.values.get('current_tool_call'):
            runtime.services.approvals.invalidate(approval_id)
            raise ValueError('Approval has no resumable checkpoint or was already consumed')
        state = snapshot.values
        runtime.services.approvals.validate(request, owner_id, state['current_tool_call'], state['conversation_key'], policy_version=state['policy_decision'].get('policy_version'))
        if runtime.services.tool_tier is None and request['policy_version'] != runtime.services.tool_policy.policy_version:
            raise ValueError('Approval policy version mismatch')
        if conversation_key is not None and conversation_key.model_dump() != state['conversation_key']:
            raise ValueError('Approval belongs to another conversation')
        runtime.services.approvals.resolve(approval_id, decision, owner_id=owner_id)
        # If the decision node was checkpointed before an interrupted executor,
        # continue that checkpoint instead of injecting a second interrupt value.
        interrupted = any(task.interrupts for task in snapshot.tasks)
        payload = Command(resume={'approval_id': approval_id, 'decision': decision}) if interrupted else None
        result = await runtime.graph.ainvoke(payload, config)
        return _response(result, runtime)
