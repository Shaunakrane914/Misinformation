# End-to-end intelligence checkpoint — 2026-10-18

## Scope and ownership

User requested completion across strict AI controls, four domain agents,
source-to-frontend preservation and regression/CI closeout. No live generation,
quota probes, access bypass, main merge or deployment is authorized this phase.

Worktree: isolated phase9-remediation checkout, branch
`feat/continuous-source-intelligence-20261017`, starting HEAD
`d1ffcaf7a4801b0c9f15377be0312838a65adea5`, plus preserved uncommitted
terminal-quality implementation. The original IDE checkout is different.
See [review](../testing/INTELLIGENCE_PIPELINE_COMPLETION_2026-10-18.md)
and [durable proof](../testing/evidence/2026-10-18_intelligence_completion/README.md).

## Code map and decisions

- `backend/infrastructure/llm/advisory_policy.py`: fail-closed explicit runs,
  investigation identity, transactional request reservations, shared cooldown.
  Model-list support must be separately observed; a context is not an API-body
  permission flag. Crashed in-flight reservations deliberately remain blocked.
  Configure a genuinely shared persistent ledger path for multiple processes;
  separate container filesystems cannot coordinate without shared storage.
- Gemini provider/gateway: strict model/first key/one attempt/160-token cap.
  Native verdict/report paths do not receive generation. Diagnostic scripts
  cannot generate. Evidence adviser keeps complete bounded paragraphs and uses
  copied context across its single-worker boundary; late output cannot mutate
  the investigation. Source-planner advice additionally needs discovery failure.
- `passage_records.py`, `financial_observations.py`, extraction/synthesis and
  public inspection: exact source offsets, role/context, attribution, units,
  period/page and explicit abstentions. No sentence-only negation stripping,
  table-column inference, currency conversion or independent truth assertion.
- Brand assessment/agent: background and protective notices excluded from
  threat findings; genuine complaints/allegations retain canonical references.
  Unknown lookalike ownership does not authorize takedown.
- Personal identity/catalog/planner/gate/monitoring: observed public feed and
  author-aware first-person attribution. Feed paragraph boundaries survive.
  Public statements are distinct from identity abuse; profile metadata alone
  is not substantive verification.
- Shared renderer/theme: readable report paint, expandable full context,
  financial inspection and community-uncertainty labels. Unresolved leads
  remain separate from findings, including honest zero-acquisition states.

## Regression pointers and intentional changes

New controls: `tests/unit/test_strict_advisory_policy.py`,
`test_intelligence_completion.py`, and prior cost/background/discovery tests.
Historical golden JSON is unchanged. The research golden comparator excludes
only new additive passage/financial inspection fields from its historical core
projection; exact-span tests verify those projections independently.

The historical Target-VIP golden had injected Jensen/Satya records and expected
identity threats against an unrelated target. Its reviewed expectation now
requires no subject incident, while preserving the old manifest. The synthetic
positive deepfake evaluation now explicitly names its intended subject; a
separate negative regression rejects unlinked CEO clips. The Scout adapter test
now requires unresolved factors outside findings, not a fabricated finding.

## Commands actually run

- `python -m pytest tests/ -q`: **1,402 passed**, exit 0 (42.97s).
- `python -m pytest tests/unit tests/chaos tests/security -q`:
  **1,194 passed**, exit 0 (24.57s).
- `python -m flake8 backend tests scripts --count --select=E9,F63,F7,F82 --show-source --statistics`: 0, exit 0.
- All eight `node tests/frontend/test_*.js`: exit 0.
- `python scripts/validation/verify_frozen_benchmarks.py`: exit 0.
- `python scripts/validate_release_candidate_smoke.py`: OFFLINE_SMOKE_PASS, exit 0.
- `python scripts/validate_rollback_compatibility.py`:
  OFFLINE_PERSISTENCE_PASS, exit 0, isolated archive empty. Original historical
  corruption and deployed rollback are not validated by that result.
- `git diff --check`: exit 0; credential-pattern scan of changed text paths
  found no matching credential values. This is not a complete secret-scanner audit.

Intermediate full runs failed before fixes (11, then 7 failures); their results
were not reported as acceptance. Focused regressions and final suites pass.
The initial browser counter and PDF-restoration harness mistakes are described
in the review. Repeated browser/reprocessing checks used saved captures only.

## Reproduce without spending quota

Run offline suites above. For saved capture processing, use a fresh output path:

```powershell
$proofRoot = Join-Path ([IO.Path]::GetTempPath()) ('aegis-check-' + [guid]::NewGuid())
python scripts/audits/run_terminal_agent_quality.py --allow-live --env-file .env --capture-from <saved-response-directory> --output-dir $proofRoot
```

The legacy `--allow-live` argument is still required by this runner, but
`--capture-from` blocks live network and replaces acquisition/read I/O with
recorded bytes. The default case order is the fixed twelve. For the four-case
checkpoint supply, in order, `--case scout:INFY.NS --case trending:NVIDIA
--case brandshield:Nike --case "personal_watch:Sam Altman"`.
Do not treat saved mode's cached-read telemetry as a new transport observation.
The per-case `-pipeline.json` preserves corpus, evidence, findings and API report;
temporary dossiers contain sealed snapshots. Scripts refuse output-directory
reuse. Never point output at frozen benchmarks or historical dossier storage.

Use `run_phase9_four_agent_browser_audit.py --replay-dir <saved-directory>`
with the same case list, a fresh output directory, server-side env path and the
actual pinned Chart.js asset. It exercises real buttons/SSE/renderers at
320/390/1440px. Do not enable `--allow-live-ai`.

## Outstanding boundaries

BrandShield's real sample still cannot establish counterfeit/impersonation
exposure. Tim Cook/Satya substantive depth, all-site provider access, manual
screen-reader/contrast/other-browser validation, independently adjudicated
financial truth and real trend velocity remain unverified. Do not label a
productive feed or passing HTTP response research-quality acceptance.
Protected historical data, frozen benchmarks, real env and access flags were
not changed. No background optimization job is left running.

## Publication

Development commits/push and exact-SHA hosted CI are authorized. Publication
result is appended below after the actual remote observation; no main merge
or deployment is authorized or implied.

Logical implementation commits: `2f05d59` (backend/config/offline regressions)
and `eac047f` (frontend and terminal/browser replay tools). They also preserve
the previously uncommitted terminal-quality work rather than discard it.
The final post-chat-filter proof is the `event-polish` snapshot; earlier
measurements/screenshots are retained as explicitly superseded iterations.
