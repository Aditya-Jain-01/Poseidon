"""MCP configuration cannot expose in-process external handlers to the agent."""

import pytest
from app.tools.mcp_manager import mcp_manager
from app.tools.registry import get_all_tools, get_tier, execute_tool


@pytest.mark.asyncio
async def test_mcp_dynamic_tool_registration():
    def custom_echo(message: str) -> str:
        return f"echo: {message}"

    mcp_manager.register_dynamic_tool(
        name="custom_echo",
        description="Echoes input",
        parameters={"properties": {"message": {"type": "string"}}, "required": ["message"]},
        handler=custom_echo,
        tier="auto",
    )

    all_tools = get_all_tools()
    assert "custom_echo" not in all_tools
    assert get_tier("custom_echo") == "approval_required"

    with pytest.raises(ValueError, match="Unknown tool"):
        await execute_tool("custom_echo", {"message": "hello"})


@pytest.mark.asyncio
async def test_mcp_execute_tool_timeout():
    async def hanging_tool():
        return "late"

    mcp_manager.register_dynamic_tool(
        name="hanging_mcp",
        description="A hanging MCP tool",
        parameters={},
        handler=hanging_tool,
        tier="approval_required",
    )

    res = await mcp_manager.execute_mcp_tool("hanging_mcp", {})
    assert res.get("status") == "failed"
    assert "disabled" in res.get("error", "")
