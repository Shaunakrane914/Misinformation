# Current project state — 2026-10-14

Current review branch: `feat/phase8-independent-audit-codex`, based on Gemini
`a10fde82467df21508b4a254507b414cd5b6e9fd`. Implementation checkpoints
`195ae0a`, `220f16f`, `d58c5ba`, `c420296` and `0f5a659`; later commits package proof and documentation.
Inspect the checked-out commit and worktree before continuing.

Start with the [independent Phase 8 review](architecture/PHASE8_INDEPENDENT_REVIEW_2026-10-14.md)
and [handoff](handoffs/2026-10-14_PHASE8_INDEPENDENT_REVIEW.md).
Earlier all-stage completion claims do not override independent evidence.

## Acceptance

| Stage | State | Boundary |
|---|---|---|
| 8A acquisition | PASS, bounded sample | All 16 protected operations returned real samples. Not uptime, full history or unrestricted provider access. |
| 8B extraction | PARTIAL | Full pagination, filing/XBRL bodies and full academic papers remain incomplete. |
| 8C intelligence | PARTIAL | Source spoofing, unrelated support, manufactured citations and specialist false certainty corrected. General semantic adjudication is not calibrated. |
| 8D expansion | PARTIAL | SEC/NVD/arXiv/FactCheck registered in shared runtime. SEC contact and FactCheck key required; added claim value not fully verified. |
| 8E frontend | PARTIAL | Chromium/API-replay and hostile/large-input checks; mobile/accessibility corrections. Contrast, manual screen reader and evidence-rich live acceptance remain open. |
| 8F integration | PARTIAL; release gate unmet | API and persistence execution work; sparse coverage and independent accuracy/recall not accepted. |

## Dated evidence snapshot

Full offline suite **1,156 passed**; fast suite **948 passed**. Fatal Python
lint, all seven Node frontend scripts and frozen hashes pass. Isolated smoke
and persistence/rollback readers pass; historical archive and deployed
rollback remain **NOT_VERIFIED**.

Clean `220f16f` Apple API run: 3/0/0/0 evidence records; four HTTP 200 responses
and assembled unified reports. Mocks disabled, no live LLM key, deterministic
fallback used. This is not a correct-investigation PASS. Ten source-adjudicated
holdout cases: safe outcomes 10/10, **truth resolution 0/4** before and after.
Not human ground truth, population accuracy, precision or recall.

Post-fix narrow-browser replay/stress has zero observed axe violations,
script images, unsafe links or document overflow. Gradient contrast and
manual assistive-technology acceptance remain open.
[Proof](../artifacts/phase8_independent_review/) is append-only.
[CI closeout](handoffs/2026-10-14_PHASE8_INDEPENDENT_CI_CLOSEOUT.md) separates
remote verification from local tests; baseline CI does not verify new changes.

## Preserve and continue

Frozen retrieval datasets, all historical dossiers, `research/`, old
`artifacts/`, scrapers and shims remain unchanged. The original workspace
inventory reported 55 malformed dossiers; no repair or overwrite occurred.
No merge, deployment, paid provider or production-secret change.

Prioritize external claim-to-passage adjudication, claim-relevant discovery,
issuer/period/unit-aligned financial evidence, citation entailment,
authorized model/provider checks, lineage and evidence-rich accessibility.
An official hostname, heuristic confidence or valid citation ID is not truth.

Read the [target architecture](architecture/TARGET_ARCHITECTURE.md),
[executed path](architecture/PHASE8_INVESTIGATION_PATH_TRACE.md),
[extraction matrix](architecture/PHASE8B_MAXIMUM_EXTRACTION_SCHEMA_MATRIX.md),
[configuration](operations/PRODUCTION_CONFIGURATION_MATRIX.md),
[CI coverage](testing/CI_COVERAGE_MATRIX.md) and [handoff index](handoffs/README.md).
Historical reports are retained as dated snapshots, not permanent acceptance.
