"""Bounded multi-agent tool graph with real approval pauses."""
from __future__ import annotations
import json
from typing import Any
from langchain_core.messages import AIMessage, ToolMessage
from langgraph.graph import END, START, StateGraph
from app.agents import qa_agent
from app.config import settings
from app.memory.episodic_store import episodic_store
from app.memory.working_memory import assemble, session_store
from app.orchestration.approval_store import approval_store
from app.orchestration.router import route_request
from app.orchestration.state import AgentState, InboundEvent
from app.orchestration.trajectory import trajectory_store
from app.security.dlp import DLPScanner
from app.security.risk_analyzer import RiskAnalyzer
from app.security.taint import is_channel_untrusted
from app.soul import soul_store
from app.tools.registry import execute_tool, get_tier, get_tools_for_agent

async def router_node(state: AgentState) -> dict:
    text = next((str(m.content) for m in reversed(state["messages"]) if getattr(m, "type", "") in {"human", "user"}), "")
    agent = await route_request(text, soul_store.load_all_agents())
    trajectory_store.record(state["run_id"], "route", agent_id=agent)
    return {"active_agent": agent}

async def agent_node(state: AgentState) -> dict:
    if state["iteration_count"] >= settings.poseidon_max_iterations:
        return {"messages": [AIMessage(content="I stopped because this request exceeded the configured execution limit.")], "current_tool_call": None}
    agent = state["active_agent"]
    result = await qa_agent.call(agent, state["messages"], tools=get_tools_for_agent(agent))
    calls = result.get("tool_calls") or []
    trajectory_store.record(state["run_id"], "agent", agent_id=agent, tool_calls=len(calls))
    message = AIMessage(content=result.get("content") or "", tool_calls=[{"name": c["name"], "args": c.get("arguments", {}), "id": c["id"], "type": "tool_call"} for c in calls])
    return {"messages": [message], "iteration_count": state["iteration_count"] + 1, "current_tool_call": calls[0] if calls else None}

def next_step(state: AgentState) -> str:
    if not state.get("current_tool_call"): return "end"
    if state["tool_call_count"] >= settings.poseidon_max_tool_calls: return "limit"
    return "approval" if get_tier(state["current_tool_call"]["name"]) == "approval_required" else "execute"

async def approval_gate(state: AgentState) -> dict:
    call = state["current_tool_call"]
    analysis = RiskAnalyzer.analyze_tool_call(call["name"], call.get("arguments", {}), state["is_tainted"])
    request = approval_store.park(state["run_id"], call, {"active_agent": state["active_agent"], "user_id": state["user_id"], "channel": state["channel"]})
    request.update(analysis)
    trajectory_store.record(state["run_id"], "approval_requested", agent_id=state["active_agent"], tool_name=call["name"], tool_args=call.get("arguments", {}), risk_level=analysis["risk_level"])
    return {"pending_approvals": [request], "approval_status": "pending"}

async def tool_executor(state: AgentState) -> dict:
    call = state["current_tool_call"]
    try: result = execute_tool(call["name"], call.get("arguments", {}))
    except Exception as exc: result = {"error": str(exc)}
    trajectory_store.record(state["run_id"], "tool_executed", agent_id=state["active_agent"], tool_name=call["name"], tool_args=call.get("arguments", {}), tool_result=result, risk_level=get_tier(call["name"]))
    return {"messages": [ToolMessage(content=json.dumps(result, default=str), tool_call_id=call.get("id", call["name"]), name=call["name"])], "tool_results": [*state["tool_results"], {"tool_name": call["name"], "result": result}], "tool_call_count": state["tool_call_count"] + 1, "current_tool_call": None}

async def limit_node(state: AgentState) -> dict:
    return {"messages": [AIMessage(content="I stopped because this request exceeded the configured tool-call limit.")], "current_tool_call": None}

_builder = StateGraph(AgentState)
_builder.add_node("router", router_node); _builder.add_node("agent", agent_node); _builder.add_node("tool_executor", tool_executor); _builder.add_node("approval_gate", approval_gate); _builder.add_node("limit", limit_node)
_builder.add_edge(START, "router"); _builder.add_edge("router", "agent")
_builder.add_conditional_edges("agent", next_step, {"end": END, "approval": "approval_gate", "execute": "tool_executor", "limit": "limit"})
_builder.add_edge("tool_executor", "agent"); _builder.add_edge("approval_gate", END); _builder.add_edge("limit", END)
graph = _builder.compile()

def _initial_state(event: InboundEvent, run_id: str) -> AgentState:
    tainted = event.is_tainted or is_channel_untrusted(event.channel)
    sources = list(event.taint_sources)
    if tainted and event.channel not in sources: sources.append(event.channel)
    return {"messages": assemble(event.text, event.user_id), "user_id": event.user_id, "channel": event.channel, "run_id": run_id, "iteration_count": 0, "tool_call_count": 0, "is_tainted": tainted, "taint_sources": sources, "pending_approvals": [], "active_agent": "octavious", "tool_results": [], "approval_status": "none", "current_tool_call": None}

async def run_agent(event: InboundEvent, run_id: str) -> dict[str, Any]:
    result = await graph.ainvoke(_initial_state(event, run_id))
    pending = result.get("pending_approvals", [])
    raw = "Awaiting your approval to continue." if pending else str(result["messages"][-1].content)
    safe = DLPScanner.scan_and_redact(raw).sanitized_text
    session_store.append(event.user_id, event.text, safe)
    episodic_store.log_exchange(user_id=event.user_id, human_msg=event.text, ai_msg=safe, channel=event.channel, run_id=run_id)
    return {"reply": safe, "run_id": run_id, "active_agent": result["active_agent"], "approval_request": pending[0] if pending else None}

async def resume_approval(approval_id: str, decision: str) -> dict[str, Any]:
    request = approval_store.resolve(approval_id, decision)
    context = request["context"]
    trajectory_store.record(request["run_id"], "approval_resolved", agent_id=context["active_agent"], tool_name=request["tool_name"], decision=decision)
    if decision == "denied": return {"reply": "Action denied. No changes were made.", "run_id": request["run_id"], "active_agent": context["active_agent"], "approval_request": None}
    try: result = execute_tool(request["tool_name"], request["arguments"]); reply = f"Approved action completed: {json.dumps(result, default=str)}"
    except Exception as exc: reply = f"Approved action failed: {exc}"
    trajectory_store.record(request["run_id"], "tool_executed", agent_id=context["active_agent"], tool_name=request["tool_name"], tool_args=request["arguments"], tool_result=reply, risk_level="approval_required")
    return {"reply": reply, "run_id": request["run_id"], "active_agent": context["active_agent"], "approval_request": None}
