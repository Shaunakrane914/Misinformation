# Phase 8B clean full re-probe and richness runner — 2026-10-13

## Scope, branch and decisions

Continuing the user-authorized Phase 8 mandate, this checkpoint measured the
16 protected recovered operations across three bounded live scenarios each.
Work stayed in the isolated `feat/phase8b-extraction` worktree because another
coding agent was active on the original Phase 8 branch. The observed starting
commit was `8dce5412ab7c3ab4de2d1d6239e4f658bb27e756`, whose exact
[CI run 38374526123](https://github.com/Shaunakrane914/Misinformation/actions/runs/38374526123)
passed all five hosted jobs. The new evidence, documentation and summary-runner
fix were committed and pushed as
`a465b2b0516f45ac9c3e4ddeea5f35e92fa7286c`. No merge, deployment,
credential change, original-worktree mutation or protected-data modification
was performed.
Its exact [hosted CI run 38375446244](https://github.com/Shaunakrane914/Misinformation/actions/runs/38375446244)
completed successfully in all five jobs: fatal lint/frontend, full offline
suite/persistence/smoke, and unit/chaos/security on Python 3.11, 3.12 and
3.13. Hosted CI does not replay the live-provider probe or the browser audit.

The live runner itself was invoked as a module so Python loaded the intended
checkout. Its [run metadata](../../artifacts/phase8_extraction_spotchecks/2026-10-13_09-13-13Z/run_metadata.json)
records clean worktree, commit, interpreter, budget and credential *presence*
flags, not credential values. It generated
[48 bounded probe records](../../artifacts/phase8_extraction_spotchecks/2026-10-13_09-13-13Z/probe_records.jsonl)
and an [8A acceptance result](../../artifacts/phase8_extraction_spotchecks/2026-10-13_09-13-13Z/acceptance.json).
All 16 operations had at least one actual-live, honestly classified result;
30 of 48 individual probes were live-verified. The rest were designed edge
or inaccessible cases, including `NOT_FOUND`, `EMPTY_RESULT`, and one
`NETWORK_FAILURE`. This is **Phase 8A connectivity PASS**, not uptime or
extraction-completeness proof.

The [richness summary](../../artifacts/phase8_extraction_spotchecks/2026-10-13_09-13-13Z/richness_summary_v12.json)
was generated from that run alone. It reports measured important-field
population per successful normalized sample and relevant text lengths for all
16 operations; the [schema matrix](../architecture/PHASE8B_MAXIMUM_EXTRACTION_SCHEMA_MATRIX.md)
has the compact table and interpretation. This does not infer complete raw
provider schemas. During generation, `python -m
scripts.audits.summarize_phase8_extraction` failed because the script imported
its sibling only as a top-level module. The
[fix](../../scripts/audits/summarize_phase8_extraction.py) makes both module
and legacy file-path invocations load this checkout, with a
[regression test](../../tests/unit/test_phase8_extraction_summary.py). This
prevents editable-installed other-worktree contamination and keeps the
summarizer no-network, append-only and overwrite-refusing.

## Validation actually run

| Check | Result |
|---|---|
| `python -m scripts.audits.run_phase8_live_acquisition_audit --output-root artifacts/phase8_extraction_spotchecks --max-scenarios 3` | Exit 0, `PHASE8A_GATE=PASS`; clean run on `8dce541`, 16/16 operations and 30/48 live individual probes. |
| `python -m scripts.audits.summarize_phase8_extraction --probe-records artifacts/phase8_extraction_spotchecks/2026-10-13_09-13-13Z/probe_records.jsonl --output artifacts/phase8_extraction_spotchecks/2026-10-13_09-13-13Z/richness_summary_v12.json` | Exit 0; 16-operation summary created exclusively, without network. |
| `pytest tests/ -q -o addopts='--tb=short -ra'` | Exit 0; 1040 passed. |
| `pytest tests/unit tests/chaos tests/security -q -o addopts='--tb=short -ra'` | Exit 0; 844 passed. |
| `pytest tests/unit/test_phase8_extraction_summary.py -q -o addopts='--tb=short -ra'` | Exit 0; one test, including both CLI invocation modes and overwrite refusal. |
| `flake8 backend tests scripts --count --select=E9,F63,F7,F82 --show-source --statistics` | Exit 0; zero selected fatal errors. |
| All five Node `tests/frontend/test_*.js` files | Exit 0; simulated-DOM frontend contracts passed. |
| `python scripts/validation/verify_frozen_benchmarks.py` | Exit 0; frozen hashes verified. |
| `python scripts/validate_release_candidate_smoke.py` | Exit 0; `OFFLINE_SMOKE_PASS`; not live/provider or production proof. |
| `python scripts/validate_rollback_compatibility.py` | Exit 0; `OFFLINE_PERSISTENCE_PASS`; archive and deployed rollback `NOT_VERIFIED` here. |
| `git diff --cached --check`, protected frozen/dossier/research diff and bounded credential-pattern scan | Exit 0/no matches for the scan; new run artifacts were intentionally appended, never overwritten. |

## Open acceptance boundaries

Stage 8B remains **PARTIAL**. The summary counts populated fields in a small
successful sample, not all optional provider fields. GitHub discussions,
YouTube reply continuation, web article completeness, RSS linked-page reads,
V2EX and podcast pagination, difficult-case reliability, rate-limit behavior
and marginal per-item cost remain incomplete or unverified as stated in the
schema matrix. Stage 8C four-agent usefulness/truth evaluation, Stage 8D new
sources and Stage 8F final release acceptance cannot be inferred from this
run. Frontend Node contracts passed, but a real-browser visual/responsive/
accessibility check is still **NOT_VERIFIED**: this session's computer-use
inventory had no browser or app, and creating an in-app browser returned
“Browser is not available.” The temporary local HTTP server was stopped;
no UI screenshots or browser success are claimed. Stage 8E is therefore not
complete. Historical dossier readability and deployed rollback also remain
outside the evidence of this isolated checkout. No production deployment is
authorized.

Next agent: inspect branch status and exact hosted CI for `a465b2b` before
building on this checkpoint. Use the v12 summary to prioritize actual missing
fields and pagination; do not reinterpret sample population rates as provider
completeness, turn index snippets into target-page proof, or fabricate missing
articles, transcripts, dates, comments or author attribution.
