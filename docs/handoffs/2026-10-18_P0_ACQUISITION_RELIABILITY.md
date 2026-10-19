# P0 Lenovo / shared acquisition reliability — 2026-10-18

## Scope, authority and state

User requested measured acquisition starvation remediation, conservative company
resolution, explicit acquisition failure, offline-first validation and **one**
AI-disabled live Lenovo investigation. No merge/deployment before verification.
Work began clean at `8471ee349efd48644519d3a8fecde2e724ebf6ae` and is isolated on
`fix/p0-lenovo-acquisition-20261018` in the existing remediation worktree.
No main push, Cloudflare upload, Render setting change or deployment is part of
this task. Original checkout, credentials, access gates, historical dossiers,
research/artifact trees and frozen benchmark JSONL files are preserved.

**Bounded local P0 acquisition acceptance: PASS. General research accuracy and
production parity: NOT ESTABLISHED.** The new live run attempted real discovery,
preserved candidates, acquired an original PDF and rendered its source-linked
observation. This does not establish repeatability, financial adjudication,
independent corroboration or coverage of every provider/agent input.

## What the old trace does and does not prove

Previously inspected production session
`R-2026-F453764B8B19468AB26D99CB1011F8CF`: target `Lenovo (LENOVO)`, 9,706ms,
nine TIMEOUT records across news/web/RSS, no candidates/reads. One record says
`Retrieval deadline or result budget exhausted`, latency zero. The other eight
records have synthetic 8,000ms timeout latencies and near-identical generated
start/end timestamps. Those fields are **not measured provider durations**.

The old dossier did not persist resolution, quote, planning, doctor, submission,
queue or qualification timings. Exact retrospective attribution of its 9.7s is
therefore **NOT VERIFIED**; no claim is made that diagnostics consumed all of it.
A fresh read-only retrieval first timed out at 15s, then returned 404 after the
backend became reachable. Do not fabricate a recovered original or overwrite
historical records. Previously observed measurements and the user's screenshot
remain evidence, not a newly recovered raw trace. An ephemeral-storage loss is
plausible, but the cause of this disappearance was not established.

Read-only deployment attestation still observed Render deploy
`dep-dbabh79srm7s73a93jl0` at application `725f4e251e3cb4cfbd97be90cf39c27811be556b`,
with nine checked Cloudflare blobs matching that commit. This is the old deployed
code, **not this P0 branch**.

## Reproduced mechanism and changes

- Before implementation, the new four-agent calibration injected a 60ms doctor
  lookup into a 40ms discovery allowance. All four tests failed: even an immediate
  fake provider could not return a record. After implementation all pass with
  zero diagnostic refresh calls. This proves a starvation mechanism, not the
  complete historical production timing breakdown.
- A second offline control loaded the actual `725f4e2` acquisition service from
  Git, supplied nine fake queries across news/web/RSS and blocked live network.
  With a 250ms allowance and each diagnostic lookup artificially delayed 300ms,
  the old code produced nine TIMEOUTs / zero provider calls / zero records;
  the P0 code produced nine SUCCESS records / nine fake provider calls / zero
  diagnostic refreshes. Measured total control times were 5,445.758ms versus
  5.879ms. The baseline made 27 instrumented diagnostic lookups; the delay was
  intentionally applied even to repeated lookups. **This is a synthetic stress
  control, not an estimate of production cache behavior or a scraper benchmark.**
- [Doctor snapshots](../../backend/services/agent_reach/native/doctor.py) expose
  `peek_channel_status()`: copies observed/fresh cached capability metadata, or
  returns not-probed. No network, subprocess or cold-cache diagnostic refresh.
  Explicit doctor endpoints remain available separately. Runtime operation
  capability/access/cooldown assessment continues to authorize each action.
- [Shared service](../../backend/infrastructure/acquisition/service.py) removes
  diagnostic refreshes from setup, workers, timeout handling and trace assembly.
  Eight process-wide search workers and 32 admitted running/queued searches cap
  concurrency even across timed-out requests. Channel-round-robin submission
  gives unrelated providers an opportunity before repeated same-channel work.
  No retries or timeout inflation were added.
- Query records distinguish skipped, not submitted, submitted/queued, started,
  queue timeout, provider timeout and completed outcomes. They retain UTC event
  timestamps but calculate submission delay, queue wait and provider duration
  with `time.monotonic()`. A timed-out running call has a **censored observed
  duration**, not an invented completion time. Returned results are copied;
  lifecycle state is frozen at return, queued futures canceled, late results
  ignored. Running Python threads cannot be killed: underlying bounded
  transports must exit them; the shared cap prevents unlimited orphan workers.
- [Pipeline](../../backend/application/research/pipeline.py), adaptive and reading
  stages use one monotonic elapsed budget. Planning consumes the discovery slice
  rather than resetting it. Every stage records remaining total/discovery/read
  time; existing 45/40/15 allocation remains. Pure CPU/persistence work is not
  preemptively terminated by a thread kill; deadlines remain cooperative there.
- [Scout resolver](../../backend/agents/scout/financial.py) separates company from
  listing. Unknown company names and ambiguous unrecognized symbols no longer
  become uppercase quote symbols. Catalog mappings remain proposals until a
  chart response matches symbol and supplies currency. Quote fallbacks share a
  five-second allowance through the shared SSRF/byte/deadline-bounded HTTP
  transport (one attempt, no credential-bearing redirect); duplicate quote retries/social acquisition before the
  real research pass and the API's duplicate fallback are removed for this path.
- Lenovo remains a company with multiple listings. Its
  [official stock information](https://investor.lenovo.com/en/ir/stockinfo.php)
  documents HKEX HKD/RMB counters and the OTC ADR. Plain `Lenovo` selects none;
  explicit listings still require supported quote validation. Missing/ambiguous
  listings do not prevent corporate research or produce fabricated USD quotes.
  This is a bounded catalog resolver, not a universal listing search: unfamiliar
  names/symbols remain unresolved for quotes while their company research continues.
- Source planning now knows the observed
  [Lenovo issuer index](https://investor.lenovo.com/en/financial/results.php) and
  uses HKEX rather than automatically adding SEC to its filing search. This is
  a discovery endpoint, not a frozen quarterly answer; document URLs must be
  observed on fetched pages and pass existing safety/relevance/read gates.
- [Acquisition outcome](../../backend/services/research/acquisition_status.py)
  separates retrieval failure from insufficient acquired evidence. All failed,
  skipped or unsubmitted searches (or failed selected body reads without any
  acquisition) produce `ACQUISITION_FAILED` with query counts/reasons. Successful
  empty discovery can remain `INSUFFICIENT_EVIDENCE`. Dossiers, research result
  serialization, native report boundaries and the shared renderer preserve this
  distinction. Scout suppresses normal misinformation/risk conclusions on failure.
- The shared renderer adds an escaped alert before native sections and a failure
  banner in the report, retaining query-level diagnostics. It does not hide the
  report, pretend the company has no information, or replace failures with data.

## Actual one-run local measurements

Exactly one live local ASGI/SSE investigation: Scout / `Lenovo`, production-style
20s research budget, **no AI credentials or mock generation**, isolated fresh
SQLite/dossier storage, lifespan/background ingestion/notifications disabled.
Elapsed API time **17.22s**, 39 candidates / 33 accepted, four successful direct
reads plus one discovery-acquired record, five retained records / **5,485 words /
41.003 decimal KB**, 28 discovery-only leads. Ten successful query responses,
two timeouts, one auth-required response. Successful query response does not
necessarily mean useful body acquisition.

| Measured phase | Milliseconds |
| --- | ---: |
| Company resolution | 0.014 |
| Market quote | 0.000 — skipped because listing ambiguous |
| Query planning | 2.79 |
| Cached capability snapshot | 0.131, zero synchronous doctor calls |
| Discovery | 9,031.54 |
| Qualification | 7.34 |
| Ranking | 3.37 |
| Deep reading | 7,958.42 |
| Passage analysis | 38.09 |

Worker submission delays were about 1–2ms, queue waits 0.12–1,434.24ms. Completed
news/web/RSS provider durations were 437–1,565ms; one SEC auth-required result
took 287ms. The two still-running timeout observations are censored, not exact
provider completion times. Reading started with about 7.95s remaining and
processing finished with about 2.95s of total allowance remaining.

The useful PDF was discovered from the fetched issuer index:
`https://investor.lenovo.com/en/financial/results/press_2627_q1.pdf`, 1,564 retained
words. One UNVERIFIED, source-linked observation cites its canonical evidence ID
and resolves to a source record. The other four records are issuer/year index
pages, **not four independent filings**. A real finding is not an independently
verified verdict. Index/nav duplication remains a depth optimization opportunity.

Local configuration was not identical to production: it retained the existing
operator-enabled Reddit flag and exposed SEC as a bounded attempted operation,
giving 13 queries / five channels instead of the old nine / three. No approval
flag was changed, and this is not evidence of provider authorization. Reddit
returned no acquired body here; the new useful PDF came from direct web reading.
Do not attribute all improvement to doctor isolation or claim production parity.

The successful live capture preceded the final additive censored-duration flag
and failure-only summary/result serialization changes, and the bounded quote
transport/total-duration cleanup (plain Lenovo did not take the quote path). Those final contracts
were tested offline; no second live run was used to overstate exact-build live
acceptance. Frontend/source-content paths did not change afterward.

## Verification and failure history

[Durable measurements / screenshots](../testing/evidence/2026-10-18_p0_lenovo/README.md).
Fresh raw responses, logs and screenshots remain in a new system-temp directory
prefixed `aegis-p0-lenovo-`; do not copy them over old evaluation outputs.

- [P0 unit tests](../../tests/unit/test_p0_acquisition_reliability.py): 25 focused
  controls, including slow diagnostics across four agents, isolated timeout,
  queued vs started, late-return isolation, company/listing ambiguity, matching
  quote metadata, candidate-to-direct-read flow, and all-timeout pipeline/dossier
  and shared report semantics across all four agents.
- `python -m pytest tests/ -q --tb=short --show-capture=no`: **1,456 passed**,
  exit 0, 87.15s, latest application code; `full-last-clock.log` in the fresh temp directory.
- `python -m pytest tests/unit tests/chaos tests/security -q --tb=short --show-capture=no`:
  **1,248 passed**, exit 0, 59.97s; `fast-last-clock.log` in the same directory.
  The later test-only CI scheduling-margin correction passed the 71 focused
  P0/stage/golden/remediation tests (exit 0, 2.32s); hosted CI runs the full matrix.
- Fatal Python lint: zero errors; nine Node frontend scripts passed. Release
  smoke and isolated rollback returned `OFFLINE_SMOKE_PASS` and
  `OFFLINE_PERSISTENCE_PASS`. These do not repair the 55 original malformed
  dossiers or establish a deployed rollback/durable filesystem.
- Frozen hashes/protected tracked paths unchanged; whitespace checks pass.
- Exact saved Lenovo SSE replay: 320/390/1440px, one visible finding, five acquired
  cards, 28 discovery cards, no missing finding text/overflow/uncaught exception;
  source inspection opened with keyboard Enter. This is not fresh browser
  acquisition. External fonts were deliberately blocked; a static 404/resource
  console error was retained, not declared resolved.
- Labeled synthetic all-timeout replay: four actual agent pages at the same three
  widths, zero sources/findings, shared reports visible and failure warnings in
  captured text. Not live provider evidence. Screen-reader/contrast/other browser
  acceptance is unverified.
- Initial regression runs failed on old wall-clock fixture inputs and a new
  test's mock/cache isolation. Those were corrected, not hidden. Historical
  golden manifests stay unchanged: additive lifecycle/timing/status fields are
  tested separately before legacy projection. One new author-reviewed fixture
  records the intentional credential-failure summary change; it is calibration,
  not independently annotated research accuracy.
- Initial browser harness attempt failed before opening pages because its
  Chart.js asset was absent after a preceding remote-read timeout. The explicit
  pinned asset was then fetched and replay rerun in a fresh directory; no second
  provider investigation. No fabricated screenshot or raw terminal transcript.

## Reproduction and next-agent instructions

```text
python -m pytest tests/unit/test_p0_acquisition_reliability.py -q
python -m pytest tests/ -q
python -m pytest tests/unit tests/chaos tests/security -q
python -m flake8 backend tests scripts --count --select=E9,F63,F7,F82 --show-source --statistics
python scripts/validate_release_candidate_smoke.py
python scripts/validate_rollback_compatibility.py
python scripts/validation/verify_frozen_benchmarks.py
```

Offline UI controls (no network in fixture construction):

```text
python scripts/diagnostics/build_acquisition_failure_controls.py --output-dir <new-control-dir>
python scripts/audits/run_phase9_four_agent_browser_audit.py --env-file <existing-env> --output-dir <new-browser-dir> --chart-js <pinned-4.4.1-js> --case scout:Lenovo --case trending:NVIDIA --case brandshield:Nike --case "personal_watch:Satya Nadella" --replay-dir <new-control-dir>
```

The live terminal command used `SERVER_MODE=1` for the subprocess, then:

```text
python scripts/audits/run_terminal_agent_quality.py --allow-live --env-file <existing-env> --output-dir <fresh-dir> --case scout:Lenovo
```

Do not repeat it automatically: one live run was authorized and completed.
Replay its saved events for further UI work. Zero AI generation/model-list
requests were made by this task; independent upstream account accounting is not
observed. No key refresh, model rotation or provider access bypass is needed.

At this handoff snapshot, publication is intended only to the dedicated P0
branch for the explicitly requested hosted CI. Hosted results must be observed,
not predeclared; use `gh run list --branch fix/p0-lenovo-acquisition-20261018` and
inspect the exact implementation SHA. No merge/deployment is authorized by a
passing HTTP response or this report. Next review should focus on the diff and
exact-branch CI, then production parity and persistence risks before any release.

### Hosted verification follow-up

Implementation `6dc92fe8a8814b4ba46846cbb273698466bf4d9e` was committed and pushed
only to the P0 branch. [First hosted run](https://github.com/Shaunakrane914/Misinformation/actions/runs/39135745747)
failed Python suites on an old test mocking `reading.time.time` after the
production path moved to `time.monotonic`. Windows uptime accidentally made that
test expire anyway; Linux runner uptime exposed the wrong clock fixture. The
assertion that escalation cannot consume reserved reading time was preserved,
and the fixture now patches the clock actually used. No product timeout was
increased and no test was skipped. New P0 tests passed in that failed hosted run.
Subsequent CI must be observed separately; this failed run is not acceptance.

The [second hosted run](https://github.com/Shaunakrane914/Misinformation/actions/runs/39135975584)
at `6ba80f4` passed full/lint/Python 3.11/Python 3.13, but one Python 3.12 test
exceeded its synthetic 40ms allowance with ~116ms elapsed in a mocked provider
path. Scheduling/processing overhead is the likely explanation, not measured
external provider latency; no real source request occurs in that control.
The initial 60/40ms reproduction above remains the historical observation.
Current tests give the fast path a CI-tolerant 1s allowance with a simulated
doctor delay of 1.2s (never called), still guaranteeing starvation if invoked.
Event-controlled queue/isolation tests likewise use larger test-only margins.
No production timeout was raised. Two remaining adaptive query duration counters
were also made monotonic; that pass was not exercised by the single live capture.

### Final hosted result — closeout recorded 2026-10-19

The [third hosted run](https://github.com/Shaunakrane914/Misinformation/actions/runs/39136495988)
at `9a730ac1d5e6347ca4981ce9b4d3e48395d70974` completed successfully: all five
jobs passed, including Python 3.11/3.12/3.13, full offline regression, frontend
contracts and isolated release validators. See the [dated CI closeout](2026-10-19_P0_CI_CLOSEOUT.md)
for the verification ledger and remaining release limits. The fix branch was
pushed; no merge or deployment was performed.
