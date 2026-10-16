"""Web/CLI gateway adapter — the local dev channel.

Translates HTTP requests into InboundEvent and replies back as JSON.
This is the only file that knows about HTTP/REST; the harness and
everything downstream only see InboundEvent.
"""

from datetime import datetime, timezone
from typing import Any
from typing import Literal
from uuid import uuid4

import logging
from fastapi import APIRouter, Request, Depends
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from app.orchestration.graph import run_agent, resume_approval
from app.orchestration.state import InboundEvent
from app.models import ActorContext, ConversationKey, Identifier
from app.security.identity import resolve_actor
from app.security.secrets import redact
from app.security.taint import calculate_overall_risk
from app.security.risk_analyzer import RiskAnalyzer
from app.security.guardrails import guardrail_store, GuardrailRateLimitError, HarnessPausedError


class ChatRequest(BaseModel):
    """What the caller sends to POST /chat."""
    text: str
    user_id: str = Field(default="local_user")
    channel: str = Field(default="web")
    thread_id: Identifier | None = None
    agent_id: Identifier | None = None


class ChatResponse(BaseModel):
    """What POST /chat returns."""
    reply: str
    run_id: str
    approval_request: dict[str, Any] | None = None
    active_agent: str = "poseidon"
    memory_context: dict[str, Any] | None = None
    trajectory: list[dict[str, Any]] | None = None
    thread_id: str
    conversation_key: ConversationKey


class ApprovalDecisionRequest(BaseModel):
    approval_id: Identifier
    decision: Literal['approved', 'denied']


class ToolInspectRequest(BaseModel):
    """Payload to inspect a tool call's risk and parameters."""
    tool_name: str
    arguments: dict[str, Any] = Field(default_factory=dict)
    is_tainted: bool = False
    original_values: dict[str, Any] | None = None


router = APIRouter()


from app.security.audit import audit_service


@router.post("/chat")
async def chat(req: ChatRequest, request: Request, actor: ActorContext = Depends(resolve_actor)):
    risk_info = calculate_overall_risk('web', req.text)
    tainted = risk_info["is_tainted"]
    event = InboundEvent(
        actor=actor,
        conversation_key=ConversationKey(owner_id=actor.owner_id, channel='web', channel_account_id='local_browser', thread_id=req.thread_id or 'default'),
        text=req.text,
        timestamp=datetime.now(timezone.utc),
        is_tainted=tainted,
        taint_sources=["content_risk"] if tainted else [],
    )
    if req.thread_id is None:
        logging.getLogger(__name__).warning('Chat without thread_id is deprecated; using compatibility default thread')

    run_id = str(uuid4())
    audit_service.record_event(
        run_id=run_id,
        owner_id=actor.owner_id,
        channel='web',
        direction='inbound',
        event_type='chat_request',
        status='received',
        agent_id=req.agent_id,
        payload={'text': req.text, 'thread_id': req.thread_id or 'default'},
    )
    command = req.text.strip().lower()
    if command in {'/pause', '/resume', '/status'}:
        if command == '/pause':
            guardrail_store.set_paused(True)
        elif command == '/resume':
            guardrail_store.set_paused(False)
        paused = guardrail_store.is_paused()
        reply = ('Poseidon is paused. Tool execution is disabled until /resume.' if paused
                 else 'Poseidon is active. Tool execution is enabled.')
        audit_service.record_event(run_id=run_id, owner_id=actor.owner_id, channel='web',
                                   direction='internal', event_type='guardrail_command', status='completed',
                                   payload={'command': command, 'paused': paused})
        return ChatResponse(reply=reply, run_id=run_id, thread_id=event.conversation_key.thread_id,
                            conversation_key=event.conversation_key)
    try:
        from app.orchestration.router import route_request, UnknownAgentError
        target_agent = route_request(req.text, explicit_agent_id=req.agent_id)
        result = await run_agent(event, run_id, agent_id=target_agent)
    except UnknownAgentError as e:
        audit_service.record_event(
            run_id=run_id,
            owner_id=actor.owner_id,
            channel='web',
            direction='outbound',
            event_type='unknown_agent_error',
            status='failed',
            payload={'agent_id': e.agent_id, 'available': e.available},
        )
        return JSONResponse(status_code=422, content={"error": "unknown_agent", "agent_id": e.agent_id, "available_agent_ids": e.available, "run_id": run_id})
    except (GuardrailRateLimitError, HarnessPausedError) as e:
        return JSONResponse(status_code=429 if isinstance(e, GuardrailRateLimitError) else 423,
                            content={"error": type(e).__name__, "detail": str(e), "run_id": run_id})
    except Exception as e:
        audit_service.record_event(
            run_id=run_id,
            owner_id=actor.owner_id,
            channel='web',
            direction='outbound',
            event_type='chat_error',
            status='failed',
            payload={'error': type(e).__name__, 'detail': redact(str(e))},
        )
        return JSONResponse(
            status_code=502,
            content={"error": type(e).__name__, "detail": redact(str(e)), "run_id": run_id},
        )

    audit_service.record_event(
        run_id=run_id,
        owner_id=actor.owner_id,
        channel='web',
        direction='outbound',
        event_type='chat_response',
        status='awaiting_approval' if result.get('approval_request') else 'completed',
        agent_id=result.get('active_agent'),
        payload={'reply': result.get('reply'), 'has_approval': bool(result.get('approval_request'))},
    )
    return ChatResponse(**result)


@router.post("/chat/approve")
async def approve(req: ApprovalDecisionRequest, actor: ActorContext = Depends(resolve_actor)):
    """Resolve a real pending tool action. Silence never executes the action."""
    audit_service.record_event(
        run_id=req.approval_id,
        owner_id=actor.owner_id,
        channel='web',
        direction='inbound',
        event_type='approval_decision',
        status=req.decision,
        payload={'approval_id': req.approval_id, 'decision': req.decision},
    )
    try:
        res = await resume_approval(req.approval_id, req.decision, owner_id=actor.owner_id)
        audit_service.record_event(
            run_id=res.get('run_id', req.approval_id),
            owner_id=actor.owner_id,
            channel='web',
            direction='outbound',
            event_type='approval_resolved',
            status='completed',
            payload={'reply': res.get('reply')},
        )
        return res
    except KeyError as exc:
        return JSONResponse(status_code=404, content={"error": redact(str(exc))})
    except ValueError as exc:
        return JSONResponse(status_code=422, content={"error": redact(str(exc))})
    except HarnessPausedError as exc:
        return JSONResponse(status_code=423, content={"error": str(exc)})


@router.get('/security/guardrails')
async def guardrail_status(actor: ActorContext = Depends(resolve_actor)):
    alerts = audit_service.query_events(owner_id=actor.owner_id, run_id='guardrails', limit=10)
    return {'paused': guardrail_store.is_paused(),
            'limit_alerts': [event for event in alerts if event['event_type'] == 'guardrail_limit']}


@router.post('/security/guardrails/pause')
async def pause_guardrails(actor: ActorContext = Depends(resolve_actor)):
    guardrail_store.set_paused(True)
    audit_service.record_event(run_id='guardrails', owner_id=actor.owner_id, channel='web',
                               direction='internal', event_type='guardrails_paused', status='completed')
    return {'paused': True}


@router.post('/security/guardrails/resume')
async def resume_guardrails(actor: ActorContext = Depends(resolve_actor)):
    guardrail_store.set_paused(False)
    audit_service.record_event(run_id='guardrails', owner_id=actor.owner_id, channel='web',
                               direction='internal', event_type='guardrails_resumed', status='completed')
    return {'paused': False}


@router.post("/security/inspect-tool")
async def inspect_tool(req: ToolInspectRequest):
    """Evaluate tool invocation risk, dangerous parameters, and diffs."""
    analysis = RiskAnalyzer.analyze_tool_call(
        tool_name=req.tool_name,
        arguments=req.arguments,
        is_tainted=req.is_tainted,
        original_values=req.original_values,
    )
    return redact(analysis)
