# Observed Poseidon outputs

Captured from the running local `POST /brain/query` endpoint on 2026-11-26. These are **live Brain responses**, not human-approved benchmark results. The raw response data and per-check results are in the local ignored files `brain-rescanned-observed.jsonl` and `brain-rescanned-report.json`.

| ID | Question | Poseidon's answer | Deterministic check |
| --- | --- | --- | --- |
| brain-001 | What did the team decide to build? | The team decided to build an offline-first company brain. | Pass; cited `raw/team-meeting.md` |
| brain-002 | How will Obsidian be used? | Obsidian will be used to display the source notes and the generated topic pages. | Pass; cited `raw/team-meeting.md` |
| brain-003 | Did the team choose a cloud-first brain? | No, the team chose to build an offline-first company brain, not a cloud-first one. | Pass; cited `raw/team-meeting.md` |
| brain-004 | What date was the decision made? | I couldn't find supporting evidence in the Brain. | Pass; abstained |
| brain-005 | Who attended the team meeting? | The provided excerpt does not mention who attended the team meeting. | Pass; abstained |
| brain-006 | Which embedding model did the team select? | The provided excerpts do not specify which embedding model the team selected. | Pass; abstained |
| brain-007 | What is the budget for the brain? | I couldn't find enough supporting evidence in the Brain. | Pass; abstained |
| brain-008 | Who owns the Obsidian vault? | I couldn't find enough supporting evidence in the Brain. | Pass; abstained |
| brain-009 | Which cloud provider hosts the brain? | I couldn't find enough supporting evidence in the Brain. | Pass; abstained |
| brain-010 | What is the deadline for launch? | I couldn't find supporting evidence in the Brain. | Pass; abstained |

The first run returned “I couldn't find supporting evidence in the Brain” for **all 10** questions: seven abstention cases passed and three source-backed cases failed. The source file's hash differed from its indexed hash, so retrieval skipped it. After `POST /brain/sync` processed `raw/team-meeting.md`, the rerun passed **10/10** deterministic checks. The checker initially mislabeled `brain-005` and `brain-006` as failures because it did not recognize “does not mention” or “do not specify” as abstentions; that wording is now covered by tests.

The remaining `chat-011` through `route-025` cases have **no captured output**. They need controlled conversation context or disposable local data, and their references still need review. See [REVIEW.md](REVIEW.md) before treating any pass rate as a product metric.

## Local embedding RAG check

After adding local `all-MiniLM-L6-v2` passage embeddings and combining semantic and FTS5 ranks, `backend/scripts/capture_brain_eval.py` captured the same ten Brain questions through the running API as UTF-8 JSON. The deterministic runner passed **10/10** in the local ignored `brain-rag-report.json`. Three answers cited the meeting note and seven returned a structured abstention. This checks that the current demo vault still answers these questions; it does not measure retrieval recall on a diverse reviewed dataset or validate every citation semantically.
