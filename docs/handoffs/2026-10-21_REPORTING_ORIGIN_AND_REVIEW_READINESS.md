# Resume: reporting-origin integrity and review readiness — 2026-10-21

## Scope and state

User asked to continue the latest completed Trending checkpoint. Performed a
focused offline research/report-integrity repair and prepared the missing human
review collection tool. No new live source permission was inferred from
“Continue”; previous bounded live permissions remain consumed. Zero AI calls,
new source requests, quota probes, Git writes, merge or deployment.

Actual worktree `.scratch/phase9-remediation-20261016`, branch
`fix/p0-lenovo-acquisition-20261018`, HEAD
`39a514b68388450bbc5e6061aba97bda2077fc7f`, plus preserved dirty implementation.
The outer checkout is different. No changes staged/committed/pushed by this work.
Do not stage or discard the inherited large worktree indiscriminately.

[Report and actual outcomes](../testing/REPORTING_ORIGIN_AND_REVIEW_READINESS_2026-10-21.md)
· [durable measurements/screenshots](../testing/evidence/2026-10-21_origin_integrity/README.md)
· [earlier live Trending proof](2026-10-20_TRENDING_FRESH_ACQUISITION_COMPLETION.md).

## What changed and why

- `source_independence.py::reporting_origin_groups`: pure, conservative connected
  components from valid observed publisher URLs, existing wire signals and
  duplicate titles. Headline-specific story families remain separate. Different
  headlines from one Reuters origin cannot corroborate themselves; publisher/wire
  bridges merge transitively. Known wire hosts join attributed republications.
- `proposition_grounding.py::evaluate_grounded_claim` and
  `corroboration.py::evaluate_corroboration`: ignore arbitrary incoming group IDs;
  missing/invalid URLs do not create origins or primary-authority upgrades.
  Rationale describes heuristic grouping, not authenticated independence.
- `report_builder.py::_set_retained_publisher_trust`, schema and renderer: count
  only publishers represented in final report records. Add
  `trust.observed_publisher_count`; verified-independence count/axis stay null.
  Keep upstream heuristic group count in explicitly named processing diagnostics.
  Old renderer payloads keep their labeled legacy fallback.
- `tests/unit/test_reporting_origin_integrity.py`: **21 synthetic controls**;
  inspect same-host/multiple-wire, cross-host/shared-wire, transitive bridges,
  arbitrary group strings, invalid locators, unresolved primary metadata and all
  four report boundaries. Updated older nonfrozen test expectations/locators.
- `tests/unit/fixtures/research_origin_integrity_deltas.json`: explicit four-case
  serialization correction overlay used by the golden test. Existing golden
  manifests, candidate-byte checks and all frozen datasets remain unchanged.
- `scripts/evaluation/reviewer_acceptance.py` and **38 synthetic contract tests**:
  reuse existing automatic scorer, bind human reviews to exact label/observation
  SHA-256, expose per-agent results and leave missing judgments unverified. No
  automatic research/release PASS. This is a reviewer tool, not new ground truth.
- `run_phase9_four_agent_browser_audit.py`: add focused trust screenshots/text to
  its existing saved-SSE UI audit. No new live test executed.

Judgment/tradeoff: conservative origin grouping can undercount, especially with
wire mentions or incomplete suffix/ownership information. Distinct components,
primary flags and model scores are still not authenticated independent truth.
No source/security/access limits, permissions or provider set were expanded.

## Verification and evidence boundaries

Final full **1,826 passed / 51.12s**; fast **1,618 passed / 45.54s**, exits 0.
Fatal lint, all nine frontend Node files, frozen verifier, protected tracked diff,
whitespace check and reviewer CLI help exited 0. Smoke is `OFFLINE_SMOKE_PASS`;
rollback is `OFFLINE_PERSISTENCE_PASS`, with original historical archive and
deployed rollback **NOT_VERIFIED**. That isolated pass does not recover or clear
the previously recorded 55 malformed historical dossiers.

Current API replay of genuine Samsung/Pichai captures preserved source IDs, URLs,
titles, dates and bodies/hashes. Final reports have seven sources/six publishers
and one source/one publisher respectively; verified independence remains unknown.
All cited source IDs remain available. Final Chromium saved-SSE replay has six
states at 320/390/1440px, no page exceptions/overflow/missing finding text/source
identity mismatches; source inspection opened by keyboard. Two focused final
trust screenshots were visually inspected. These are **offline** tests, not new
acquisition, accuracy, live progress timing, provider health or production parity.

Full raw logs/output use fresh system-temp basename
`aegis-origin-integrity-a0711178d84243f694f19108a3d96267`. Final logs:
`full-verified.log`, `fast-verified.log`, `scout-final/`, `personal-final/`,
`browser-final/`, `smoke-final.json`, `rollback-final.json`. Temp files may expire.
The report records earlier failures/intermediate passes rather than concealing
them. No private reasoning transcript or credentials were recorded.

Portable commands, from the actual worktree:

```text
python -m pytest tests/ -q
python -m pytest tests/unit tests/chaos tests/security -q
python -m flake8 backend tests scripts --count --select=E9,F63,F7,F82 --show-source --statistics
python scripts/validation/verify_frozen_benchmarks.py
python scripts/validate_release_candidate_smoke.py --output <new-temp-json>
python scripts/validate_rollback_compatibility.py --output <new-temp-json>
python scripts/evaluation/reviewer_acceptance.py --help
```

Run each `tests/frontend/test_*.js` with Node. Saved-source reprocessing uses
`python scripts/audits/replay_specialist_completion.py --input <genuine-saved-json>
--output-dir <new-temp-directory> --agent <agent> --subject <original-subject>`.
Use the original clock for Trending; never refresh historical source dates.
The browser runner requires explicit `--replay-dir`, genuine saved SSE, a pinned
local Chart.js asset and its credential-isolating environment setup. Never omit
replay to turn a validation command silently into a live investigation.

## Next owner/agent actions

Use [human-review instructions](../testing/RESEARCH_QUALITY_HUMAN_REVIEW_2026-10-21.md)
and the existing 48-slot packet. Independent humans must supply/freeze labels and
later review actual passages; no held-out accuracy score exists yet. Do not call
synthetic regression success research acceptance. Agree thresholds before scoring.

Preserve all historical dossiers, research/artifacts and frozen datasets. Any new
live verification needs a fresh bounded case/request authorization, no AI by
default. No push/merge/deploy authorized here. Production parity, hosted CI,
staging rollback, original archive integrity and measured trend velocity/virality
remain separate open release gates. Do not restart acquisition architecture or
rerun broad scraper sweeps merely to increase counters.
