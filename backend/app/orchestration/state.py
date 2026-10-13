"""AgentState — the Working Memory schema for LangGraph.

Assembled per run and persisted by the injected LangGraph checkpointer.
This TypedDict is the state that flows through every node in the graph.
"""

from typing import Annotated
from typing_extensions import TypedDict
from langgraph.graph.message import add_messages
from langchain_core.messages import BaseMessage
from app.models import InboundEvent


class AgentState(TypedDict):
    """State passed through the LangGraph state machine.

    `messages` uses LangGraph's add_messages reducer so that each node
    can append to the conversation without overwriting what came before.
    All other fields use replacement semantics: queues are replaced after each
    dequeue, and telemetry/policy decisions belong only to this run.
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
    active_agent: str
    tool_results: list[dict]
    approval_status: str
    current_tool_call: dict | None
    pending_tool_calls: list[dict]
    conversation_key: dict
    actor: dict
    user_text: str
    memory_context: dict
    policy_decision: dict
