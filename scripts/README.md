# Command-line tools

Run these from the repository root. For complete verification commands see
[Testing](../docs/TESTING.md).

| Tool | Purpose |
| --- | --- |
| `validate_release_candidate_smoke.py` | Isolated offline API/agent smoke validation |
| `validate_rollback_compatibility.py` | Temporary persistence and archive-reader checks |
| `validation/verify_frozen_benchmarks.py` | Verify immutable retrieval fixture hashes |
| `evaluate_dataset.py` | Classical ML/reranker experiments; use a fresh output directory |
| `run_retrieval_quality_benchmark.py` | Frozen retrieval evaluation |
| `audits/run_terminal_agent_quality.py` | Explicitly opted-in bounded specialist investigations |
| `audits/website_word_yield.py` | Source, passage and published-word accounting |
| `audits/audit_evidence_workbench.py` | Saved report workbench inspection |
| `diagnostics/verify_deployed_candidate.py` | Explicit deployed-candidate verification |

Other retained audit modules support regression tests, saved-source replay or the
bounded runner. Do not import executable diagnostics into the application or run
live probes automatically. Generated outputs, credentials and local traces are ignored.
Compatibility wrappers remain for existing CLI users.
