"""AgentState — the Working Memory schema for LangGraph.

Assembled fresh per run, discarded after the reply is sent.
This TypedDict is the state that flows through every node in the graph.
"""

from datetime import datetime
from typing import Annotated
from typing_extensions import TypedDict
from pydantic import BaseModel, Field
from langgraph.graph.message import add_messages
from langchain_core.messages import BaseMessage


class InboundEvent(BaseModel):
    """The one internal event schema from spec §3.

    Every channel adapter produces this; the harness never sees
    anything channel-specific.
    """
    user_id: str
    channel: str
    channel_thread_id: str
    text: str
    timestamp: datetime
    is_tainted: bool = False
    taint_sources: list[str] = Field(default_factory=list)


class AgentState(TypedDict):
    """State passed through the LangGraph state machine.

    `messages` uses LangGraph's add_messages reducer so that each node
    can append to the conversation without overwriting what came before.
    """
    messages: Annotated[list[BaseMessage], add_messages]
    user_id: str
    channel: str
    run_id: str
    iteration_count: int
    tool_call_count: int
    is_tainted: bool
    taint_sources: list[str]
    pending_approvals: list[dict]
