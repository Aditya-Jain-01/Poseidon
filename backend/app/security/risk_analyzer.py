"""Tool Risk Analyzer & Parameter Diff Generator.

Evaluates pending tool invocations, assigns risk tiers (HIGH / MEDIUM / LOW),
identifies dangerous parameters (URLs, scripts, overrides, shell commands),
and generates parameter diffs for the ApprovalCard UI.
"""

import re
from typing import Any


DANGEROUS_PARAM_PATTERNS = [
    (r"https?://[^\s<>\"']+", "Contains external URL"),
    (r"(?i)\b(rm\s+-rf|del\s+/f|format\s+c:|drop\s+table|delete\s+from)\b", "Destructive operation keyword"),
    (r"(?i)\b(ignore\s+previous|system\s+override|dan|bypass)\b", "Prompt override signature"),
    (r"(?i)\b(password|secret|api_key|token)\b", "Sensitive credential reference"),
]

COMPILED_PARAM_PATTERNS = [(re.compile(p), label) for p, label in DANGEROUS_PARAM_PATTERNS]


class RiskAnalyzer:
    """Computes risk ratings and parameter analysis for tool approval requests."""

    @classmethod
    def analyze_tool_call(
        cls,
        tool_name: str,
        arguments: dict[str, Any],
        is_tainted: bool = False,
        original_values: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Perform a complete risk analysis on a tool call and its arguments."""
        tool = (tool_name or "").strip().lower()
        args = arguments or {}
        orig = original_values or {}

        warnings: list[str] = []
        dangerous_params: list[dict[str, Any]] = []

        # 1. Parameter content scan
        for param_key, param_val in args.items():
            val_str = str(param_val)
            for pattern, warning_label in COMPILED_PARAM_PATTERNS:
                if pattern.search(val_str):
                    warning_msg = f"Parameter '{param_key}': {warning_label}"
                    warnings.append(warning_msg)
                    dangerous_params.append({
                        "param": param_key,
                        "value": val_str,
                        "warning": warning_label,
                    })

        # 2. Parameter diff computation
        diff: dict[str, Any] = {}
        all_keys = set(args.keys()).union(set(orig.keys()))
        for k in all_keys:
            old_v = orig.get(k)
            new_v = args.get(k)
            if old_v != new_v:
                diff[k] = {"old": old_v, "new": new_v}

        # 3. Determine Risk Level
        is_write = any(w in tool for w in ["write", "create", "update", "delete", "cron", "delegate", "manage_write"])

        if is_tainted and is_write:
            risk_level = "high"
            warnings.append("CRITICAL: Tool write requested under a TAINTED / untrusted context.")
        elif dangerous_params:
            risk_level = "high"
        elif is_write:
            risk_level = "medium"
        elif is_tainted:
            risk_level = "medium"
            warnings.append("Context is TAINTED: read operation requires verification.")
        else:
            risk_level = "low"

        return {
            "tool": tool_name,
            "risk_level": risk_level,  # "high" | "medium" | "low"
            "is_tainted": is_tainted,
            "arguments": args,
            "diff": diff,
            "dangerous_params": dangerous_params,
            "warnings": warnings,
        }
