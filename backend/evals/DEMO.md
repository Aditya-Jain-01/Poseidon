# Recruiter demo: evaluation and judge

The 25 rows in [candidates.jsonl](candidates.jsonl) are a **review queue**, not a benchmark. Every row has `review_status: needs_human_review`. Only the three supported Brain questions and seven abstention questions use the current `team-meeting.md` source. Chat, tool, and routing cases need captured Poseidon responses and some need disposable test data. Do not report their pass rate until you review the references and record real `actual` responses.

## Show a caught failure

From the repository root:

```powershell
$env:PYTHONPATH='backend'
python -m app.evals.runner backend/evals/demo_bad_citation.jsonl
```

The command prints `FAIL demo-bad-citation` and exits with code 1. The answer text is correct, but it cites `raw/unrelated.md` instead of `raw/team-meeting.md`.

To show the **LLM judge's** decision, run the same case with `--judge --output backend/evals/demo-judge-report.json` while a local model is available. Add `--allow-remote-judge` only when the demo data is safe to send to the configured provider. In the observed synthetic run, the configured `openai/gpt-oss-120b` judge scored it **1/2**, correctly saying that the citation points to an unrelated source. The report is ignored by Git because real reports may contain private text.

## Build a real result table

For each reviewed candidate, add the captured response as `actual` in a private copy of the JSONL file. Run that copy with `--output backend/evals/real-report.json`, optionally adding `--judge`. Keep private reports out of Git. Compare judge decisions with your expected outcomes; record at least one disagreement and the rubric or prompt change it led to.

| Dataset | Cases | Deterministic pass rate | Judge 0 / 1 / 2 | Judge model | Status |
| --- | ---: | ---: | --- | --- | --- |
| Synthetic starter | 5 | 5/5 | 0 / 0 / 5 | openai/gpt-oss-120b | Runner smoke test only |
| Synthetic bad citation | 1 | 0/1 | 0 / 1 / 0 | openai/gpt-oss-120b | Wrong source path caught |
| Candidate review queue | 25 | — | — | — | Needs reviewed references and captured responses |
| Real reviewed benchmark | — | — | — | — | Pending |

The first judge run scored the synthetic routing case 0/2 even though the deterministic check passed: the judge prompt only included answer text, while the route was in the structured `active_agent` field. The judge now receives relevant structured fields, and a second run scored the case 2/2. This is a rubric/payload fix, not a measured improvement in Poseidon's real task accuracy.

A short screen recording can show the command, failure line, and JSON judge decision. Keep any sensitive case data out of the recording.
