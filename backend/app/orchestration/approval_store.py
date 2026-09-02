"""In-memory parking lot for tool calls requiring explicit approval."""
from __future__ import annotations
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

class ApprovalStore:
    def __init__(self) -> None:
        self._pending: dict[str, dict[str, Any]] = {}

    def park(self, run_id: str, tool_call: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
        approval_id = str(uuid4())
        request = {"id": approval_id, "run_id": run_id, "tool_name": tool_call["name"], "arguments": tool_call.get("arguments", {}), "status": "pending", "created_at": datetime.now(timezone.utc).isoformat(), "context": context}
        self._pending[approval_id] = request
        return self.public(request)

    def resolve(self, approval_id: str, decision: str) -> dict[str, Any]:
        request = self._pending.pop(approval_id, None)
        if request is None:
            raise KeyError("Approval request not found or already resolved")
        if decision not in {"approved", "denied"}:
            self._pending[approval_id] = request
            raise ValueError("decision must be approved or denied")
        request["status"] = decision
        request["resolved_at"] = datetime.now(timezone.utc).isoformat()
        return request

    @staticmethod
    def public(request: dict[str, Any]) -> dict[str, Any]:
        return {key: value for key, value in request.items() if key != "context"}

approval_store = ApprovalStore()
