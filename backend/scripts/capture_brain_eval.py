"""Capture live Brain API responses for review without changing candidate cases."""
from __future__ import annotations

import json
import sys
from pathlib import Path
from urllib.request import Request, urlopen


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.evals.runner import read_cases  # noqa: E402


def main() -> None:
    dataset = ROOT / "evals" / "candidates.jsonl"
    output = ROOT / "evals" / "brain-rag-observed.jsonl"
    captured = []
    for case in read_cases(dataset):
        if case.get("kind") != "brain":
            continue
        payload = json.dumps({"question": case["input"]}).encode("utf-8")
        request = Request("http://127.0.0.1:8000/brain/query", data=payload,
                          headers={"Content-Type": "application/json"}, method="POST")
        with urlopen(request, timeout=90) as response:
            actual = json.loads(response.read().decode("utf-8"))
        captured.append({**case, "actual": actual})
        print(f"{case['id']}: {ascii(actual['answer'])}")
    output.write_text("\n".join(json.dumps(case, ensure_ascii=False) for case in captured) + "\n", encoding="utf-8")
    print(f"Saved {len(captured)} responses to {output}")


if __name__ == "__main__":
    main()
