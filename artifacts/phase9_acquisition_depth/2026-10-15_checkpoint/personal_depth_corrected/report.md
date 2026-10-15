# Four-agent API investigation audit

Commit: abe547f1e17aab5b54e90ff55e2d4783afa95283; dirty source: True.
Observed at: 2026-10-15T14:59:52.245470+00:00. Overall research gate: **PARTIAL**.

API execution, returned records and research correctness are assessed separately.
Independent precision, recall, entailment and LLM-injection success require separate adjudication.

| Agent | Execution | Returned records | URL-bearing records | Coverage | Correctness |
|---|---|---:|---:|---|---|
| personal_watch | PASS | 1 | 1 | REQUIRES_ADJUDICATION | NOT_VERIFIED |

## personal_watch

Exact request: {"name": "Tim Cook", "query": "Tim Cook recent public statements"}

- Returned record: Profile: Tim Cook (@tim_cook)
  URL: https://x.com/tim_cook
  Depth: PROFILE_METADATA; publication: 
  Retained passage: ### Profile: Tim Cook (@tim_cook)  Apple Executive Chairman

Complete sanitized API payloads are in summary.json. Claim-to-passage adjudication is required before a research PASS can be assigned.
