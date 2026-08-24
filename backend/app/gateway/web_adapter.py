"""Web/CLI gateway adapter — the local dev channel.

Translates HTTP requests into InboundEvent and replies back as JSON.
This is the only file that knows about HTTP/REST; the harness and
everything downstream only see InboundEvent.
"""

from datetime import datetime, timezone
from uuid import uuid4

from fastapi import APIRouter
from pydantic import BaseModel, Field

from app.orchestration.graph import run_agent
from app.orchestration.state import InboundEvent


class ChatRequest(BaseModel):
    """What the caller sends to POST /chat."""
    text: str
    user_id: str = Field(default="local_user")


class ChatResponse(BaseModel):
    """What POST /chat returns."""
    reply: str
    run_id: str


router = APIRouter()


@router.post("/chat", response_model=ChatResponse)
async def chat(req: ChatRequest) -> ChatResponse:
    event = InboundEvent(
        user_id=req.user_id,
        channel="web",
        channel_thread_id=f"web_{req.user_id}",
        text=req.text,
        timestamp=datetime.now(timezone.utc),
    )

    run_id = str(uuid4())
    reply = await run_agent(event, run_id)

    return ChatResponse(reply=reply, run_id=run_id)
