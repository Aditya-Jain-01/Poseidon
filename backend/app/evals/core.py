"""Deterministic checks for recorded Poseidon responses."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any


def _comparable(text: str) -> str:
    return " ".join(text.casefold().translate(str.maketrans({
        "‐": "-", "‑": "-", "‒": "-", "–": "-", "—": "-", "−": "-",
    })).split())


@dataclass(frozen=True)
class Check:
    name: str
    passed: bool
    detail: str = ""

    def as_dict(self) -> dict[str, Any]:
        return {"name": self.name, "passed": self.passed, "detail": self.detail}


def evaluate_case(case: dict[str, Any], actual: dict[str, Any] | None = None) -> dict[str, Any]:
    """Score one reviewed case without a model or network access."""
    case_id = case["id"]
    expected = case.get("expected", {})
    actual = actual if actual is not None else case.get("actual", {})
    if not isinstance(actual, dict):
        raise ValueError(f"{case_id}: actual must be an object")
    answer = actual.get("answer", actual.get("reply", ""))
    if not isinstance(answer, str):
        raise ValueError(f"{case_id}: answer must be a string")
    folded = _comparable(answer)
    checks: list[Check] = []
    for phrase in expected.get("contains", []):
        checks.append(Check(f"contains:{phrase}", _comparable(phrase) in folded))
    for phrase in expected.get("excludes", []):
        checks.append(Check(f"excludes:{phrase}", _comparable(phrase) not in folded))
    if "abstain" in expected:
        if type(actual.get("abstained")) is bool:
            abstains = actual["abstained"]
        else:
            abstains = any(term in folded for term in (
                "couldn't find", "not enough", "insufficient evidence", "don't know", "cannot determine",
                "does not mention", "do not mention", "does not specify", "do not specify", "not specified",
            ))
        checks.append(Check("abstain", abstains == expected["abstain"]))
    if "approval_required" in expected:
        checks.append(Check("approval_required", bool(actual.get("approval_request")) == expected["approval_required"]))
    if "active_agent" in expected:
        checks.append(Check("active_agent", actual.get("active_agent") == expected["active_agent"]))
    if "source_paths" in expected:
        sources = actual.get("sources", [])
        paths = {item.get("path") for item in sources if isinstance(item, dict)}
        for path in expected["source_paths"]:
            checks.append(Check(f"source:{path}", path in paths))
    if expected.get("citations_required"):
        sources = actual.get("sources", [])
        checks.append(Check("citations_present", bool(sources)))
        checks.append(Check("quotes_present", bool(sources) and all(
            isinstance(source.get("evidence"), str) and source["evidence"].strip()
            for source in sources if isinstance(source, dict)) and all(isinstance(source, dict) for source in sources)))
    if not checks:
        raise ValueError(f"{case_id}: no deterministic checks configured")
    return {"id": case_id, "passed": all(check.passed for check in checks),
            "checks": [check.as_dict() for check in checks], "answer": answer,
            "actual": actual}


def summary(results: list[dict[str, Any]]) -> dict[str, Any]:
    passed = sum(result["passed"] for result in results)
    return {"cases": len(results), "passed": passed, "failed": len(results) - passed,
            "pass_rate": round(passed / len(results), 3) if results else 0}
