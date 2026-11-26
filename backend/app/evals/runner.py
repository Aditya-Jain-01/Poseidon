"""Run Poseidon evaluation cases with no model calls unless requested."""
from __future__ import annotations

import argparse
import asyncio
import json
import sys
import time
from pathlib import Path

from app.evals.core import evaluate_case, summary


def read_cases(path: Path) -> list[dict]:
    cases = []
    seen = set()
    for line_number, line in enumerate(path.read_text(encoding="utf-8-sig").splitlines(), 1):
        if not line.strip():
            continue
        case = json.loads(line)
        if not isinstance(case, dict) or not isinstance(case.get("id"), str) or case["id"] in seen:
            raise ValueError(f"{path}:{line_number}: each case needs a unique string id")
        if not isinstance(case.get("expected"), dict):
            raise ValueError(f"{path}:{line_number}: expected must be an object")
        seen.add(case["id"])
        cases.append(case)
    if not cases:
        raise ValueError("No cases found")
    return cases


async def run(path: Path, *, live_brain: bool = False, judge: bool = False,
              allow_remote_judge: bool = False, output: Path | None = None) -> dict:
    cases = read_cases(path)
    results = []
    for case in cases:
        started = time.perf_counter()
        actual = case.get("actual")
        if live_brain and case.get("kind") == "brain":
            from app.brain.service import BrainService
            from app.config import settings
            actual = await BrainService(settings.brain_vault_path, settings.poseidon_db_path).query("local_owner", case["input"])
        if actual is None:
            raise ValueError(f"{case['id']}: no recorded actual response; supply one or use --live-brain for Brain cases")
        result = evaluate_case(case, actual)
        result["run_ms"] = round((time.perf_counter() - started) * 1000, 2) if live_brain and case.get("kind") == "brain" else None
        if judge:
            from app.evals.judge import judge_case
            result["judge"] = await judge_case(case, actual, allow_remote=allow_remote_judge)
        results.append(result)
    report = {"summary": summary(results), "results": results,
              "mode": "live-brain" if live_brain else "recorded",
              "judge_enabled": judge}
    if output:
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description="Evaluate reviewed Poseidon responses")
    parser.add_argument("dataset", type=Path)
    parser.add_argument("--live-brain", action="store_true", help="Query the configured Brain vault; may log queries")
    parser.add_argument("--judge", action="store_true", help="Use Poseidon's configured model to score answers")
    parser.add_argument("--allow-remote-judge", action="store_true", help="Permit case data to reach a remote judge")
    parser.add_argument("--output", type=Path, help="Write a JSON report")
    args = parser.parse_args()
    try:
        report = asyncio.run(run(args.dataset, live_brain=args.live_brain, judge=args.judge,
                                 allow_remote_judge=args.allow_remote_judge, output=args.output))
    except (ValueError, OSError, json.JSONDecodeError) as exc:
        parser.exit(2, f"Evaluation failed: {exc}\n")
    print(json.dumps(report["summary"], indent=2))
    for result in report["results"]:
        print(f"{'PASS' if result['passed'] else 'FAIL'} {result['id']}")
    return 0 if report["summary"]["failed"] == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
