"""One handler invocation boundary for registered tools."""
from __future__ import annotations

import json
import inspect
from typing import Any

from app.models import ToolCall, ToolExecutionContext
from app.security.secrets import redact
from app.security.sandbox import ExecutionGuard
from app.tools.registry import get_tool


class ToolExecutionService:
    """Executes reviewed registry handlers after the graph has applied policy.

    Trusted owner, run, and approval information remains in ``context`` and is
    never merged into model-provided tool arguments.
    """

    async def execute(self, call: ToolCall | dict[str, Any], context: ToolExecutionContext, *, approval_granted: bool = False) -> Any:
        call = ToolCall.model_validate(call)
        tool = get_tool(call.name)
        if tool is None:
            raise ValueError("Unknown tool")
        arguments = dict(call.arguments)
        signature = inspect.signature(tool['handler'])
        if 'owner_id' in signature.parameters:
            arguments['owner_id'] = context.actor.owner_id
        if approval_granted and '_operator_approved' in signature.parameters:
            arguments['_operator_approved'] = True
        result = await ExecutionGuard.execute(call.name, tool["handler"], arguments, timeout_seconds=tool["timeout_seconds"])
        # A JSON round trip prevents non-serializable handler values becoming
        # accidental internal-object leaks in model messages or audit storage.
        return redact(json.loads(json.dumps(result, default=str)))

