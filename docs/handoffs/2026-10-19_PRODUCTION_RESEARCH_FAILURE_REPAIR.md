# October production-failure repair handoff — 2026-10-19

## Start here

User scope: repair the October 18 acquisition, contradiction and missing-assessment
failures, then validate offline. **No live provider/AI call, secret/access change,
commit, push, merge or deployment authorized or performed.**

Working branch `fix/p0-lenovo-acquisition-20261018`, base
`39a514b68388450bbc5e6061aba97bda2077fc7f`; worktree initially clean. Implementation,
tests and this handoff remain uncommitted. Review `git status --short` and both
staged/unstaged diffs before continuing. Do not discard these edits.

Read the [complete repair report](../testing/PRODUCTION_RESEARCH_FAILURE_REPAIR_2026-10-19.md)
for the root-cause table, original observations, intermediate failures, tradeoffs
and exact next production checks. [Selected proof](../testing/evidence/2026-10-19_production_research_repairs/README.md)
contains measurements and four real replay screenshots, not new live acquisition.

## Code map and decisions

- [Deep reader](../../backend/services/research/deep_reader.py): wrapper-specific
  read opportunity without fabricated publisher independence; bounded resolver
  rejection observations; challenge/empty/error classification; safe new error
  messages; body/feed byline conflict preservation. Keep the 75% title join and
  normal protected service read. Do not relax relevance/SSRF to inflate counts.
- [Reading stage](../../backend/application/research/reading.py): specialist task
  priority plus finite unattempted replacement candidates inside existing total
  attempt/time limits. Issuer chains remain separate. Expired reading opportunity
  is a failure, not a completed evidence assessment.
- [Acquisition service](../../backend/infrastructure/acquisition/service.py): source
  wait timeout latches deadline exhaustion, preventing downstream search in a
  sub-millisecond clock-rounding window. No broad timeout change or worker rewrite.
- [Planner](../../backend/services/agent_reach/planner.py) and
  [adaptive stage](../../backend/application/research/adaptive.py): preserve
  brand/personal objective rather than generic partnership follow-ups.
- [Outcome classifier](../../backend/services/research/acquisition_status.py) and
  [assembly](../../backend/application/research/assembly.py): distinguish no read
  opportunity/all failed reads from genuinely insufficient acquired evidence.
- [Contradiction detector](../../backend/services/research/contradiction_detector.py),
  [synthesis](../../backend/application/research/synthesis.py),
  [Scout assessment](../../backend/agents/scout/assessment.py): lexical denial and
  catalyst polarity cannot establish opposing factual propositions. Exact observed
  passage/source references survive as unassessed review context.
- [Report builder](../../backend/services/report_builder.py),
  [schema](../../backend/schemas/unified_report.py),
  [inspection](../../backend/schemas/evidence_inspection.py): readable change
  descriptions, conservative conflicts, preserved attribution. Builder remains
  nonmutating; [API helper](../../backend/api/agents.py) publishes failure status
  at all four response boundaries instead.
- [Trending](../../backend/agents/trending/agent.py) and
  [shared renderer](../../frontend/unified-report-renderer.js): absent risk/filing/
  timeseries evidence is UNASSESSED, not LOW/safe/reconciled/viral. Catalog matching
  is not independent identity verification. No new design or agent was introduced.
- [Browser harness](../../scripts/audits/run_phase9_four_agent_browser_audit.py):
  saved-SSE replay stubs readiness explicitly, blocks other APIs. Its PASS is not
  deployed readiness, operation health or source-reading proof.

These choices retain more inspectable leads and fewer unsupported assessments.
They deliberately do not claim that inaccessible articles became accessible or
that heuristic detection became general fact verification.

## Actual verification

| Check | Exit / result |
| --- | --- |
| `python -m pytest tests/ -q` | 0; **1,498 passed / 54.41s** |
| `python -m pytest tests/unit tests/chaos tests/security -q` | 0; **1,290 passed / 225.62s** |
| New repair + acquisition-policy tests | 0; **52 passed / 0.74s** |
| Fatal flake8 command from AGENTS | 0; no fatal findings |
| All nine Node frontend scripts | 0; passed |
| Release smoke with fresh `--output` | 0; OFFLINE_SMOKE_PASS |
| Rollback validator with fresh `--output` | 0; OFFLINE_PERSISTENCE_PASS; archive/deployed rollback NOT_VERIFIED |
| Frozen content verifier | 0; protected benchmark hashes match |
| Terminal saved-source reprocessing | 0; four cases, no fresh provider requests |
| Chromium exact-SSE replay | 0; 12 states at 320/390/1440px, all report/card/text/overflow checks pass |
| Final `git diff --check`, new-document links and screenshot SHA-256 checks | 0 / PASS; protected-path and staged diff lists empty |

Application fingerprint for final terminal/browser verification:
`df0dcf9bd27b5c7290fece6ffe9a505fa1ff36b4a24e6c9759d98e5f8052f442`.
Both runners recorded stable application bytes during the run. Four focused
390px report images were viewed. Semantic Node assertions and rendered text,
not screenshots alone, establish the missing-value label corrections.

All historical/benchmark/research/artifact/scraper protected paths have no staged
or unstaged diff. No historical dossier recovery occurred. Some intermediate
verification attempts failed or were interrupted; the report records them and
the actual fixes. Do not summarize this task as an uninterrupted green run.

New [24-case test file](../../tests/unit/test_production_research_failure_repairs.py)
is the best targeted starting point. Existing contradiction tests now expect
possible, unestablished disagreements; frontend positive fixtures explicitly
supply synthetic capture/measurement context. No frozen/golden rebaseline.

Portable validation sequence:

```powershell
python -m pytest tests/ -q
python -m pytest tests/unit tests/chaos tests/security -q
python -m flake8 backend tests scripts --count --select=E9,F63,F7,F82 --show-source --statistics
foreach ($testFile in Get-ChildItem tests/frontend/test_*.js) {
    node $testFile.FullName
    if ($LASTEXITCODE -ne 0) { throw "Frontend test failed: $($testFile.Name)" }
}
$proofRoot = Join-Path ([IO.Path]::GetTempPath()) ('aegis-repair-' + [guid]::NewGuid())
New-Item -ItemType Directory -Path $proofRoot
python scripts/validate_release_candidate_smoke.py --output (Join-Path $proofRoot 'smoke.json')
python scripts/validate_rollback_compatibility.py --output (Join-Path $proofRoot 'rollback.json')
python scripts/validation/verify_frozen_benchmarks.py
git diff --check
```

The terminal audit requires the four saved capture JSONs and an existing local
configuration file, not a new provider run. Use `--capture-from` and new output
directories; do not remove that option to make a missing capture succeed. Its
legacy `--allow-live` flag is required by parsing, but saved mode independently
blocks network. Browser replay uses `--replay-dir` pointing to those regenerated
SSE files plus local pinned Chart.js. Avoid putting existing `.env` values in
commands, logs or documents.

## Remaining work / handoff boundary

Research acceptance is **not complete**. The replay still has zero bodies for
NVIDIA/Nike/Satya, exactly because no new bytes were obtained. Microsoft's five
corporate captures are not independent financial adjudications. Failed-read
replacement is proven with controlled transports, not a successful fresh incident.

Keep the [17-defect register](../testing/AEGIS_CONSOLIDATED_DEFECT_REPORT_2026-10-19.md)
open for duplicate release findings, stopping/saturation/adaptive/funnel telemetry,
broader documentation freshness and upstream publisher success. Historical 55-file
corruption is not resolved by this worktree's isolated persistence PASS. Independent
accuracy, live/deployed parity, hosted CI for these edits and owner-controlled
staging rollback remain unverified.

Next authorized activity can be diff review and a separate request to checkpoint/
run hosted CI. A single AI-off bounded live specialist smoke is only **proposed**;
it needs explicit authorization. Do not infer permission to push/deploy from an
older release instruction or from these offline passing tests.
