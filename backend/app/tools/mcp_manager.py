"""Model Context Protocol (MCP) Client & Tool Registration Manager.

Keeps MCP configuration and proposed tool definitions for future isolated
execution. Registered handlers are not exposed to the agent or executed.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Callable

from app.config import settings

_CONFIG_PATH = Path(settings.poseidon_db_path).parent / "mcp_config.json"


class MCPManager:
    """Manages external Model Context Protocol tool discovery and execution."""

    def __init__(self, config_path: Path | str | None = None) -> None:
        self.config_path = Path(config_path or _CONFIG_PATH)
        self._servers: dict[str, dict[str, Any]] = {}
        self._mcp_tools: dict[str, dict[str, Any]] = {}

    def load_config(self) -> dict[str, Any]:
        """Load mcp_config.json if present."""
        if not self.config_path.exists():
            return {}
        try:
            data = json.loads(self.config_path.read_text(encoding="utf-8"))
            self._servers = data.get("mcpServers", {})
            return data
        except Exception as exc:
            print(f"[MCPManager] Warning: failed to parse {self.config_path}: {exc}")
            return {}

    def register_dynamic_tool(
        self,
        name: str,
        description: str,
        parameters: dict[str, Any],
        handler: Callable[..., Any],
        tier: str = "approval_required",
    ) -> dict[str, Any]:
        """Register a dynamic tool originating from an MCP server or plugin."""
        tool_def = {
            "name": name,
            "tier": tier,
            "handler": handler,
            "schema": {
                "type": "function",
                "function": {
                    "name": name,
                    "description": description,
                    "parameters": {
                        "type": "object",
                        "properties": parameters.get("properties", {}),
                        "required": parameters.get("required", []),
                        "additionalProperties": False,
                    },
                },
            },
        }
        self._mcp_tools[name] = tool_def
        return tool_def

    def discover_tools(self) -> dict[str, dict[str, Any]]:
        """Return all discovered MCP tools."""
        self.load_config()
        return dict(self._mcp_tools)

    async def execute_mcp_tool(self, tool_name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        """External handlers require process isolation before they can run."""
        return {"error": "MCP execution is disabled until isolated execution is available", "status": "failed"}


mcp_manager = MCPManager()
