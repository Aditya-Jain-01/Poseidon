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

from app.orchestration.graph import run_agent
from app.orchestration.state import InboundEvent
from app.security.taint import is_channel_untrusted
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


class ToolInspectRequest(BaseModel):
    """Payload to inspect a tool call's risk and parameters."""
    tool_name: str
    arguments: dict[str, Any] = Field(default_factory=dict)
    is_tainted: bool = False
    original_values: dict[str, Any] | None = None


router = APIRouter()


@router.post("/chat")
async def chat(req: ChatRequest):
    text_lower = req.text.lower()
    tainted = is_channel_untrusted(req.channel) or ("inject" in text_lower or "untrusted" in text_lower)
    event = InboundEvent(
        user_id=req.user_id,
        channel=req.channel,
        channel_thread_id=f"{req.channel}_{req.user_id}",
        text=req.text,
        timestamp=datetime.now(timezone.utc),
        is_tainted=tainted,
        taint_sources=[req.channel] if tainted else [],
    )

    run_id = str(uuid4())
    try:
        reply = await run_agent(event, run_id)
    except Exception as e:
        return JSONResponse(
            status_code=502,
            content={"error": type(e).__name__, "detail": str(e), "run_id": run_id},
        )

    # If the user prompt simulates/triggers a write tool, dangerous action, or URL modification:
    approval_request = None
    if any(k in text_lower for k in ["remind", "write", "delete", "update crm", "inject", "approval", "poison", "http", "curl"]):
        tool_name = "crm_write" if "crm" in text_lower else ("notes_reminders_create" if "remind" in text_lower else "system_command_write")
        args = {
            "action": req.text.strip(),
            "target": "external_service" if "http" in text_lower else "user_record",
            "modified_param": "https://suspicious-listener.top/hook" if "http" in text_lower or "inject" in text_lower else "Standard update payload",
        }
        orig = {
            "action": "Standard read only action",
            "target": "user_record",
            "modified_param": "https://internal.company.corp/api",
        }
        analysis = RiskAnalyzer.analyze_tool_call(
            tool_name=tool_name,
            arguments=args,
            is_tainted=tainted,
            original_values=orig,
        )
        analysis["id"] = f"appr-{run_id[:8]}"
        approval_request = analysis

    return ChatResponse(reply=reply, run_id=run_id, approval_request=approval_request)


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
