# Phase 9 remediation handoff — 2026-10-16

## Read this first

**Phase 9 is NOT fully accepted. Do not merge or deploy as a finished release.**
Read the [verification report](../testing/PHASE9_REMEDIATION_VERIFICATION_2026-10-16.md)
and [durable evidence index](../testing/evidence/2026-10-16_phase9_remediation/README.md).
Publication of the full application/report checkpoint and exact-commit hosted CI
is confirmed in the [CI closeout](2026-10-16_PHASE9_REMEDIATION_CI_CLOSEOUT.md).
The implementation fixes security/evidence defects but does not establish the
required increase in useful misinformation-verification coverage.

## User scope and workspace preservation

The user requested the Phase 9 packages, normal four-agent live output checks,
an API-key test, and useful instructions/evidence for subsequent agents. The
attachment authorizes development commits, branch push and hosted CI, not merge,
production deployment, paid services, historical-data repair or access bypass.

Fetched main/base: `ff6d246bfe1e9cfd0f21d8e32135582e631636f1`.
Branch: `feat/phase9-intelligence-remediation-20261016` in a new isolated
`phase9-remediation-20261016` worktree. The previous `phase9-main-release`
worktree's known 49 changed/new files were preserved in `9e5b6e3`, not silently
credited as new remediation. Its original dirty files and other agent worktrees
remain untouched. Inspect `git status --short`, branch and diff when resuming.

## Engineering conclusions and owner map

| Problem / decision | Implementation and regression pointers |
|---|---|
| Do not inject label authority or call citation presence entailment | `scripts/evaluation/run_phase9_benchmark.py`; `tests/unit/test_phase9_evaluation_integrity.py` |
| Preserve canonical IDs through specialized normalization | `backend/agents/brandshield/scanning.py`, `personal_watch/monitoring.py`, `trending/agent.py`; `test_phase9_intelligence_remediation.py` |
| Retain discovery separately from bodies; exact claims separately from purpose | Agent request builders, `application/research/acquisition.py`, `services/agent_reach/source_planner.py` |
| Reserve read opportunity; do not spend the entire deadline on escalation | `application/research/{acquisition,reading}.py`, `services/research/primary_source_escalator.py` |
| A successful explicit source read must not vanish or be fetched twice | `CandidateQualificationStage`, `DeepReadingStage`; source-body preservation regression |
| Grouped observations are not claim verdicts | `application/research/synthesis.py`; explicit claims reuse `claim_intelligence_engine`, metadata records the assessment |
| Numerical context and bibliographic boundaries matter | `services/research/proposition_grounding.py`; `test_phase9_grounding_context.py` |
| Official warnings are not attacker listings; valid IDs are not model entailment | BrandShield assessment, `services/research/model_grounding.py`, Scout assessment |
| Configured opaque Gemini credential is not verified availability | `core/settings.py`, `infrastructure/llm/providers/gemini.py`; header-only/rejected-key controls in `test_llm_gateway.py` |
| Preserve uncertainty, empty states, original links and excerpts on screen | `services/report_builder.py`, shared renderer, BrandShield page and theme; Node contracts plus rendered controls |

The current grounding remains lexical/heuristic. Scores are uncalibrated; neither
source count nor a matching ID proves a proposition. Registry-role presentation
and strategic summaries still need work. Avoid expanding whitelists, stripping
negation/periods, or lowering thresholds to recover fixture scores.

### Why old fixtures changed

Several old fixtures populated `content` but left the default `SNIPPET` depth.
Acquired-body fixtures now explicitly say `PARTIAL_CONTENT`; metadata controls
require no supported finding. Corporate root/locale pages are discovery leads,
while a separate corporate-document positive control remains. Historical Phase 4
and Phase 8 golden manifests stay unchanged. A new Phase 9 manifest records the
intentional policy/serialization changes; original candidate bytes/hashes and IDs
are still asserted. This is an agent-reviewed policy snapshot, not human validation.

## Verification actually observed

- Preserved baseline: **1,243 full** cases passed here. The **1,035 fast** baseline
  is the inherited handoff's reported snapshot, not a separately rerun pre-fix command.
- Final backend: **1,285 full / 1,077 fast** cases; fatal Flake8 zero; all eight
  Node scripts pass. Later frontend-only clipping/replay changes also passed Node
  and fatal lint, plus the 22-state rendered check.
- Smoke exit 0: isolated offline regression. Rollback exit 0:
  `OFFLINE_PERSISTENCE_PASS`, historical archive and deployed rollback NOT_VERIFIED.
- Frozen normalized hashes and protected-tree diffs passed. No benchmark labels,
  old golden manifests, dossiers, artifacts or research outputs were rewritten.
- Comparable supplied-reference resolution regressed: development 22→20/31,
  regression 17→14/20, existing held-out 8→5/28. Final recorded unsupported SUPPORT
  count is zero, not a proof of zero real-world false positives. No human-reviewed
  labels or independently measured calibration/entailment/retrieval recall.
- Eleven real claim probes and two named title rechecks. The corrected arXiv
  title pair supports/refutes the appropriate title, with actual source reads.
  A first true-title false refutation is retained, not hidden by the recheck.
- Twelve real button/SSE entity scans, three per agent: five records / 1,434 words;
  eight zero-acquisition inputs. All 24 viewport states preserve API-to-DOM counts.
  Source richness/research acceptance FAIL despite completed requests.
- CSS-only exact saved SSE replay: twelve saved results / 24 viewport states;
  NOT fresh acquisition. Seven verdict/hostile/large/empty fixture controls and
  exact report replays are separately labeled. Internal clipping was visually
  observed, measured as nine failures, then zero in the same 22-state check.
- Gemini presence/prefix bug fixed, but successful live generation NOT_VERIFIED.
  Existing generation attempts fail; a small documented Interactions probe also
  returned HTTP 503. No credential was printed, edited or committed.

### Reconstructed execution log, not a raw terminal transcript

1. Baseline full suite: 1,243 passed (exit 0).
2. New context controls: 9 failed / 2 passed before fixes, then 13 passed; later
   quote/conjunction/identifier controls reproduced three additional failures.
3. First broad post-change suite: 15 failed / 1,250 passed, including old snippet
   and golden-policy expectations. They were investigated, not blindly refreshed.
4. A later parallel-load run exposed a stream-test race: a heartbeat can precede
   worker admission. The test now waits for its running-worker event before
   testing cancellation; lock/429/cleanup assertions remain unchanged.
5. Full/fast/fatal/Node/smoke/rollback/frozen commands below were rerun. A regression
   set wire-independence false positive was found, fixed with a predicate guard
   and recorded in intermediate evidence. No held-out cases were inspected for tuning.
6. Backend checkpoint `8c8b6c5` was pushed and all five hosted jobs passed in
   [run 38928988850](https://github.com/Shaunakrane914/Misinformation/actions/runs/38928988850).
   Later frontend/documentation publication is distinct; check the branch's exact
   head and most recent hosted run rather than inferring acceptance from this run.

## Portable rerun commands

Run from the intended worktree. Use fresh output directories; never redirect
over tracked benchmark proof. Fresh logs from this session were retained under
the system-temp `aegis-phase9-remediation-*` directory; durable measurements and
selected screenshots are committed under `docs/testing/evidence/`.

```powershell
python -m pytest tests/ -q
python -m pytest tests/unit tests/chaos tests/security -q
python -m flake8 backend tests scripts --count --select=E9,F63,F7,F82 --show-source --statistics
python scripts/validate_release_candidate_smoke.py
python scripts/validate_rollback_compatibility.py
python scripts/validation/verify_frozen_benchmarks.py
git diff --exit-code -- tests/retrieval_benchmark artifacts research backend/data/dossiers
Get-ChildItem tests/frontend/test_*.js | ForEach-Object { node $_.FullName; if ($LASTEXITCODE) { throw $_.Name } }
```

Audit command templates (replace placeholders; never paste secret values):

```text
python scripts/evaluation/run_phase9_benchmark.py --split dev --output-dir <fresh-reference-output>
python scripts/audits/run_phase9_claim_probes.py --allow-live --env-file <private-server-env-file> --output-dir <fresh-claim-output>
python scripts/audits/run_phase9_four_agent_browser_audit.py --env-file <private-server-env-file> --chart-js <actual-pinned-chart-asset> --output-dir <fresh-browser-output>
python scripts/audits/run_phase9_four_agent_browser_audit.py --replay-dir <saved-browser-output> --env-file <private-server-env-file> --chart-js <actual-pinned-chart-asset> --output-dir <fresh-replay-output>
python scripts/audits/run_phase9_render_controls.py --claim-results <claim-summary-json> --chart-js <actual-pinned-chart-asset> --output-dir <fresh-render-output>
```

The live scripts need existing Playwright/Chromium and server-side credentials;
they isolate persistence/notifications, keep mocks off and reject existing output
directories. The environment file is read, not copied. Source-probe
`--case-ids scientific_title_true scientific_title_false` is an explicitly named
recheck, not an independent full matrix. No benchmark CLI defaults to tracked
artifact paths. Existing held-out metrics are reused diagnostic evidence, not a
fresh blind test. Collect a genuinely new reviewed holdout before claiming that.

## Next work, in priority order

1. Trace why exact issuer/filing queries still fail to deliver useful bodies.
   Add bounded linked financial-statement/PDF retrieval and metric-period binding
   to resolve the real Apple false-number case. Do not substitute EPS/revenue.
2. Review lost development/regression resolutions with traceable original passages;
   improve predicate/context attachment, not confidence or source counts. Obtain
   independently reviewed, untouched evaluation material.
3. Restore verified live Gemini inference only after an upstream success. Do not
   infer invalidity from the key's prefix or enable mocks to hide provider failures.
4. Improve registry-role presentation, passage boundaries and case-specific
   evidence-gap explanations. Keep profile/search metadata as leads.
5. Complete manual accessibility/contrast/axe, cross-browser/mobile and production
   parity checks. They remain UNVERIFIED. Retain all historical corruption and
   source-access limitations. Deployment requires separate owner approval.
