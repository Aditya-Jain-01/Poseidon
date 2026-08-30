"""Taint Tracking & Data Provenance Module.

Enforces provenance rules:
1. Tags data originating from external channels (Telegram, incoming emails, third-party MCP tools) as UNTRUSTED / TAINTED.
2. When context is tainted, dynamically downgrades auto-run read tools to require operator approval or triggers redaction.
"""

from typing import Any
from enum import Enum


class TrustLevel(str, Enum):
    TRUSTED = "TRUSTED"
    UNTRUSTED = "UNTRUSTED"


# Known trusted channels vs untrusted external channels
TRUSTED_CHANNELS = {"web", "web_operator", "cli", "local"}
UNTRUSTED_CHANNELS = {"telegram", "email", "incoming_webhook", "mcp_untrusted", "external_api"}

# Standard tool tiers per GUARDRAILS.md
BASE_AUTORUN_TOOLS = {
    "crm_read",
    "calendar_read",
    "notes_reminders_read",
    "skill_manage_read",
}

BASE_APPROVAL_REQUIRED_TOOLS = {
    "crm_write",
    "calendar_create",
    "calendar_update",
    "calendar_delete",
    "notes_reminders_create",
    "notes_reminders_update",
    "notes_reminders_delete",
    "cronjob",
    "delegate_task",
    "skill_manage_write",
    "mcp_client",
}


def is_channel_untrusted(channel: str) -> bool:
    """Check if an incoming channel is classified as untrusted/tainted."""
    normalized = (channel or "").strip().lower()
    if normalized in UNTRUSTED_CHANNELS:
        return True
    return normalized not in TRUSTED_CHANNELS


class TaintTracker:
    """Evaluates taint status and determines tool execution permissions."""

    @staticmethod
    def evaluate_tool_tier(
        tool_name: str,
        is_tainted: bool = False,
        extra_reasons: list[str] | None = None,
    ) -> dict[str, Any]:
        """Determine if a tool call can auto-run or requires approval.

        If `is_tainted` is True, auto-run read tools are downgraded to approval-required.
        """
        tool = (tool_name or "").strip().lower()
        reasons = list(extra_reasons or [])

        # Check if natively write/approval required
        if tool in BASE_APPROVAL_REQUIRED_TOOLS or not (tool in BASE_AUTORUN_TOOLS):
            reasons.append("Tool is in the approval-required tier by policy.")
            return {
                "tool": tool_name,
                "requires_approval": True,
                "tier": "approval_required",
                "downgraded_by_taint": False,
                "reasons": reasons,
            }

        # Tool is normally auto-run
        if is_tainted:
            reasons.append("Context is TAINTED (untrusted channel/data). Auto-run read tool downgraded to approval-required.")
            return {
                "tool": tool_name,
                "requires_approval": True,
                "tier": "downgraded_approval_required",
                "downgraded_by_taint": True,
                "reasons": reasons,
            }

        return {
            "tool": tool_name,
            "requires_approval": False,
            "tier": "auto_run",
            "downgraded_by_taint": False,
            "reasons": ["Tool is read-only and context is trusted."],
        }
