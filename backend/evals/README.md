# Poseidon evaluations

The starter dataset contains **synthetic, manually specified examples**. It proves the runner and rubric work; its scores are not a claim about Poseidon's real accuracy. Replace or extend it with cases you have reviewed from actual runs. Keep private prompts, vault excerpts, and credentials out of committed datasets.

[Review the 25 candidate cases](REVIEW.md) before recording actual responses. [The demo](DEMO.md) shows a synthetic wrong-citation failure and the judge's observed decision.

[Observed live Brain outputs](OBSERVED.md) show the first ten questions and the source rescan needed before they could be evaluated.

With the backend running locally, `venv\Scripts\python.exe backend/scripts/capture_brain_eval.py` records current Brain responses to the ignored `brain-rag-observed.jsonl` file. Run that file through the evaluator to inspect per-case checks. The candidate references still require human review before the result is presented as a benchmark.

Run the recorded cases from the repository root:

```powershell
$env:PYTHONPATH='backend'
python -m app.evals.runner backend/evals/starter.jsonl --output backend/evals/latest-report.json
```

Each JSONL row has a unique `id`, `input`, `reference`, `expected`, and `actual`. The `expected` object supports `contains`, `excludes`, `abstain`, `approval_required`, `active_agent`, `source_paths`, and `citations_required`. These deterministic checks run without an LLM. A failed check makes the command exit with code 1. Reports contain response text and may be sensitive; do not commit reports from real data.

To evaluate Brain against your current vault, supply reviewed Brain cases with `kind: "brain"`, an `input` question, and `expected` checks, then use `--live-brain`. This queries the configured Brain and records a query event. It requires the configured Brain model and source data; the starter dataset's synthetic source path is not expected to exist in your vault.

Add `--judge` to score answers from 0 (wrong or unsupported) to 2 (correct and supported). The judge uses Poseidon's configured model and refuses remote endpoints by default. `--allow-remote-judge` explicitly permits sending case content and excerpts to that provider. Judge scores are advisory: review disagreements against your human-written reference and source text.

For a useful project baseline, collect real cases across chat, memory retrieval, Brain answers, routing, and approval decisions. Record expected outcomes **before** changing prompts or models. Keep the same cases across runs and compare pass rate and individual failures; do not treat the synthetic starter score as a product metric.
