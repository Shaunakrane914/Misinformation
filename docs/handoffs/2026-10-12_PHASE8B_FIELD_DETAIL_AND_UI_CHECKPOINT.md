# Phase 8B field detail and UI checkpoint — 2026-10-12

This is an engineering checkpoint, **not** Phase 8 completion. Start with
[AGENTS.md](../../AGENTS.md), the [prior Phase 8B handoff](2026-10-12_PHASE8B_EXTRACTION_CHECKPOINT.md)
and the [schema matrix](../architecture/PHASE8B_MAXIMUM_EXTRACTION_SCHEMA_MATRIX.md).
Inspect the live worktree before editing.

## Scope and branch

- Owner request: continue the whole Phase 8 mandate, including the frontend,
  and report completion only after it is actually achieved.
- Work remains isolated on `feat/phase8b-extraction` because another coding
  agent was confirmed to be committing to `feat/phase8-real-acquisition-proof`.
  This checkpoint began at `5f75578b3ace28a1ee77e95969ca0a65bdff4358`.
  Do not rewrite, reset or auto-merge either branch.
- Implementation/evidence commit `3b8a95ff80ac627d85b3f7f13d68157703169f1e`
  was pushed to the isolated branch. No merge, deployment, credential change,
  frozen benchmark edit or historical dossier edit was made.

## Implementation and rationale

- [GitHub collection executor](../../backend/services/agent_reach/native/executor.py)
  accepts bounded explicit pages 1–5 and records observed `Link: rel=next`.
  [Routing normalization](../../backend/infrastructure/acquisition/routing/standard_handlers.py)
  retains issue/PR chronology and status, commit SHA/parents/API verification,
  release flags/assets and repository context. Body or list metadata is not
  misrepresented as source-code, review or binary evidence. Follow-up API
  requests for comments/reviews/diffs are not implemented.
- Captions retain up to 500 timed cues, filename language when observed, and
  `caption_origin: UNVERIFIED`. No audio transcription is inferred.
  [V2EX normalization](../../backend/services/agent_reach/native/normalizer.py)
  distinguishes reply ID from topic ID, sorts a bounded reply sample by
  observed creation epoch and avoids inventing an author or zero reply count.
- The [live probe runner](../../scripts/audits/run_phase8_live_acquisition_audit.py)
  now records bounded parsed adapter-item key names without values. These are
  **not** a complete raw-provider schema. The
  [17:37Z guarded pass](../../artifacts/phase8_extraction_spotchecks/2026-10-12_17-37-38Z/)
  returned classified usable output for 16/16 common targets. It was run on
  a dirty worktree before the commit; `run_metadata.json` records that exact
  limitation. The [v3 richness summary](../../artifacts/phase8_extraction_spotchecks/2026-10-12_17-37-38Z/richness_summary_v3.json)
  combines the retained Phase 8A scenarios with this newer common-case pass.
  No response body or credential was retained in the new records. The artifact
  was explicitly force-added only after checking for token-shaped secrets.
- The [shared report renderer](../../frontend/unified-report-renderer.js)
  rejects non-HTTP(S) evidence links, unwraps `unified_report` responses,
  uses native button controls for collapsible sections, shows the exact
  investigation target, exposes bounded acquisition lineage and channel
  outcome coverage, and labels non-primary/non-community evidence as
  “Other reporting” because source grouping alone does not establish
  independence. [CSS](../../frontend/aegis-theme.css) supplies responsive
  overflow/focus styling. This is frontend *contract hardening*, not the
  complete Stage 8E visual and workflow redesign.

## Verification actually observed

| Check | Result |
|---|---|
| Focused acquisition/summary tests after final adapter edits | 49 passed, exit 0 |
| Full `pytest tests/ -q -o addopts='--tb=short -ra'` after final staged changes | 1003 passed, exit 0 |
| Fast `pytest tests/unit tests/chaos tests/security -q -o addopts='--tb=short -ra'` | 807 passed, exit 0 |
| Fatal flake8 command from `AGENTS.md` | exit 0, 0 findings |
| Node frontend `test_*.js` suite | three scripts passed, exit 0, including the new report-renderer security/large-input test |
| Release-candidate smoke | exit 0, `OFFLINE_SMOKE_PASS`; test mocks/disabled acquisition only |
| Rollback compatibility, isolated worktree | exit 0, `OFFLINE_PERSISTENCE_PASS`; historical archive `NOT_VERIFIED` because ignored protected dossiers are absent there |
| Frozen benchmark hash verifier | exit 0 |
| Guarded live common-case probe | 16/16 operations yielded usable classified output, not a complete-content or hard-case guarantee |
| Browser visual screenshot | **NOT VERIFIED**: no browser surface was available in the computer-use inventory; static and Node tests are not a visual/accessibility audit |
| Hosted CI for `3b8a95f` | [run 38286579279](https://github.com/Shaunakrane914/Misinformation/actions/runs/38286579279) **passed**, exact `headSha` verified: fatal lint/frontend contracts; fast unit/chaos/security on Python 3.11, 3.12 and 3.13; entire offline suite, release/persistence validators and frozen/tracked-output integrity |

## Gate state and next safe work

**8A PASS** remains the prior live-acquisition gate. **8B PARTIAL**: parsed
field-name observation and GitHub bounded page access improved, but complete
provider field inventory, important-field population benchmarks, follow-up
requests/pagination cost and rich web article structure remain open.
**8C–8F are not accepted.** The Stage 8E frontend is not complete, despite
the shared-renderer improvements. The owner-requested “everything” is not done.

1. Continue Phase 8B with an agreed operation-by-operation field contract,
   fixture and live important-field checks, bounded continuation costs and
   documented optional/restricted/unavailable fields. Do not use raw-key counts
   as completeness percentages.
2. Then evaluate four-agent claim/entity/temporal/contradiction behavior on a
   held-out labeled set before claiming 8C gains. New source integrations
   require permission, live value and regression proof.
3. Build and test all four agent workflows and the shared investigation UI
   from verified backend fields. Obtain visual/narrow-screen/keyboard evidence
   where a browser becomes available. Do not mark 8E complete from static JS
   checks alone.
4. Reconcile the historical 55 malformed dossier limitation in the original
   checkout read-only; the isolated worktree's empty archive is not proof of
   historical recovery.

No private reasoning transcript, secret or unverified CI claim is recorded
here. Decisions and reproducible test pointers are the handoff.

## 2026-10-13 evidence-quality correction

The old 17:37Z run's `web.read` common-page excerpt was **not usable text**:
it contained 243 replacement/control characters in its first 400 characters
because the server sent gzip despite an `Accept-Encoding: identity` request.
The 16/16 result above is a historical *classifier output*, not proof that all
16 returned valid content. The old v3 summary and this handoff remain intact
for auditability; use the later corrected runs and v6 summary linked from the
[spot-check index](../../artifacts/phase8_extraction_spotchecks/README.md).
