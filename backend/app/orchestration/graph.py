"""Bounded agent execution harness with LangGraph approval pauses and resumption."""
from __future__ import annotations

import json
from typing import Any
from langchain_core.messages import AIMessage, ToolMessage
from langgraph.graph import END, START, StateGraph

from app.agents import qa_agent
from app.config import settings
from app.memory.memory_engine import memory_engine
from app.orchestration.approval_store import approval_store
from app.orchestration.state import AgentState, InboundEvent
from app.orchestration.trajectory import trajectory_store
from app.security.dlp import DLPScanner
from app.security.risk_analyzer import RiskAnalyzer
from app.security.taint import is_channel_untrusted
from app.tools.registry import execute_tool, get_tier, get_tools_for_agent


DEFAULT_PRIMARY_AGENT = "poseidon"


async def agent_node(state: AgentState) -> dict:
    if state["iteration_count"] >= settings.poseidon_max_iterations:
        return {
            "messages": [AIMessage(content="I stopped because this request exceeded the configured execution limit.")],
            "current_tool_call": None,
        }
    agent = state.get("active_agent") or DEFAULT_PRIMARY_AGENT
    tools = get_tools_for_agent(agent)
    result = await qa_agent.call(agent, state["messages"], tools=tools)
    calls = result.get("tool_calls") or []
    trajectory_store.record(state["run_id"], "agent", agent_id=agent, tool_calls=len(calls))

    message = AIMessage(
        content=result.get("content") or "",
        tool_calls=[
            {"name": c["name"], "args": c.get("arguments", {}), "id": c.get("id", c["name"]), "type": "tool_call"}
            for c in calls
        ],
    )
    return {
        "messages": [message],
        "iteration_count": state["iteration_count"] + 1,
        "current_tool_call": calls[0] if calls else None,
    }


def next_step(state: AgentState) -> str:
    if not state.get("current_tool_call"):
        return "end"
    if state["tool_call_count"] >= settings.poseidon_max_tool_calls:
        return "limit"
    return "approval" if get_tier(state["current_tool_call"]["name"]) == "approval_required" else "execute"


async def approval_gate(state: AgentState) -> dict:
    call = state["current_tool_call"]
    analysis = RiskAnalyzer.analyze_tool_call(call["name"], call.get("arguments", {}), state["is_tainted"])
    request = approval_store.park(
        state["run_id"],
        call,
        {
            "active_agent": state.get("active_agent", DEFAULT_PRIMARY_AGENT),
            "user_id": state["user_id"],
            "channel": state["channel"],
            "messages": state["messages"],
            "iteration_count": state["iteration_count"],
            "tool_call_count": state["tool_call_count"],
            "is_tainted": state["is_tainted"],
            "taint_sources": state["taint_sources"],
            "tool_results": state["tool_results"],
        },
    )
    request.update(analysis)
    trajectory_store.record(
        state["run_id"],
        "approval_requested",
        agent_id=state["active_agent"],
        tool_name=call["name"],
        tool_args=call.get("arguments", {}),
        risk_level=analysis["risk_level"],
    )
    return {"pending_approvals": [request], "approval_status": "pending"}


async def tool_executor(state: AgentState) -> dict:
    call = state["current_tool_call"]
    try:
        result = await execute_tool(call["name"], call.get("arguments", {}))
    except Exception as exc:
        result = {"error": str(exc)}

    trajectory_store.record(
        state["run_id"],
        "tool_executed",
        agent_id=state["active_agent"],
        tool_name=call["name"],
        tool_args=call.get("arguments", {}),
        tool_result=result,
        risk_level=get_tier(call["name"]),
    )
    return {
        "messages": [
            ToolMessage(
                content=json.dumps(result, default=str),
                tool_call_id=call.get("id", call["name"]),
                name=call["name"],
            )
        ],
        "tool_results": [*state["tool_results"], {"tool_name": call["name"], "result": result}],
        "tool_call_count": state["tool_call_count"] + 1,
        "current_tool_call": None,
    }


async def limit_node(state: AgentState) -> dict:
    return {
        "messages": [AIMessage(content="I stopped because this request exceeded the configured tool-call limit.")],
        "current_tool_call": None,
    }


# LangGraph state machine — single primary agent execution loop
_builder = StateGraph(AgentState)
_builder.add_node("agent", agent_node)
_builder.add_node("tool_executor", tool_executor)
_builder.add_node("approval_gate", approval_gate)
_builder.add_node("limit", limit_node)

_builder.add_edge(START, "agent")
_builder.add_conditional_edges("agent", next_step, {
    "end": END,
    "approval": "approval_gate",
    "execute": "tool_executor",
    "limit": "limit",
})
_builder.add_edge("tool_executor", "agent")
_builder.add_edge("approval_gate", END)
_builder.add_edge("limit", END)
graph = _builder.compile()


def _initial_state(event: InboundEvent, run_id: str, agent_id: str = DEFAULT_PRIMARY_AGENT) -> AgentState:
    tainted = event.is_tainted or is_channel_untrusted(event.channel)
    sources = list(event.taint_sources)
    if tainted and event.channel not in sources:
        sources.append(event.channel)

    messages = memory_engine.hydrate_context(agent_id=agent_id, user_id=event.user_id, user_text=event.text)

    return {
        "messages": messages,
        "user_id": event.user_id,
        "channel": event.channel,
        "run_id": run_id,
        "iteration_count": 0,
        "tool_call_count": 0,
        "is_tainted": tainted,
        "taint_sources": sources,
        "pending_approvals": [],
        "active_agent": agent_id,
        "tool_results": [],
        "approval_status": "none",
        "current_tool_call": None,
    }


async def run_agent(event: InboundEvent, run_id: str, agent_id: str = DEFAULT_PRIMARY_AGENT) -> dict[str, Any]:
    """Execute one full turn of the agent harness."""
    result = await graph.ainvoke(_initial_state(event, run_id, agent_id))
    pending = result.get("pending_approvals", [])
    raw = "Awaiting your approval to continue." if pending else str(result["messages"][-1].content)
    safe = DLPScanner.scan_and_redact(raw).sanitized_text

    memory_engine.record_turn(
        user_id=event.user_id,
        user_text=event.text,
        reply=safe,
        run_id=run_id,
        channel=event.channel,
    )

    return {
        "reply": safe,
        "run_id": run_id,
        "active_agent": result.get("active_agent", agent_id),
        "approval_request": pending[0] if pending else None,
        "memory_context": memory_engine.get_last_memory_context(),
        "trajectory": trajectory_store.get(run_id),
    }


async def resume_approval(approval_id: str, decision: str) -> dict[str, Any]:
    """Resume a pending tool action. Re-enters LangGraph upon approval."""
    request = approval_store.resolve(approval_id, decision)
    context = request["context"]
    agent_id = context.get("active_agent", DEFAULT_PRIMARY_AGENT)

    trajectory_store.record(
        request["run_id"],
        "approval_resolved",
        agent_id=agent_id,
        tool_name=request["tool_name"],
        decision=decision,
    )

    if decision == "denied":
        return {
            "reply": "Action denied. No changes were made.",
            "run_id": request["run_id"],
            "active_agent": agent_id,
            "approval_request": None,
            "memory_context": memory_engine.get_last_memory_context(),
            "trajectory": trajectory_store.get(request["run_id"]),
        }

    # Execute tool under SandboxGuard
    tool_name = request["tool_name"]
    arguments = request.get("arguments", {})
    try:
        result = await execute_tool(tool_name, arguments)
    except Exception as exc:
        result = {"error": str(exc)}

    trajectory_store.record(
        request["run_id"],
        "tool_executed",
        agent_id=agent_id,
        tool_name=tool_name,
        tool_args=arguments,
        tool_result=result,
        risk_level="approval_required",
    )

    # Re-enter LangGraph: construct resumed state with ToolMessage
    tool_msg = ToolMessage(
        content=json.dumps(result, default=str),
        tool_call_id=request.get("tool_call", {}).get("id", tool_name),
        name=tool_name,
    )

    parked_messages = context.get("messages", [])
    resumed_state: AgentState = {
        "messages": [*parked_messages, tool_msg],
        "user_id": context["user_id"],
        "channel": context["channel"],
        "run_id": request["run_id"],
        "iteration_count": context.get("iteration_count", 0) + 1,
        "tool_call_count": context.get("tool_call_count", 0) + 1,
        "is_tainted": context.get("is_tainted", False),
        "taint_sources": context.get("taint_sources", []),
        "pending_approvals": [],
        "active_agent": agent_id,
        "tool_results": [*context.get("tool_results", []), {"tool_name": tool_name, "result": result}],
        "approval_status": "approved",
        "current_tool_call": None,
    }

    graph_res = await graph.ainvoke(resumed_state)
    pending = graph_res.get("pending_approvals", [])
    raw = "Awaiting your approval to continue." if pending else str(graph_res["messages"][-1].content)
    safe = DLPScanner.scan_and_redact(raw).sanitized_text

    user_text = next(
        (str(m.content) for m in reversed(parked_messages) if getattr(m, "type", "") in {"human", "user"}),
        "",
    )
    memory_engine.record_turn(
        user_id=context["user_id"],
        user_text=user_text,
        reply=safe,
        run_id=request["run_id"],
        channel=context["channel"],
    )

    return {
        "reply": safe,
        "run_id": request["run_id"],
        "active_agent": graph_res.get("active_agent", agent_id),
        "approval_request": pending[0] if pending else None,
        "memory_context": memory_engine.get_last_memory_context(),
        "trajectory": trajectory_store.get(request["run_id"]),
    }
