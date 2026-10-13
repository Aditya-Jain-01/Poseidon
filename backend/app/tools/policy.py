"""Single authoritative policy decision for every model-requested tool call."""
from __future__ import annotations

from typing import Any

from app.models import PolicyDecision, ToolCall, ToolExecutionContext
from app.security.note_guard import NoteGuard
from app.tools.registry import get_tool


class ToolPolicyService:
    """Evaluate tool availability, schema shape, agent permission and taint.

    This service deliberately returns data, never invokes a handler. Native
    graph interrupts and approvals consume its ``require_approval`` decision.
    """

    policy_version = "2"

    @staticmethod
    def _schema_errors(schema: dict[str, Any], arguments: dict[str, Any]) -> list[str]:
        params = schema["function"]["parameters"]
        properties = params.get("properties", {})
        errors = [f"missing required argument: {key}" for key in params.get("required", []) if key not in arguments]
        unknown = set(arguments) - set(properties)
        if params.get("additionalProperties") is False and unknown:
            errors.append(f"unexpected arguments: {', '.join(sorted(unknown))}")
        for key, value in arguments.items():
            spec = properties.get(key, {})
            types = spec.get("type")
            if types == "string" and not isinstance(value, str):
                errors.append(f"{key} must be a string")
            elif types == "object" and not isinstance(value, dict):
                errors.append(f"{key} must be an object")
            elif types == "array" and not isinstance(value, list):
                errors.append(f"{key} must be an array")
            if spec.get("enum") and value not in spec["enum"]:
                errors.append(f"{key} must be one of {', '.join(map(str, spec['enum']))}")
        return errors

    def evaluate(self, call: ToolCall | dict[str, Any], context: ToolExecutionContext, *, agent_allowed_tools: list[str], calls_used: int, max_calls: int) -> PolicyDecision:
        call = ToolCall.model_validate(call)
        tool = get_tool(call.name)
        if tool is None:
            return PolicyDecision(decision="deny", reasons=["Unknown tool"])
        # Empty means no permissions. Wildcard remains explicit-only.
        if call.name not in agent_allowed_tools and "*" not in agent_allowed_tools:
            return PolicyDecision(decision="deny", reasons=["Agent lacks permission for this tool"])
        errors = self._schema_errors(tool["schema"], call.arguments)
        if errors:
            return PolicyDecision(decision="deny", reasons=errors)
        if calls_used >= max_calls:
            return PolicyDecision(decision="deny", reasons=["Configured tool-call limit reached"])
        if tool["trusted_provenance"] != "built_in" or context.is_tainted:
            return PolicyDecision(decision="require_approval", reasons=["Untrusted provenance or tainted context requires approval"], policy_version=self.policy_version)
        if tool["base_tier"] == "approval_required":
            return PolicyDecision(decision="require_approval", policy_version=self.policy_version)
        if tool["base_tier"] == "guarded_auto":
            verdict = NoteGuard.inspect(str(call.arguments.get("text", "")))
            if verdict.verdict == "reject":
                return PolicyDecision(decision="deny", reasons=verdict.reasons, policy_version=self.policy_version)
            if verdict.verdict == "suspicious":
                return PolicyDecision(decision="require_approval", reasons=verdict.reasons, policy_version=self.policy_version)
            return PolicyDecision(decision="guard", policy_version=self.policy_version)
        return PolicyDecision(decision="allow", policy_version=self.policy_version)

