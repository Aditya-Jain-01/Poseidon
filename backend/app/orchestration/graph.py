"""LangGraph state machine — the harness that drives each agent run.

Sprint 1: single node (agent → reply). No tools, no conditional routing.
The graph takes an InboundEvent, assembles Working Memory, calls the LLM,
saves the exchange in session history, and returns the reply.
"""

from langgraph.graph import StateGraph, START, END
from langchain_core.messages import AIMessage

from app.orchestration.state import AgentState, InboundEvent
from app.memory.working_memory import assemble, session_store
from app.agents import qa_agent


async def agent_node(state: AgentState) -> dict:
    """The single LLM call node. Sends Working Memory, gets a reply."""
    reply_text = await qa_agent.call(state["messages"])
    return {
        "messages": [AIMessage(content=reply_text)],
        "iteration_count": state["iteration_count"] + 1,
    }


# Build the graph: START → agent → END
_builder = StateGraph(AgentState)
_builder.add_node("agent", agent_node)
_builder.add_edge(START, "agent")
_builder.add_edge("agent", END)
graph = _builder.compile()


async def run_agent(event: InboundEvent, run_id: str) -> str:
    """Entry point called by the gateway adapter.

    Assembles Working Memory from the event, invokes the graph,
    persists the exchange in session history, and returns the reply.
    """
    messages = assemble(event.text, event.user_id)

    initial_state: AgentState = {
        "messages": messages,
        "user_id": event.user_id,
        "channel": event.channel,
        "run_id": run_id,
        "iteration_count": 0,
        "tool_call_count": 0,
    }

    result = await graph.ainvoke(initial_state)

    # The last message in the list is the AI reply
    reply_text = result["messages"][-1].content

    # Save to in-session history (lost on restart)
    session_store.append(event.user_id, event.text, reply_text)

    return reply_text
