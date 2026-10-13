# Current project state — 2026-10-13

This is the maintained status entry point for `feat/phase8b-extraction` at
`e74b9847ab107e2793f69e2155914028f02391b6`. It is a dated observation,
not a claim that every future checkout or deployment has the same state. Read
the [latest handoff](handoffs/README.md), inspect `git status --short --branch`
and the checked-out commit, then use the code and tests as the source of truth.
The separate `feat/phase8-real-acquisition-proof` worktree is older and does
not yet contain this branch's Phase 8B/8C/8E implementation; do not silently
combine their test counts or source files.

## Phase 8 acceptance

| Gate | State | Evidence and boundary |
|---|---|---|
| 8A — real acquisition proof | PASS for the bounded 16-operation clean-commit re-probe | [48-scenario record](../artifacts/phase8_extraction_spotchecks/2026-10-13_09-13-13Z/) and [handoff](handoffs/2026-10-13_PHASE8B_FULL_REPROBE_AND_SUMMARY_RUNNER.md). This is sampled live connectivity/content-depth proof, not universal provider availability. |
| 8B — maximum extraction | PARTIAL | [Field matrix](architecture/PHASE8B_MAXIMUM_EXTRACTION_SCHEMA_MATRIX.md) distinguishes captured, conditional and missing fields. Pagination, full discussions and complete provider schemas remain unproved. |
| 8C — four-agent intelligence | PARTIAL | [Research-truth checkpoint](handoffs/2026-10-13_PHASE8C_8E_TRUTH_AND_RENDERING.md) removes unsupported contradiction and identity-certainty claims; evaluated claim-level usefulness is still outstanding. |
| 8D — source expansion | NOT ACCEPTED | No new source should be called production-ready without permission assessment, real acquisition proof, provenance, tests and measured added value. |
| 8E — frontend redesign | PARTIAL | Four agent pages were improved and [rendered in Chromium](../artifacts/phase8_frontend_visual/2026-10-13_final_truthful_labels/summary.json) at 1440/390/320px. [Automated axe](../artifacts/phase8_frontend_accessibility/2026-10-13_final_truthful_labels_axe/summary.json) found zero violations in 12 initial states, but contrast checks were incomplete on gradients. Live backend-result, large-set and manual screen-reader acceptance remain open. |
| 8F — final integration/research-quality audit | NOT ACCEPTED | Offline regressions and hosted CI pass; adversarial real-world investigation quality and release acceptance have not been established. |

The 16 protected operations are listed in [AGENTS.md](../AGENTS.md) and
exercised by [route-contract tests](../tests/unit/test_recovered_operation_routes.py).
The runtime also exposes auxiliary channels; a count of registered channels,
eligible operations, or successful test fixtures is not a count of healthy
live providers. All external reads remain bounded and may legitimately return
`EMPTY_RESULT`, `AUTH_REQUIRED`, `RATE_LIMITED` or another non-success class.

## Executed system and evidence boundaries

FastAPI routers in [`backend/api/`](../backend/api/) handle claim submission,
the four specialist scans, acquisition diagnostics, replay and system status.
Claim verification proceeds through source planning, the shared acquisition
runtime, evidence qualification, research and verdict synthesis. The
[production-path trace](architecture/PHASE8_INVESTIGATION_PATH_TRACE.md)
identifies concrete owners and remaining bypass risks. The four static
[agent pages](../frontend/README.md) render supplied backend data and explicit
absence/uncertainty states; a safe clickable URL is not a verified publisher,
a user-entered handle is not an official identity, and an empty finding list
is not proof of truth. Simulation and offline ML benchmark metrics are not
live misinformation-verdict accuracy.

## Verification snapshot and limits

On this branch before the documentation-only update, local commands reported
`pytest tests/ -q`: **1,051 passed**; `pytest tests/unit tests/chaos
tests/security -q`: **855 passed**; all six Node frontend scripts, fatal
Python lint, frozen-hash verification and isolated release smoke passed. The
offline rollback check passed against fresh temporary persistence, while the
historical archive was `NOT_VERIFIED` in the isolated worktree. Hosted
[GitHub Actions run 38420523255](https://github.com/Shaunakrane914/Misinformation/actions/runs/38420523255)
passed all five jobs for exact commit `e74b984`. It does not run a hosted
browser or live-provider matrix. Current documentation edits require their
own validation before this snapshot is extended.

The protected historical dossier inventory in the original worktree reported
55 malformed JSON files. Those files are not present for inspection in this
isolated worktree and must never be overwritten or silently repaired. The
frozen retrieval datasets, `research/`, prior `artifacts/`, working scrapers
and compatibility shims are protected. Neither offline tests nor this status
document authorize a production deployment, merge to `main`, or launch claim.

## Documentation reading paths

- New contributor: [README](../README.md) → [developer guide](development/README.md)
  → [testing/CI](testing/CI_COVERAGE_MATRIX.md) → [latest handoff](handoffs/README.md).
- Architecture/research reviewer: [target architecture](architecture/TARGET_ARCHITECTURE.md)
  → [executed path](architecture/PHASE8_INVESTIGATION_PATH_TRACE.md)
  → [8B field matrix](architecture/PHASE8B_MAXIMUM_EXTRACTION_SCHEMA_MATRIX.md).
- Operator: [production configuration](operations/PRODUCTION_CONFIGURATION_MATRIX.md)
  → [rollback limitations](operations/ROLLBACK_VERIFICATION.md)
  → [current CI coverage](testing/CI_COVERAGE_MATRIX.md).

Older phase reports, benchmark results and handoffs are immutable historical
evidence. Their past-tense numbers or readiness assessments do not override
this dated status, the checked-out code, or a new verification run.
