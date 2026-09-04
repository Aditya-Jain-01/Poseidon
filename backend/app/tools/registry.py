"""Central tool definitions with MCP discovery and sandboxed execution.

All tools (native and MCP) share this unified interface and least-privilege boundary.
"""
from __future__ import annotations

import asyncio
from typing import Any, Callable
from app.soul import soul_store
from app.security.sandbox import SandboxGuard
from . import calendar, crm, notes_reminders, skill_manage
from .mcp_manager import mcp_manager


def _schema(name: str, description: str, properties: dict[str, Any], required: list[str] | None = None) -> dict[str, Any]:
    return {
        "type": "function",
        "function": {
            "name": name,
            "description": description,
            "parameters": {
                "type": "object",
                "properties": properties,
                "required": required or [],
                "additionalProperties": False,
            },
        },
    }


BASE_TOOL_REGISTRY: dict[str, dict[str, Any]] = {
    "crm_read": {"tier": "auto", "handler": crm.crm_read, "schema": _schema("crm_read", "Search local CRM contacts.", {"query": {"type": "string"}})},
    "crm_write": {"tier": "approval_required", "handler": crm.crm_write, "schema": _schema("crm_write", "Create, update, or delete a local CRM contact.", {"action": {"type": "string", "enum": ["create", "update", "delete"]}, "contact": {"type": "object"}, "contact_id": {"type": "string"}}, ["action"])},
    "notes_reminders_read": {"tier": "auto", "handler": notes_reminders.notes_reminders_read, "schema": _schema("notes_reminders_read", "Read local notes and reminders.", {"query": {"type": "string"}})},
    "notes_reminders_create": {"tier": "approval_required", "handler": notes_reminders.notes_reminders_create, "schema": _schema("notes_reminders_create", "Create a note or reminder.", {"kind": {"type": "string", "enum": ["note", "reminder"]}, "text": {"type": "string"}, "due_at": {"type": "string"}}, ["kind", "text"])},
    "notes_reminders_delete": {"tier": "approval_required", "handler": notes_reminders.notes_reminders_delete, "schema": _schema("notes_reminders_delete", "Delete a note or reminder.", {"kind": {"type": "string", "enum": ["note", "reminder"]}, "item_id": {"type": "string"}}, ["kind", "item_id"])},
    "calendar_read": {"tier": "auto", "handler": calendar.calendar_read, "schema": _schema("calendar_read", "Read local calendar events.", {"query": {"type": "string"}})},
    "calendar_create": {"tier": "approval_required", "handler": calendar.calendar_create, "schema": _schema("calendar_create", "Create a local calendar event.", {"title": {"type": "string"}, "starts_at": {"type": "string"}, "ends_at": {"type": "string"}, "description": {"type": "string"}}, ["title", "starts_at"])},
    "skill_manage_read": {"tier": "auto", "handler": skill_manage.skill_manage_read, "schema": _schema("skill_manage_read", "List procedural skills.", {"query": {"type": "string"}})},
    "skill_manage_write": {"tier": "approval_required", "handler": skill_manage.skill_manage_write, "schema": _schema("skill_manage_write", "Create a procedural skill.", {"name": {"type": "string"}, "description": {"type": "string"}, "triggers": {"type": "array", "items": {"type": "string"}}, "content": {"type": "string"}}, ["name", "description", "triggers", "content"])},
}


def get_all_tools() -> dict[str, dict[str, Any]]:
    """Return merged registry of base native tools and discovered MCP tools."""
    tools = dict(BASE_TOOL_REGISTRY)
    discovered = mcp_manager.discover_tools()
    tools.update(discovered)
    return tools


def get_tier(tool_name: str) -> str:
    tool = get_all_tools().get(tool_name)
    return tool.get("tier", "approval_required") if tool else "approval_required"


def get_tool(tool_name: str) -> dict[str, Any] | None:
    return get_all_tools().get(tool_name)


def get_tools_for_agent(agent_id: str = "poseidon") -> list[dict[str, Any]]:
    """Return tool schemas available for the agent."""
    all_tools = get_all_tools()
    agent = soul_store.get_agent(agent_id)
    if agent and agent.get("tools"):
        names = agent.get("tools", [])
        return [all_tools[name]["schema"] for name in names if name in all_tools]
    # Default: all registered tools
    return [t["schema"] for t in all_tools.values()]


async def execute_tool(tool_name: str, arguments: dict[str, Any] | None = None) -> Any:
    """Execute a tool within the in-process SandboxGuard least-privilege boundary."""
    tool = get_tool(tool_name)
    if not tool:
        raise ValueError(f"Unknown tool: {tool_name}")

    args = arguments or {}
    handler = tool["handler"]

    # Sandboxed execution with timeout and path jailing
    return await SandboxGuard.execute(tool_name, handler, args)
