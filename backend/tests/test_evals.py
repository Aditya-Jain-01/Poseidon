from pathlib import Path

import pytest

from app.evals.core import evaluate_case, summary
from app.evals.runner import read_cases, run


def test_recorded_cases_score_and_report(tmp_path):
    path = Path(__file__).parents[1] / "evals" / "starter.jsonl"
    report_path = tmp_path / "report.json"
    report = __import__("asyncio").run(run(path, output=report_path))
    assert report["summary"] == {"cases": 5, "passed": 5, "failed": 0, "pass_rate": 1.0}
    assert report_path.is_file()


def test_unsupported_brain_answer_fails_checks():
    case = {"id": "wrong", "expected": {"contains": ["Friday"], "citations_required": True,
                                      "source_paths": ["raw/meeting.md"]}}
    result = evaluate_case(case, {"answer": "The meeting is Thursday.", "sources": []})
    assert not result["passed"]
    assert {check["name"] for check in result["checks"] if not check["passed"]} == {
        "contains:Friday", "source:raw/meeting.md", "citations_present", "quotes_present"}
    assert summary([result])["failed"] == 1


@pytest.mark.parametrize("answer", [
    "The provided excerpt does not mention who attended.",
    "The provided excerpts do not specify the model.",
])
def test_abstention_accepts_observed_wording(answer):
    result = evaluate_case({"id": "abstain", "expected": {"abstain": True}}, {"answer": answer})
    assert result["passed"]


def test_content_check_accepts_typographic_hyphen():
    result = evaluate_case({"id": "hyphen", "expected": {"contains": ["offline-first"]}},
                           {"answer": "An offline‑first company brain."})
    assert result["passed"]


def test_brain_abstention_uses_structured_field():
    case = {"id": "missing", "expected": {"abstain": True}}
    result = evaluate_case(case, {"answer": "The excerpt lacks that detail.", "sources": [], "abstained": True})
    assert result["passed"]


def test_dataset_rejects_duplicate_ids(tmp_path):
    file = tmp_path / "duplicate.jsonl"
    file.write_text('{"id":"same","expected":{}}\n{"id":"same","expected":{}}\n', encoding="utf-8")
    with pytest.raises(ValueError, match="unique string id"):
        read_cases(file)


@pytest.mark.asyncio
async def test_remote_judge_requires_explicit_opt_in(monkeypatch):
    from app.evals import judge
    monkeypatch.setattr(judge.llm_provider, "get_agent_resolved_config", lambda _: {
        "base_url": "https://example.com/v1", "model": "test"})
    with pytest.raises(ValueError, match="local model"):
        await judge.judge_case({"input": "private"}, {"answer": "private"})


@pytest.mark.asyncio
async def test_judge_receives_structured_routing_and_approval_fields(monkeypatch):
    import json
    from types import SimpleNamespace
    from app.evals import judge
    observed = {}

    async def complete(**kwargs):
        observed.update(json.loads(kwargs["messages"][1]["content"]))
        return SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(
            content='{"score":2,"reason":"Correct route and approval."}'))])

    monkeypatch.setattr(judge.llm_provider, "get_agent_resolved_config", lambda _: {
        "base_url": "http://localhost:11434/v1", "model": "test-model"})
    monkeypatch.setattr(judge.llm_provider, "get_client", lambda _: SimpleNamespace(
        chat=SimpleNamespace(completions=SimpleNamespace(create=complete))))
    result = await judge.judge_case({"input": "Route it", "reference": "Nereus"}, {
        "reply": "Working on it", "active_agent": "nereus", "approval_request": {"tool_name": "crm_write"}})
    assert observed["active_agent"] == "nereus"
    assert observed["approval_request"]["tool_name"] == "crm_write"
    assert result["model"] == "test-model"
