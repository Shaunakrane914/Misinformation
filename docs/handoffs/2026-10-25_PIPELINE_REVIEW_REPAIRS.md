# Pipeline review repairs — 2026-10-25

User approved repairing the [progress-review findings](2026-10-25_ACQUISITION_GROWTH_PROGRESS_REVIEW.md)
and the bounded pilot. Branch `release/specialist-task-20261024`, base `7ad13a5` plus preserved local
implementation. **Uncommitted; no push, merge or deployment.**

[Full implementation, pilot and limitations report](../testing/PIPELINE_REVIEW_REPAIRS_AND_BOUNDED_PILOT_2026-10-25.md)
and [durable compact measurements](../testing/evidence/2026-10-25_pipeline_review_repairs/measurements.json).

## Changes and decisions

- Private worker copies and coordinator-only merges eliminate late mutation. Stable reserved attempt
  IDs retain queued cancellation and interrupted/unknown-provider states without inventing HTTP failures.
  Concurrent discovery aliases survive the merge. See `PipelinedAcquisition` and `DeepReader.deep_read`.
- Existing strict AI search advice is wired into the experimental controller with query/read capacity
  retained. Local nonsecret enable flags were set, exact `gemini-3.5-flash-lite`; credentials and shared
  policy ledger unchanged. Production/current running processes were not altered. No live generation
  verification or model-capability probe was made. Ordinary tests and the comparison consumed zero AI.
- Replay failure costs and efficiencies are explicitly modeled, not original measured HTTP counts.
  Resource sampling is optional and honestly unavailable without psutil.
- The live Trending failure exposed premature futility, root-slug demotion and empty link labels.
  Follow-up corrections preserve untested article opportunities and observed later headline labels.
  These changes have offline proof only; do not attribute them to the earlier live application bytes.

Regression pointers: [scheduler controls](../../tests/unit/test_pipelined_acquisition.py),
[audit provenance](../../tests/unit/test_acquisition_audit_provenance.py),
[observed anchors](../../tests/unit/test_web_page_extraction.py). Existing strict advisory, access,
SSRF, recovered routes, source hashing, temporal qualification and frozen-data protections remain.

## Actual validation

| Command | Result |
| --- | --- |
| Focused closeout scheduler/audit/page suites | Exit 0; 37 passed /11.23s |
| `python -m pytest tests/ -q` | Exit 0; **2,556 passed /54.95s** |
| `python -m pytest tests/unit tests/chaos tests/security -q` | Exit 0; **2,348 passed /45.85s** |
| Fatal flake8 (`E9,F63,F7,F82`) | Exit 0; zero findings |
| Ten Node `tests/frontend/test_*.js` scripts | Exit 0 each |
| Release smoke / isolated persistence validators, fresh temporary outputs | Exit 0; OFFLINE_SMOKE_PASS / OFFLINE_PERSISTENCE_PASS |
| Frozen verifier / protected-tree diff | Exit 0; benchmark hashes match; no protected tracked changes |
| Twelve-original-response baseline and four-new-response measurements | Exit 0; inputs unchanged |
| Eight-run offline legacy/pipeline replay, before later selection follow-up | Exit 0; modeled costs separate; not a live benchmark |
| Supplemented genuine saved-body Trending control | Exit 0; 1 qualified /100 selected words; explicitly offline combined-source replay |
| Four-case native pilot | Exit 0; 301 HTTP admissions; 0 AI reservations; stable application fingerprint |
| Exact saved-report Chromium replay | Exit 0; 12 states, four focused screenshots inspected |

The raw archive/deployed previous-version rollback are **NOT_VERIFIED**; the isolated persistence
validator does not establish historical recovery. No new hosted CI. Intermediate tests/path/glob
instrumentation failures are disclosed in the report; no provider retry was used to hide them.
Detailed logs/native responses/SSE and earlier passing test runs remain under the fresh system-temp
basename `aegis-pipeline-repair-8uv6z1ek`; durable selected evidence is linked above.

## Actual quality outcome and next owner

Live qualified records / frontend workbench words: Scout **15 /6,963**, BrandShield **5 /1,629**,
Trending **0 /0**, Personal Watch **1 /114 historical**. All 150 displayed passages join to exact
captured source spans and hashes. No frontend display-budget omissions. Counts are not truth,
independence, current-threat confirmation or release acceptance; **2×/20× not demonstrated**.

The new live Trending run observed the ECS URL but stopped before reading it. Later offline replay
combines that observed URL with an earlier genuine saved body and verifies the corrected path. The
four approved live cases are consumed; no fifth investigation or generation call occurred.

Next: separately bounded live verification of the post-pilot selection fixes, better attributed
Personal Watch source supply and independent passage/claim review. Keep `pipelined_v1` opt-in;
do not increase concurrency or weaken date/access gates to meet a word target. Preserve all existing
user changes, historical dossiers, research/artifacts and frozen benchmarks. Portable commands are in
the linked report; no private reasoning transcript or credentials were written.
