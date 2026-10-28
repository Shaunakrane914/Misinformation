# Acquisition growth implementation review — 2026-10-25

Latest repair cycle: [publisher allocation and speaker attribution results](READ_ALLOCATION_RESULTS_2026-10-26.md).
Battery recycling now has live fresh-article proof; semiconductor and current Personal Watch coverage remain incomplete.

Follow-up: [review repairs and bounded pilot](PIPELINE_REVIEW_REPAIRS_AND_BOUNDED_PILOT_2026-10-25.md)
records implementation corrections, new tests, four live observations and the remaining research-quality
limitations. This earlier review is preserved as the defect baseline.

**Engineering progress confirmed; experimental yield acceptance not met.** This is a review of the
user's new implementation, not a repair, fresh live pilot or deployment. Application code and existing
uncommitted changes were preserved.

Reviewed checkout: `.scratch/phase9-remediation-20261016`, branch
`release/specialist-task-20261024`, HEAD `7ad13a5`, plus the local changes. The attached continuation
transcript ends during the measured-yield experiment. Its earlier completed predicate/provenance
handoff is [here](../handoffs/2026-10-25_TRENDING_PREDICATE_AND_GDELT_PROVENANCE.md).

## Confirmed progress

- GDELT first-seen time is retained as `gdelt_seen_at`, with explicit observation provenance. It is
  not promoted to publisher publication time. Catalog forwarding and strict temporal controls are tested.
- The finite-predicate heuristic admits more ordinary source prose and preserves recorded source bytes,
  citation identities and exact offsets. The genuine ECS battery-recycling fixture passes offline;
  this is not a new live acquisition or an independent accuracy evaluation.
- `pipelined_v1` is opt-in. It interleaves bounded discovery and reading, reuses the existing budgeted
  transport, ranks article-shaped leads and uses a recoverable publisher-yield penalty. The default
  controller remains `legacy`. Shared safety and final qualification gates remain in place.
- New baseline/replay tooling separates original captures, requalification and manually supplied
  review labels. Resource sampling measures this local process and explicitly labels Render projections.

The proposed new authoritative-source integrations are not completed by this diff. The transcript's
CPSC/FTC documentation research is not evidence that new adapters have acquired useful content.

## Findings, in repair order

### P1 — Running readers can mutate returned candidates after cancellation

[`PipelinedAcquisition._dispatch_reads`](../../backend/services/research/pipelined_acquisition.py)
passes the live `EvidenceItem` from `known` into an outer worker. `DeepReader.deep_read` changes that
object's status, content, acquired identity and metadata. `run` shuts its executor down with
`wait=False`; cancellation does not stop workers already running. Discarding their returned tuple
therefore does not prevent mutation through the shared object reference.

Reproduced offline with the real reader and the synthetic `FakeWorld` from
[`test_pipelined_acquisition.py`](../../tests/unit/test_pipelined_acquisition.py): block the
`deep_reader._challenge_body` call only on a `pipeline-read` processing thread using a `threading.Event`,
run with a 0.6-second parent deadline, snapshot returned candidate content/identity, then release the
event. Two returned candidates changed from empty/unacquired to populated/acquired after return.
The returned capture list stayed empty. No source or model request was made.

Use private worker copies and merge an eligible completed result only in the coordinator before
closure. Add assertions over returned candidate fields and hashes after a delayed worker finishes;
the existing cancellation test only checks capture-list length and misses this defect.

### P2 — Interrupted read attempts disappear from primary telemetry

In the same reproduction, `acquisition_controller.reads_started` was **2**, but
`read_telemetry.attempted` was **0**, with no returned acquisition-attempt records. Those counters are
merged only by `_complete_read`. A parent deadline can close the controller before that merge.

Reserve a stable attempt identity at dispatch. Finalize every dispatched attempt exactly once as
completed, cancelled-before-start, or interrupted/unknown-after-start, preserving the distinction
between submission and actual provider execution. Do not infer a failed HTTP response from cancellation.

### P2 — Replay admission accounting omits failed searches and is mislabeled as measured

[`ReplayService.retrieve_many`](../../scripts/audits/acquisition_replay.py) calls `_charge` only in
the branch that can succeed. A recorded provider timeout/failure consumes no simulated admissions.
An offline synthetic record with status `TIMEOUT` reproduced **0 admissions charged**. Some failures
can occur before HTTP admission, but provider failure alone does not establish that; the replay needs
recorded transport admission detail or an explicit unknown/estimated cost.

Replay cost constants are fitted estimates, yet the output places the resulting counts under
`MEASURED.http_admissions`; the shared Markdown legend describes these as original-run measurements.
Keep measured original HTTP counts separate from modeled replay charges and label derived efficiency
accordingly. Preserve uncertainty for failures whose admission count was not recorded.

### P2 — The experimental scheduler does not execute the AI suggestion hook

[`HarvestingEngine.run`](../../backend/services/research/harvesting.py) excludes `pipeline is not None`
from its legacy advice block. `PipelinedAcquisition` has no equivalent `expand_with_advice` call.
Consequently, enabling advisory environment flags alone cannot enable suggestions in `pipelined_v1`.

The original workspace's inspected `.env` also had the three advisory-enable switches unset. Only
nonsecret flags were inspected; no credentials were printed or changed. The existing runtime advisory
helper and strict budget are present in HEAD, but that is not proof of active inference.

Wire one optional budgeted suggestion into weak-capture feedback with remaining read opportunity,
then test the hook with mocks. Any separately authorized real verification must retain the existing
shared call ledger, model/output limits and no-retry behavior. This review made **zero Gemini calls**.

### P2 — Resource sampling needs an explicit dependency or unavailable state

[`ResourceSampler.__init__`](../../scripts/audits/resource_sampler.py) imports `psutil` unconditionally,
and the terminal runner now instantiates it for every case. This checkout has psutil installed, but
the project's dependency files do not declare it directly. A clean installation may fail before its
investigation starts. Declare an audit dependency or report resource measurements as unavailable while
allowing the investigation to run. Do not substitute a fabricated memory measurement.

## What the saved scheduler comparison actually shows

Inspected the existing `replay_matrix2.json` from the attached session's scratchpad: **72 offline
runs**, six configurations over the same 12 saved investigations, `inputs_unchanged=true`.
This review aggregated that saved output; it did not rerun the 72-case matrix. The scratchpad path
is temporary and may expire. A [compact aggregate and verification record](evidence/2026-10-25_growth_progress_review/measurements.json)
is preserved with this report.

| Same replay world | Qualified records | Selected passage words | Modeled admissions | Words / modeled admission |
| --- | ---: | ---: | ---: | ---: |
| Legacy | 51 | 2,899 | 572 | 5.07 |
| Pipelined, two read workers | 49 | 2,774 | 518 | 5.36 |

This is about **5.7% higher modeled word efficiency**, **4.3% fewer selected words** and two fewer
qualified records. It is not a demonstrated 2× gain, a live request saving or 20× useful evidence.
Admission-model defects above further limit the efficiency interpretation. Unobserved read outcomes
remain failures/unknowns in this reconstructed world; replay cannot establish recall for new URLs.

| Agent, three saved cases each | Legacy qualified / selected words | Pipelined qualified / selected words |
| --- | ---: | ---: |
| Scout | 25 / 1,346 | 24 / 1,277 |
| BrandShield | 23 / 1,327 | 23 / 1,327 |
| Trending | 2 / 112 | 1 / 56 |
| Personal Watch | 1 / 114 | 1 / 114 |

The new scheduler has not solved Trending's fresh-source supply or Personal Watch's substantive
coverage. Publisher groups are observed domain groups, not verified independent ownership. Qualified
text is not an adjudicated claim. Compare the same selected-passage definition on both sides; do not
compare this table with all-workbench/raw word totals as a growth ratio.

## Verification performed in this review

| Command | Actual result |
| --- | --- |
| `python -m pytest tests/ -q` | Exit 0; **2,540 passed / 69.62s** |
| `python -m pytest tests/unit tests/chaos tests/security -q` | Exit 0; **2,332 passed / 52.55s** |
| `python -m flake8 backend tests scripts --count --select=E9,F63,F7,F82 --show-source --statistics` | Exit 0; zero findings |
| All ten `node tests/frontend/test_*.js` scripts, individually | Exit 0 each |
| `python scripts/validate_release_candidate_smoke.py --output <fresh-temp-json>` | Exit 0; offline smoke only |
| `python scripts/validate_rollback_compatibility.py --output <fresh-temp-json>` | Exit 0; isolated offline persistence only |
| `python scripts/validation/verify_frozen_benchmarks.py` | Exit 0; protected benchmark hashes verified |
| `git diff --check` | Exit 0 |
| Slow-processing cancellation diagnostic | Exit 0; reproduced late candidate mutation and missing attempt counts |
| Recorded-timeout replay diagnostic | Exit 0; reproduced zero modeled admission charge |

The first draft of the timeout diagnostic failed because its synthetic world lacked `channels`;
the corrected diagnostic supplied that field and produced the observation above. Test execution did
not write protected historical dossiers or frozen benchmark records. The original malformed archive
was not recovered or validated by these isolated persistence checks. Node contracts are not rendered
browser or screen-reader acceptance. No new browser run, network acquisition, model call, hosted CI,
commit, push, merge or deployment was performed.

Detailed command logs are in system-temp basename `aegis-progress-review-at0j6ui_`; the full-suite count
was observed directly in the tool result, not saved as a raw transcript in that directory.

## Recommended continuation

First repair worker isolation/attempt lifecycle and replay provenance. Wire advisory suggestions
without allowing ordinary tests to consume AI quota. Then use the corrected, identical measurement
definitions to assess the scheduler. Prioritize demonstrably fresh Trending leads and attributed
Personal Watch statements over more concurrency. The bounded four-case pilot described in the user's
attached experiment remains a separate execution step; it was not run in this review. Keep the
controller opt-in until the safety and useful-yield gates pass.
