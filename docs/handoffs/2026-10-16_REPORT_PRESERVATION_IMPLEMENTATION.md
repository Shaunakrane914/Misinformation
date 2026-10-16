# Report preservation implementation — 2026-10-16

## Outcome and scope

The user approved the [acquisition improvement plan](../architecture/ACQUISITION_PIPELINE_IMPROVEMENT_PLAN_2026-10-16.md).
This checkpoint implements **Slice A: report preservation and truthful missing
data**, locally. The full six-slice plan is not complete. There was no deployment,
commit, push, hosted CI run or fresh live-provider acquisition during this task.

Working checkout: `release/phase9-acquisition-20261015`, base/HEAD
`ff6d246bfe1e9cfd0f21d8e32135582e631636f1`. The previous plan/index edits and
untracked planning/local-Reddit handoffs were preserved. The original IDE
checkout is a separate older worktree; it was not patched with these code changes.
Its ignored local Reddit flag remains true from the earlier operator request.
Production access and credentials were not changed.

## Implementation and decisions

- [Report builder](../../backend/services/report_builder.py): all four native
  adapters now preserve canonical/structured findings, citation IDs, richer
  canonical source records, native timeline field variants and actual
  `deep_research_trace.query_records`. Explicit caller `execution_log=[]` is
  respected rather than replaced by a truthy fallback. Legacy projections remain.
- [Unified schema](../../backend/schemas/unified_report.py): additive evidence IDs,
  `finding_details` and a separate `discovery` collection. Candidate observations
  are inspectable without adding them to acquired-source buckets. Citation
  observations distinguish SOURCE_RECORD, DISCOVERY_ONLY and UNAVAILABLE;
  these are presence/depth labels, not entailment or accuracy scores.
- A shared completion helper was used instead of four parallel fixes, because
  the production defect repeated at every adapter boundary. Rich native records
  take precedence over abbreviated legacy summaries; findings retain native
  details even when their legacy string text is deduplicated. Existing report
  schema/version fields remain compatible; new fields are additive/optional.
- [Renderer](../../frontend/unified-report-renderer.js): shows retained findings,
  reported epistemic state, citation availability, evidence IDs and a separate
  expandable discovery-only section. No auto-read or unescaped content added.
  When native summary prose is absent, the builder emits only a deterministic
  retained-record count brief, with a passage-review limitation—not an invented
  financial conclusion. Structured numeric summaries are not Python-dict prose.
- [Scout](../../backend/agents/scout/agent.py): unavailable price/change/z-score
  and anomaly flags stay null. Missing market inputs produce NOT ASSESSED rather
  than a zero-valued normal assessment. [Assessment](../../backend/agents/scout/assessment.py)
  returns INSUFFICIENT_EVIDENCE / UNASSESSED with unknown quality when no acquired
  sources exist. Positive `catalyst` and legacy `factor` entries both survive.
- [Extraction API](../../backend/api/agent_reach.py): platform names may contain
  digits after the initial letter, so registered `v2ex` operations reach native
  validation. Executable-operation checks and access/SSRF boundaries remain.
- [Browser replay runner](../../scripts/audits/audit_phase9_evidence_inspector.py):
  opens only the outer ancestors of an inspected disclosure before checking
  Enter on the actual inner disclosure; supports the new nested discovery UI.

The testing/refactoring skills guided failing regressions, shared boundary
normalization and small source changes. No planner, scraper transport, provider
permission, research scoring engine or historical ledger was rewritten.

## Regression map and actual results

New [native-to-report tests](../../tests/unit/test_agent_report_preservation.py)
cover four actual normal and streaming route handlers (only agent acquisition
stubbed), report immutability, canonical bodies versus lossy summaries,
discovery-only boundaries, missing citations, structured findings, explicit empty
logs, unknown quotes and Node execution of the actual shared renderer.
Fixtures are synthetic contract data, not independently adjudicated evidence.

[Extraction API tests](../../tests/unit/test_phase9_extraction_api.py) exercise
all four protected V2EX operations through the actual API route. Extended
[renderer tests](../../tests/frontend/test_unified_report_renderer.js) include
hostile finding/citation/discovery strings and unsafe URLs. The old
[empty-source Scout test](../../tests/unit/test_scout_research_terminal.py) was
updated to assert insufficient evidence, unassessed risk and unknown quality;
its prior NOMINAL expectation would perpetuate the reported bug.

Reconstructed command record, not a raw transcript:

| Command/check actually run | Exit | Observed result |
|---|---:|---|
| Initial new regression collection | 1 | Corrected a new test parameter named `request`, reserved by pytest |
| New preservation/extraction regressions before fixes | 1 | 14 failed, 7 passed; reproduced four-agent loss, unavailable quote zeroes and V2EX rejection |
| Four focused unit files after final edge cases | 0 | 100 passed in 3.46s |
| First full/fast runs | 1 each | 1,242 / 1,034 passed; one legacy test still required NOMINAL on no acquired evidence |
| `python -m pytest tests/ -q --tb=short` after correction | 0 | **1,243 passed in 90.83s** |
| `python -m pytest tests/unit tests/chaos tests/security -q --tb=short` | 0 | **1,035 passed in 45.94s** |
| `python -m flake8 backend tests scripts --count --select=E9,F63,F7,F82 --show-source --statistics` | 0 | Zero fatal findings; rerun after the final source/test changes |
| All eight `node tests/frontend/test_*.js` scripts, separately | 0 each | Passed; renderer script rerun after its edge-case additions |
| `python scripts/validation/verify_frozen_benchmarks.py` | 0 | Frozen content hashes verified |
| `python scripts/validate_release_candidate_smoke.py --output <new-temp-file>` | 0 | OFFLINE_SMOKE_PASS; mocks/temp storage, not live or production readiness |
| `python scripts/validate_rollback_compatibility.py --output <new-temp-file>` | 0 | OFFLINE_PERSISTENCE_PASS; historical archive and deployed previous version NOT_VERIFIED |
| Saved October 15 native responses reprojected through changed report builder | 0 | Scout finding/query records restored and candidate retained separately; BrandShield/Personal findings and acquired records retained; Trending still has no acquired evidence |
| Chromium inspector replay: current report projections plus labeled hostile controls | 0 | 24 states at 320/390/1440px; zero detected overflow, page errors, injected images or unsafe links; disclosure/source-control checks passed |
| Protected-path tracked diff / `git diff --check` | 0 | No tracked evaluation/research/artifact/dossier changes; no whitespace errors |

The browser check used a temporary loopback static server and rebuilt saved
responses, not fresh backend/provider integration. Two actual screenshots were
visually inspected: Scout at 390px and BrandShield at 1440px. No axe or manual
screen-reader acceptance, whole-site visual acceptance, provider health or new
research accuracy is claimed. Screenshot/log outputs use a fresh system-temp
`aegis-preservation-validation-*` directory and are not durable committed proof.

## Remaining work and safe continuation

1. Slice B: reviewed one-line entity/intent/region parsing and candidate-community
   planning. Existing generic-only Tata Motors/Infosys mappings remain unchanged.
2. Slice C: investigate Stack Overflow's missing bodies, relevant selected-page
   depth and original-versus-archive context. The local Reddit smoke did not
   validate company-specific post relevance or full comments.
3. Slice D: internal research deadlines/read opportunity and health-count
   consistency. Browser wait extensions do not fix acquisition starvation.
4. Slice E: richer agent-specific views and eventual legacy/unified-view
   consolidation. Existing heuristic scores/causal language outside the corrected
   missing-data branch are not newly validated by this work.
5. Slice F: independent claim-support evaluation, deployment-shaped live tests,
   exact-commit hosted CI, staging rollback and access-owner review before rollout.

Do not blindly merge ranked candidates into acquired evidence to inflate counts,
fill missing text from findings, or interpret citation presence as support.
Preserve frozen data and protected historical dossiers. Read the working diff
before resuming; notes from earlier tasks are not permission to stage everything.
