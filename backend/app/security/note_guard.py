"""NoteGuard — Pre-write security validator for notes_reminders_create.

Three-tier adaptive policy:
  Tier 1 (ALLOW)      — Benign text, saves instantly. No human interaction.
  Tier 2 (SUSPICIOUS) — Credential refs, URLs, injection patterns. Pauses for
                         step-up approval via the existing ApprovalCard gate.
  Tier 3 (REJECT)     — Blatant adversarial payloads (jailbreaks, shells,
                         prompt overrides). Hard-rejected, no approval offered.
"""
from __future__ import annotations

import re
import logging
from dataclasses import dataclass, field
from typing import Literal

from app.security.adversarial_filter import COMPILED_PATTERNS as ADVERSARIAL_PATTERNS
from app.security.taint import evaluate_content_risk

logger = logging.getLogger(__name__)

# ── Tier 3 (Hard Reject) ────────────────────────────────────────────────────

# Raw LLM turn-delimiter smuggling — attempts to inject new assistant turns
_PROMPT_DELIMITER_PATTERNS = [
    re.compile(r"<\|im_start\|>"),
    re.compile(r"<\|im_end\|>"),
    re.compile(r"\[INST\]"),
    re.compile(r"###\s*System\s*:", re.IGNORECASE),
    re.compile(r"<\|system\|>"),
    re.compile(r"<\|user\|>"),
    re.compile(r"<\|assistant\|>"),
]

# ── Tier 2 (Suspicious — step-up approval) ──────────────────────────────────

# External URLs and raw IP addresses (could be exfiltration endpoints)
_URL_PATTERN = re.compile(
    r"https?://[^\s<>\"']+"
    r"|ftp://[^\s<>\"']+"
    r"|\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b",
    re.IGNORECASE,
)

# Sensitive file/config targets and secret-sounding keywords that don't
# belong in an everyday note (grocery list, meeting reminder, to-do).
_SENSITIVE_KEYWORD_PATTERNS = [
    re.compile(r"\b(api[_\s-]?key|secret[_\s-]?key|private[_\s-]?key)\b", re.IGNORECASE),
    re.compile(r"\bpassword\b", re.IGNORECASE),
    re.compile(r"\btoken\b", re.IGNORECASE),
    re.compile(r"\b(\.env|id_rsa|secrets\.json|\.aws/credentials)\b", re.IGNORECASE),
    re.compile(r"\b(bearer|authorization\s*:\s*bearer)\b", re.IGNORECASE),
    re.compile(r"\bssh[_\s-]?key\b", re.IGNORECASE),
]

# Maximum sizes (also configurable via settings, but enforced here as code constants)
_MAX_NOTE_CHARS = 500
_MAX_TOTAL_ITEMS = 500  # across all notes + reminders combined


# ── Public types ─────────────────────────────────────────────────────────────

Verdict = Literal["allow", "suspicious", "reject"]


@dataclass
class NoteVerdict:
    verdict: Verdict
    reasons: list[str] = field(default_factory=list)
    risk_level: str = "low"


class SuspiciousNoteError(Exception):
    """Sentinel raised when a note passes structural checks but triggers
    Tier 2 (suspicious) patterns.  The orchestrator catches this and
    re-routes the call to the approval_gate node instead of failing hard.
    """

    def __init__(self, kind: str, text: str, due_at: str | None, reasons: list[str]) -> None:
        super().__init__(f"Suspicious note content requires step-up approval: {reasons}")
        self.kind = kind
        self.text = text
        self.due_at = due_at
        self.reasons = reasons


# ── Core validator ───────────────────────────────────────────────────────────

class NoteGuard:
    """Stateless pre-write validator.  Call NoteGuard.inspect(text) before
    writing any note/reminder to persistent storage.
    """

    @classmethod
    def inspect(cls, text: str) -> NoteVerdict:
        """Return a NoteVerdict describing the safety tier of *text*.

        The caller should act on the verdict:
        - "allow"      → write to storage immediately.
        - "suspicious" → raise SuspiciousNoteError to trigger approval gate.
        - "reject"     → raise ValueError to hard-block the request.
        """
        text_clean = (text or "").strip()

        # ── Tier 3 checks ────────────────────────────────────────────────────

        if not text_clean:
            return NoteVerdict("reject", ["Note text is empty."], "low")

        if len(text_clean) > _MAX_NOTE_CHARS:
            return NoteVerdict(
                "reject",
                [f"Note exceeds maximum length of {_MAX_NOTE_CHARS} characters "
                 f"(got {len(text_clean)})."],
                "high",
            )

        # LLM prompt delimiter smuggling
        for pattern in _PROMPT_DELIMITER_PATTERNS:
            m = pattern.search(text_clean)
            if m:
                logger.warning("[NoteGuard] Delimiter smuggling attempt: %r", m.group(0))
                return NoteVerdict(
                    "reject",
                    [f"Forbidden prompt delimiter detected: '{m.group(0)}'"],
                    "critical",
                )

        # Adversarial jailbreak / shell / injection patterns
        for compiled_pattern in ADVERSARIAL_PATTERNS:
            m = compiled_pattern.search(text_clean)
            if m:
                logger.warning("[NoteGuard] Adversarial pattern: %r", m.group(0))
                return NoteVerdict(
                    "reject",
                    [f"Adversarial pattern blocked: '{m.group(0)}'"],
                    "critical",
                )

        # ── Tier 2 checks ────────────────────────────────────────────────────

        suspicious_reasons: list[str] = []

        # Check taint content-risk engine (credential requests, auth manipulation,
        # prompt injection patterns from taint.py)
        content_risk = evaluate_content_risk(text_clean)
        if content_risk.get("is_suspicious"):
            for reason in content_risk.get("reasons", []):
                suspicious_reasons.append(f"Content risk: {reason}")

        # External URL / IP detection
        url_match = _URL_PATTERN.search(text_clean)
        if url_match:
            suspicious_reasons.append(
                f"External URL or IP address detected: '{url_match.group(0)[:60]}'"
            )

        # Sensitive keyword detection
        for pattern in _SENSITIVE_KEYWORD_PATTERNS:
            kw_match = pattern.search(text_clean)
            if kw_match:
                suspicious_reasons.append(
                    f"Sensitive keyword detected: '{kw_match.group(0)}'"
                )

        if suspicious_reasons:
            logger.warning("[NoteGuard] Suspicious note flagged: %s", suspicious_reasons)
            return NoteVerdict("suspicious", suspicious_reasons, "medium")

        # ── Tier 1 — clean ───────────────────────────────────────────────────
        return NoteVerdict("allow", [], "low")

    @classmethod
    def check_storage_capacity(cls, data: dict) -> None:
        """Raise ValueError if total stored items would exceed the cap."""
        total = len(data.get("notes", [])) + len(data.get("reminders", []))
        if total >= _MAX_TOTAL_ITEMS:
            raise ValueError(
                f"Storage limit reached: already have {total} notes/reminders "
                f"(maximum {_MAX_TOTAL_ITEMS}). Delete some items first."
            )
