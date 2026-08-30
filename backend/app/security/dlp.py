"""Data Loss Prevention (DLP) Module for Outbound Messages.

Scans agent replies before transmission to prevent accidental exfiltration of:
- API Keys & Access Tokens (OpenAI, OpenRouter, Anthropic, AWS, GitHub, Bearer)
- Private Keys & Cryptographic Certificates
- Sensitive PII / Identifiers (Credit cards, SSNs, bulk credentials)
"""

import re
import logging
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)

# Pre-compiled DLP regex patterns
DLP_RULES = [
    (
        "OpenAI / OpenRouter API Key",
        re.compile(r"sk-[a-zA-Z0-9]{20,}"),
        "[REDACTED_API_KEY]",
    ),
    (
        "Anthropic API Key",
        re.compile(r"sk-ant-[a-zA-Z0-9_\-]{20,}"),
        "[REDACTED_API_KEY]",
    ),
    (
        "Google API Key",
        re.compile(r"AIza[0-9A-Za-z\-_]{35}"),
        "[REDACTED_API_KEY]",
    ),
    (
        "AWS Access Key ID",
        re.compile(r"\b(AKIA|ABIA|ACCA|ASIA)[0-9A-Z]{16}\b"),
        "[REDACTED_AWS_KEY]",
    ),
    (
        "GitHub Token",
        re.compile(r"\b(ghp|gho|ghu|ghs|ghr)_[A-Za-z0-9_]{36,}\b"),
        "[REDACTED_GITHUB_TOKEN]",
    ),
    (
        "Private Key",
        re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----[\s\S]*?-----END [A-Z ]*PRIVATE KEY-----"),
        "[REDACTED_PRIVATE_KEY]",
    ),
    (
        "Authorization Bearer Header",
        re.compile(r"(?i)\bbearer\s+[a-zA-Z0-9\-_\.~+/]{25,}"),
        "Bearer [REDACTED_TOKEN]",
    ),
    (
        "US Social Security Number (SSN)",
        re.compile(r"\b\d{3}-\d{2}-\d{4}\b"),
        "[REDACTED_SSN]",
    ),
    (
        "Credit Card Number",
        re.compile(r"\b(?:4[0-9]{12}(?:[0-9]{3})?|5[1-5][0-9]{14}|3[47][0-9]{13}|6(?:011|5[0-9]{2})[0-9]{12})\b"),
        "[REDACTED_CREDIT_CARD]",
    ),
]


@dataclass
class DLPResult:
    is_safe: bool
    violations: list[str] = field(default_factory=list)
    sanitized_text: str = ""
    redaction_count: int = 0


class DLPScanner:
    """Outbound scanner for data loss prevention and sensitive content scrubbing."""

    @classmethod
    def scan_and_redact(cls, text: str) -> DLPResult:
        """Scan text against DLP rules and return sanitized version."""
        if not text or not isinstance(text, str):
            return DLPResult(is_safe=True, sanitized_text=text or "")

        sanitized = text
        violations = []
        redaction_count = 0

        for rule_name, pattern, replacement in DLP_RULES:
            matches = pattern.findall(sanitized)
            if matches:
                violations.append(f"{rule_name} (found {len(matches)} match(es))")
                redaction_count += len(matches)
                sanitized = pattern.sub(replacement, sanitized)
                logger.warning("[DLP] Outbound violation detected: %s", rule_name)

        is_safe = len(violations) == 0
        return DLPResult(
            is_safe=is_safe,
            violations=violations,
            sanitized_text=sanitized,
            redaction_count=redaction_count,
        )
