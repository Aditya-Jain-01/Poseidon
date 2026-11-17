"""The runtime's single interface to reviewed model-visible tools."""

from __future__ import annotations

from typing import Any

from app.models import PolicyDecision, ToolCall, ToolExecutionContext
from app.tools.execution import ToolExecutionService
from app.tools.policy import ToolPolicyService
from app.tools.registry import get_tool, get_tools_for_agent


class ToolAccess:
    def __init__(self, policy: ToolPolicyService | None = None, executor: ToolExecutionService | None = None):
        self._policy = policy or ToolPolicyService()
        self._executor = executor or ToolExecutionService()

    @property
    def policy_version(self) -> str:
        return self._policy.policy_version

    def schemas_for_agent(self, agent_id: str) -> list[dict[str, Any]]:
        return get_tools_for_agent(agent_id)

    def get(self, name: str) -> dict[str, Any] | None:
        return get_tool(name)

    def decide(self, call: ToolCall | dict[str, Any], context: ToolExecutionContext, *, agent_allowed_tools: list[str], calls_used: int, max_calls: int) -> PolicyDecision:
        return self._policy.evaluate(call, context, agent_allowed_tools=agent_allowed_tools, calls_used=calls_used, max_calls=max_calls)

    async def execute(self, call: ToolCall | dict[str, Any], context: ToolExecutionContext, *, approval_granted: bool = False) -> Any:
        return await self._executor.execute(call, context, approval_granted=approval_granted)
