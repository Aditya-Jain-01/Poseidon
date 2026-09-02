"""Taint Tracking, Data Provenance & Content Risk Evaluation Module.

Enforces multi-layer risk and provenance rules:
1. Source/Channel Trust: Tags data originating from external channels (Telegram, incoming emails,
   third-party MCP tools, webhooks) as UNTRUSTED.
2. Content Risk: Deterministically inspects incoming message text for prompt injection,
   credential/secret requests, destructive action requests, and authorization manipulation.
3. Overall Risk Calculation: Combines Source Trust + Content Risk into a tiered risk model
   (LOW, MEDIUM, HIGH, CRITICAL). An untrusted source never becomes LOW even if content is benign.
4. Tool Execution Policy: Dynamically determines whether a tool can auto-run or requires approval,
   guaranteeing that read tools are downgraded under meaningful risk and write/unknown tools
   always require approval.
"""

import re
from enum import Enum
from typing import Any


class TrustLevel(str, Enum):
    TRUSTED = "TRUSTED"
    UNTRUSTED = "UNTRUSTED"


class RiskLevel(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class ContentRiskCategory(str, Enum):
    BENIGN = "BENIGN"
    PROMPT_INJECTION = "PROMPT_INJECTION"
    CREDENTIAL_REQUEST = "CREDENTIAL_REQUEST"
    DESTRUCTIVE_ACTION = "DESTRUCTIVE_ACTION"
    AUTHORIZATION_MANIPULATION = "AUTHORIZATION_MANIPULATION"


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


# ============================================================================
# Deterministic Content Inspection Patterns
# ============================================================================

# 1. Prompt-injection and system prompt override patterns
PROMPT_INJECTION_PATTERNS = [
    (r"(?i)\bignore\s+(all\s+|your\s+|the\s+)?(previous|prior|above|system)\s+(instructions?|prompts?|rules?|guidelines?)\b", "Prompt override: Ignore previous instructions"),
    (r"(?i)\bdisregard\s+(all\s+|your\s+|the\s+)?(previous|prior|system\s+)?(rules?|guidelines?|instructions?|prompts?)\b", "Prompt override: Disregard guidelines"),
    (r"(?i)\byou\s+are\s+now\s+(dan|an\s+unrestricted|a\s+jailbroken|developer\s+mode)\b", "Jailbreak attempt / persona override"),
    (r"(?i)\bsystem\s+override\b", "System override directive"),
    (r"(?i)\bdeveloper\s+mode\s+(enabled|activate|on|activated)\b", "Developer mode override"),
    (r"(?i)\b(reveal|show|print|output|display|dump|tell\s+me)\s+(your\s+)?(system\s+prompt|initial\s+instructions|system\s+instructions|hidden\s+prompt)\b", "System prompt extraction attempt"),
    (r"(?i)\bwhat\s+are\s+your\s+(exact\s+)?(system\s+instructions|initial\s+prompts|system\s+prompts)\b", "System prompt inquiry"),
    (r"(?i)\bbypass\s+(guardrails?|safety|filters?|rules?|policy)\b", "Guardrail bypass attempt"),
]

# 2. Credential, secret and key requests
CREDENTIAL_REQUEST_PATTERNS = [
    (r"(?i)\b(give|show|tell|reveal|dump|leak|print|send|get|fetch|extract)\s+(me\s+)?(the\s+|all\s+)?(database\s+)?(api[_\s-]?keys?|passwords?|tokens?|private[_\s-]?keys?|credentials?|secrets?|auth[_\s-]?tokens?)\b", "Credential / secret extraction request"),
    (r"(?i)\b(what\s+is|what\s+are)\s+(the\s+|your\s+)?(api[_\s-]?keys?|passwords?|tokens?|private\s+keys?|private[_\s-]?keys?|credentials?|secrets?)\b", "Credential inquiry"),
    (r"(?i)\b(print|output|dump|show)\s+(the\s+)?(auth\s+tokens?|credentials?|passwords?|api\s+keys?)\b", "Auth / credential dump request"),
    (r"(?i)\b(aws[_\s-]?secret|openai[_\s-]?api[_\s-]?key|openrouter[_\s-]?key|auth[_\s-]?token|bearer[_\s-]?token)\b", "Specific secret target mention"),
    (r"(?i)\b(cat|read|print|open)\s+(\.env|id_rsa|secrets\.json|\.aws/credentials)\b", "Sensitive file read request"),
]

# 3. Suspicious, destructive or mass-exfiltration tool/action requests
DESTRUCTIVE_ACTION_PATTERNS = [
    (r"(?i)\b(delete|drop|wipe|purge|remove|destroy)\s+(all\s+)?(customer\s+records?|users?|tables?|databases?|files?|data|crm(\s+records?)?)\b", "Destructive mass data deletion request"),
    (r"(?i)\bDROP\s+TABLE\b", "SQL injection / DROP TABLE command"),
    (r"(?i)\b(rm\s+-rf|del\s+/f|format\s+c:)\b", "Destructive file system command"),
    (r"(?i)\b(grant\s+admin|modify\s+permissions?|escalate\s+privileges?|chmod\s+777|chown\s+root)\b", "Privilege escalation / permission modification"),
    (r"(?i)\b(create|add)\s+(a\s+)?(new\s+)?(admin|superuser|root|privileged)\s+(account|user|role)\b", "Privileged account creation request"),
    (r"(?i)\b(dump|export|exfiltrate|leak|scrape)\s+(all\s+)?(crm|customers?|users?|database|records?|emails?)\b", "Mass data export/exfiltration request"),
    (r"(?i)\b(send|post|forward|upload|curl|wget)\s+(all\s+)?(data|records?|files?|secrets?)\s+(to\s+)?https?://", "External data exfiltration request"),
]

# 4. Authorization manipulation and social engineering
AUTHORIZATION_MANIPULATION_PATTERNS = [
    (r"(?i)\b(i\s+already\s+approved\s+this|approval\s+is\s+already\s+given|already\s+confirmed)\b", "False pre-approval assertion"),
    (r"(?i)\b(don'?t|do\s+not|no\s+need\s+to)\s+(ask\s+for|require|prompt\s+for)\s+(confirmation|approval|permission)\b", "Approval bypass command"),
    (r"(?i)\b(i\s+am|acting\s+as|speaking\s+as)\s+(the\s+)?(administrator|admin|operator|owner|root|supervisor|creator)\b", "Operator / admin impersonation"),
    (r"(?i)\bexecute\s+(without|bypassing)\s+(approval|confirmation|checks?)\b", "Direct unapproved execution request"),
]

# Compile pattern tables
_COMPILED_INJECTIONS = [(re.compile(p), label) for p, label in PROMPT_INJECTION_PATTERNS]
_COMPILED_CREDENTIALS = [(re.compile(p), label) for p, label in CREDENTIAL_REQUEST_PATTERNS]
_COMPILED_DESTRUCTIVE = [(re.compile(p), label) for p, label in DESTRUCTIVE_ACTION_PATTERNS]
_COMPILED_AUTH_MANIP = [(re.compile(p), label) for p, label in AUTHORIZATION_MANIPULATION_PATTERNS]


# ============================================================================
# Core Evaluation Functions
# ============================================================================

def evaluate_source_trust(channel: str | None) -> dict[str, Any]:
    """Evaluate whether an incoming channel/source is trusted or untrusted."""
    norm_channel = (channel or "").strip().lower()
    is_untrusted = is_channel_untrusted(norm_channel)
    trust_level = TrustLevel.UNTRUSTED if is_untrusted else TrustLevel.TRUSTED

    reason = (
        f"Channel '{norm_channel or 'unknown'}' is an external untrusted source."
        if is_untrusted
        else f"Channel '{norm_channel}' is an authenticated trusted source."
    )

    return {
        "channel": norm_channel,
        "trust_level": trust_level,
        "is_untrusted": is_untrusted,
        "reason": reason,
    }


def is_channel_untrusted(channel: str | None) -> bool:
    """Check if an incoming channel is classified as untrusted/tainted.

    Preserved for backwards compatibility with existing callers.
    """
    normalized = (channel or "").strip().lower()
    if normalized in UNTRUSTED_CHANNELS:
        return True
    return normalized not in TRUSTED_CHANNELS


def evaluate_content_risk(message: str | None) -> dict[str, Any]:
    """Deterministically inspect message content for security risks."""
    text = (message or "").strip()
    if not text:
        return {
            "category": ContentRiskCategory.BENIGN,
            "is_suspicious": False,
            "risk_score": 0,
            "detected_patterns": [],
            "reasons": ["Message is empty or benign."],
        }

    detected_patterns: list[dict[str, str]] = []
    categories: set[ContentRiskCategory] = set()

    # 1. Check prompt injections
    for regex, label in _COMPILED_INJECTIONS:
        match = regex.search(text)
        if match:
            detected_patterns.append({"pattern": label, "matched": match.group(0), "category": ContentRiskCategory.PROMPT_INJECTION.value})
            categories.add(ContentRiskCategory.PROMPT_INJECTION)

    # 2. Check credential requests
    for regex, label in _COMPILED_CREDENTIALS:
        match = regex.search(text)
        if match:
            detected_patterns.append({"pattern": label, "matched": match.group(0), "category": ContentRiskCategory.CREDENTIAL_REQUEST.value})
            categories.add(ContentRiskCategory.CREDENTIAL_REQUEST)

    # 3. Check destructive / exfiltration actions
    for regex, label in _COMPILED_DESTRUCTIVE:
        match = regex.search(text)
        if match:
            detected_patterns.append({"pattern": label, "matched": match.group(0), "category": ContentRiskCategory.DESTRUCTIVE_ACTION.value})
            categories.add(ContentRiskCategory.DESTRUCTIVE_ACTION)

    # 4. Check authorization manipulation
    for regex, label in _COMPILED_AUTH_MANIP:
        match = regex.search(text)
        if match:
            detected_patterns.append({"pattern": label, "matched": match.group(0), "category": ContentRiskCategory.AUTHORIZATION_MANIPULATION.value})
            categories.add(ContentRiskCategory.AUTHORIZATION_MANIPULATION)

    is_suspicious = len(detected_patterns) > 0
    reasons = [p["pattern"] for p in detected_patterns] if is_suspicious else ["Content appears benign."]

    # Determine dominant category
    if ContentRiskCategory.DESTRUCTIVE_ACTION in categories or ContentRiskCategory.CREDENTIAL_REQUEST in categories:
        primary_category = ContentRiskCategory.DESTRUCTIVE_ACTION if ContentRiskCategory.DESTRUCTIVE_ACTION in categories else ContentRiskCategory.CREDENTIAL_REQUEST
    elif ContentRiskCategory.PROMPT_INJECTION in categories:
        primary_category = ContentRiskCategory.PROMPT_INJECTION
    elif ContentRiskCategory.AUTHORIZATION_MANIPULATION in categories:
        primary_category = ContentRiskCategory.AUTHORIZATION_MANIPULATION
    else:
        primary_category = ContentRiskCategory.BENIGN

    return {
        "category": primary_category,
        "categories": [c.value for c in categories],
        "is_suspicious": is_suspicious,
        "risk_score": len(detected_patterns),
        "detected_patterns": detected_patterns,
        "reasons": reasons,
    }


def calculate_overall_risk(
    source_result: str | dict[str, Any] | None,
    content_result: str | dict[str, Any] | None,
) -> dict[str, Any]:
    """Combine Source Trust and Content Risk into an overall risk assessment.

    Risk Model Truth Matrix:
    - Trusted source + benign content            -> LOW
    - Untrusted source + benign content          -> MEDIUM
    - Trusted source + suspicious/override req   -> HIGH
    - Untrusted source + suspicious content      -> HIGH / CRITICAL
    - Any source + destructive/credential req    -> HIGH or CRITICAL
    - Untrusted source + destructive/credential  -> CRITICAL

    Invariant: An untrusted source NEVER degrades to LOW, even with benign content.
    """
    # Normalize source evaluation
    if isinstance(source_result, dict):
        source_eval = source_result
    else:
        source_eval = evaluate_source_trust(source_result)

    # Normalize content evaluation
    if isinstance(content_result, dict):
        content_eval = content_result
    else:
        content_eval = evaluate_content_risk(content_result)

    is_untrusted_source = source_eval.get("is_untrusted", False)
    is_suspicious_content = content_eval.get("is_suspicious", False)
    content_categories = set(content_eval.get("categories", []))
    if "category" in content_eval and isinstance(content_eval["category"], (ContentRiskCategory, str)):
        cat_val = content_eval["category"].value if isinstance(content_eval["category"], ContentRiskCategory) else str(content_eval["category"])
        content_categories.add(cat_val)

    has_destructive = ContentRiskCategory.DESTRUCTIVE_ACTION.value in content_categories
    has_credentials = ContentRiskCategory.CREDENTIAL_REQUEST.value in content_categories
    has_injection = ContentRiskCategory.PROMPT_INJECTION.value in content_categories
    has_auth_manip = ContentRiskCategory.AUTHORIZATION_MANIPULATION.value in content_categories

    reasons: list[str] = []
    reasons.append(source_eval.get("reason", "Source evaluated."))

    if is_suspicious_content:
        reasons.extend([f"Content flag: {r}" for r in content_eval.get("reasons", [])])

    # Compute overall risk level
    if is_untrusted_source and (has_destructive or has_credentials or (has_injection and has_auth_manip)):
        overall_level = RiskLevel.CRITICAL
        reasons.append("Untrusted external source combined with destructive/credential/injection request.")
    elif (has_destructive or has_credentials) or (is_untrusted_source and (has_injection or has_auth_manip)):
        overall_level = RiskLevel.HIGH
        reasons.append("High-severity action/credential request or untrusted source with suspicious injection directives.")
    elif is_suspicious_content:
        overall_level = RiskLevel.HIGH
        reasons.append("Suspicious prompt override or authorization manipulation detected in content.")
    elif is_untrusted_source:
        overall_level = RiskLevel.MEDIUM
        reasons.append("Untrusted source with benign content: baseline taint enforced.")
    else:
        overall_level = RiskLevel.LOW
        reasons.append("Trusted source and benign content.")

    # Context is tainted if source is untrusted OR content is suspicious
    is_tainted = is_untrusted_source or is_suspicious_content

    return {
        "overall_risk": overall_level,
        "is_tainted": is_tainted,
        "source": source_eval,
        "content": content_eval,
        "reasons": reasons,
    }


def evaluate_tool_tier(
    tool_name: str,
    is_tainted: bool | None = None,
    risk_context: dict[str, Any] | RiskLevel | None = None,
    extra_reasons: list[str] | None = None,
) -> dict[str, Any]:
    """Determine if a tool call can auto-run or requires approval.

    Guarantees:
    - Approval-required tools (write, delete, cron, delegate) ALWAYS require approval.
    - Unknown tools (not in BASE_AUTORUN_TOOLS) ALWAYS require approval.
    - Read tools (BASE_AUTORUN_TOOLS) are DOWNGRADED to require approval when context is tainted
      or has risk level >= MEDIUM.
    - Read tools ONLY auto-run in LOW risk trusted contexts.

    Parameters:
    - tool_name: Name of tool to execute
    - is_tainted: (Optional bool) Backwards-compatible taint flag
    - risk_context: (Optional dict or RiskLevel) Result from calculate_overall_risk or RiskLevel
    - extra_reasons: (Optional list[str]) Supplemental reason messages
    """
    tool = (tool_name or "").strip().lower()
    reasons = list(extra_reasons or [])

    # Extract risk level and taint flag
    risk_level = RiskLevel.LOW
    tainted_flag = False

    if isinstance(risk_context, dict):
        risk_level = risk_context.get("overall_risk", RiskLevel.LOW)
        tainted_flag = risk_context.get("is_tainted", False)
        reasons.extend(risk_context.get("reasons", []))
    elif isinstance(risk_context, RiskLevel):
        risk_level = risk_context
        tainted_flag = risk_level != RiskLevel.LOW
    elif isinstance(risk_context, str) and risk_context.upper() in RiskLevel.__members__:
        risk_level = RiskLevel[risk_context.upper()]
        tainted_flag = risk_level != RiskLevel.LOW

    # Handle backwards-compatible is_tainted arg
    if is_tainted is not None:
        tainted_flag = bool(is_tainted)
        if tainted_flag and risk_level == RiskLevel.LOW:
            risk_level = RiskLevel.MEDIUM

    # 1. Check if tool is natively approval-required or unknown
    if tool in BASE_APPROVAL_REQUIRED_TOOLS:
        reasons.append(f"Tool '{tool_name}' is in the approval-required tier by policy.")
        return {
            "tool": tool_name,
            "requires_approval": True,
            "tier": "approval_required",
            "downgraded_by_taint": False,
            "risk_level": risk_level.value,
            "reasons": reasons,
        }

    if tool not in BASE_AUTORUN_TOOLS:
        reasons.append(f"Tool '{tool_name}' is unknown/unregistered and defaults to approval-required.")
        return {
            "tool": tool_name,
            "requires_approval": True,
            "tier": "approval_required",
            "downgraded_by_taint": False,
            "risk_level": risk_level.value,
            "reasons": reasons,
        }

    # 2. Tool is in BASE_AUTORUN_TOOLS (read-only tool)
    if tainted_flag or risk_level in (RiskLevel.MEDIUM, RiskLevel.HIGH, RiskLevel.CRITICAL):
        reasons.append(
            f"Context risk is {risk_level.value} (is_tainted={tainted_flag}). "
            f"Auto-run read tool '{tool_name}' downgraded to approval-required."
        )
        return {
            "tool": tool_name,
            "requires_approval": True,
            "tier": "downgraded_approval_required",
            "downgraded_by_taint": True,
            "risk_level": risk_level.value,
            "reasons": reasons,
        }

    # 3. Trusted LOW-risk read operation
    reasons.append(f"Tool '{tool_name}' is read-only and context is trusted with LOW risk.")
    return {
        "tool": tool_name,
        "requires_approval": False,
        "tier": "auto_run",
        "downgraded_by_taint": False,
        "risk_level": RiskLevel.LOW.value,
        "reasons": reasons,
    }


class TaintTracker:
    """Evaluates taint status and determines tool execution permissions."""

    @staticmethod
    def evaluate_source(channel: str | None) -> dict[str, Any]:
        """Evaluate source channel trust."""
        return evaluate_source_trust(channel)

    @staticmethod
    def evaluate_content(message: str | None) -> dict[str, Any]:
        """Evaluate content risk of message."""
        return evaluate_content_risk(message)

    @staticmethod
    def calculate_risk(
        source: str | dict[str, Any] | None,
        content: str | dict[str, Any] | None,
    ) -> dict[str, Any]:
        """Calculate overall combined risk."""
        return calculate_overall_risk(source, content)

    @staticmethod
    def evaluate_tool_tier(
        tool_name: str,
        is_tainted: bool | None = None,
        risk_context: dict[str, Any] | RiskLevel | None = None,
        extra_reasons: list[str] | None = None,
    ) -> dict[str, Any]:
        """Evaluate tool execution tier with multi-layer risk context.

        Fully backwards-compatible with calls passing `is_tainted=True/False`.
        """
        return evaluate_tool_tier(
            tool_name=tool_name,
            is_tainted=is_tainted,
            risk_context=risk_context,
            extra_reasons=extra_reasons,
        )
