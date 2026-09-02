"""Web/CLI gateway adapter — the local dev channel.

Translates HTTP requests into InboundEvent and replies back as JSON.
This is the only file that knows about HTTP/REST; the harness and
everything downstream only see InboundEvent.
"""

from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from fastapi import APIRouter
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from app.orchestration.graph import run_agent, resume_approval
from app.orchestration.state import InboundEvent
from app.security.taint import is_channel_untrusted, calculate_overall_risk
from app.security.risk_analyzer import RiskAnalyzer


class ChatRequest(BaseModel):
    """What the caller sends to POST /chat."""
    text: str
    user_id: str = Field(default="local_user")
    channel: str = Field(default="web")


class ChatResponse(BaseModel):
    """What POST /chat returns."""
    reply: str
    run_id: str
    approval_request: dict[str, Any] | None = None
    active_agent: str = "octavious"


class ApprovalDecisionRequest(BaseModel):
    approval_id: str
    decision: str


class ToolInspectRequest(BaseModel):
    """Payload to inspect a tool call's risk and parameters."""
    tool_name: str
    arguments: dict[str, Any] = Field(default_factory=dict)
    is_tainted: bool = False
    original_values: dict[str, Any] | None = None


router = APIRouter()


@router.post("/chat")
async def chat(req: ChatRequest):
    risk_info = calculate_overall_risk(req.channel, req.text)
    tainted = risk_info["is_tainted"]
    event = InboundEvent(
        user_id=req.user_id,
        channel=req.channel,
        channel_thread_id=f"{req.channel}_{req.user_id}",
        text=req.text,
        timestamp=datetime.now(timezone.utc),
        is_tainted=tainted,
        taint_sources=[req.channel] if is_channel_untrusted(req.channel) else (["content_risk"] if tainted else []),
    )

    run_id = str(uuid4())
    try:
        result = await run_agent(event, run_id)
    except Exception as e:
        return JSONResponse(
            status_code=502,
            content={"error": type(e).__name__, "detail": str(e), "run_id": run_id},
        )

    return ChatResponse(**result)


@router.post("/chat/approve")
async def approve(req: ApprovalDecisionRequest):
    """Resolve a real pending tool action. Silence never executes the action."""
    try:
        return await resume_approval(req.approval_id, req.decision)
    except KeyError as exc:
        return JSONResponse(status_code=404, content={"error": str(exc)})
    except ValueError as exc:
        return JSONResponse(status_code=422, content={"error": str(exc)})


@router.post("/security/inspect-tool")
async def inspect_tool(req: ToolInspectRequest):
    """Evaluate tool invocation risk, dangerous parameters, and diffs."""
    analysis = RiskAnalyzer.analyze_tool_call(
        tool_name=req.tool_name,
        arguments=req.arguments,
        is_tainted=req.is_tainted,
        original_values=req.original_values,
    )
    return analysis
