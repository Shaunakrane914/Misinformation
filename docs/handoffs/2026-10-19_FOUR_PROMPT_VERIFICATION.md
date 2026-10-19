# Four-prompt verification — 2026-10-19

## Decision

**Research-quality acceptance: FAIL. Bounded saved-response rendering: PASS.**
One real local investigation per agent exposed remaining source-selection,
direct-reading and queue-start failures. The earlier Lenovo result does not
establish shared reliability across a sequence of investigations. No application
code was changed during this verification; no merge, push or deployment occurred.

Checkout: `fix/p0-lenovo-acquisition-20261018`, clean application checkpoint
`264a1c27857bf4cb36d516420dd6edf5ccc00adf`.
The application fingerprint stayed
`6d1c53aa9bccb41fdca1c0932d8275114d72c2972088b5078674b075f501e0d7`
through terminal acquisition and browser replay. New audit documentation is
uncommitted and is not part of that application fingerprint.

## Method and boundaries

The user's request for four prompts was interpreted as one distinct entity
prompt for each agent: Infosys, NVIDIA, Nike and Tim Cook. These are calibration
observations, not unseen adjudicated true/false claims or independent accuracy
labels. Requests were sequential in one local backend process, without audit
POST retries or changing normal application provider/fallback budgets. Shared
worker pressure can therefore carry between cases, as in a long-lived backend.

The terminal runner used normal ASGI SSE routes, fresh temporary SQLite/dossiers,
no background ingestion, remote persistence or notifications. AI credentials
were excluded, mock generation was false, and there were **zero requested live
AI generation/model-list calls**. Existing local acquisition settings were
retained; no credentials or approval flags were changed. Local configuration
does not prove provider authorization or deployed configuration parity.

## Actual local results

Words are whitespace tokens in one retained native `content`/`snippet` per
record; KB is UTF-8 bytes / 1,000, excluding metadata and discovery-only text.
Neither metric establishes useful evidence or independent corroboration.
Successful reads count acquired direct bodies, not HTTP status alone.

| Agent / input | Seconds | Candidates | Reads attempted / successful | Records | Words | KB | Shared findings | Result |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| Scout / Infosys | 17.46 | 38 | 6 / 4 | 5 | 1,168 | 7.403 | 0 | Acquisition completed; research inadequate |
| Trending / NVIDIA | 15.24 | 26 | 4 / 1 | 1 | 806 | 5.141 | 1 | One unverified publisher observation |
| BrandShield / Nike | 14.37 | 22 | 6 / 0 | 0 | 0 | 0 | 0 | `ACQUISITION_FAILED` |
| Personal Watch / Tim Cook | 14.91 | 5 | 1 / 0 | 0 | 0 | 0 | 0 | `ACQUISITION_FAILED` |

Six retained records / 1,974 words overall is not six relevant investigations
or independently corroborated reports. All four HTTP responses were 200, each
had one result event, 29 progress events and no SSE error events; that is only
transport completion. Reports use `COMPLETED` for acquired records, not a claim
that research quality passed.

| Input | Successful queries | Provider timeouts | Queued without starting | Reading seconds available at entry | Synchronous doctor calls |
| --- | ---: | ---: | ---: | ---: | ---: |
| Infosys | 10 | 2 | 0 | 7.570 | 0 |
| NVIDIA | 8 | 6 | 1 | 7.836 | 0 |
| Nike | 6 | 3 | 0 | 7.893 | 0 |
| Tim Cook | 1 | 1 | 8 | 7.967 | 0 |

Actual queue/provider fields, not legacy fixed timeout latency fields, are the
basis for lifecycle interpretation. Every investigation exhausted discovery's
slice and stopped adaptive expansion, but reading still received a reservation.
Removing synchronous doctor calls did not eliminate all acquisition failures.

## Findings and remaining work

### P1: cross-request queue pressure remains

Tim Cook submitted ten queries; only two started. The first news query started
in 0.269ms and returned five discovery records in 3,046ms. A web query waited
3,046.842ms before starting and timed out with a censored 5,974.143ms provider
duration. Eight others reached `QUEUE_TIMEOUT` after about 9,021ms, with
`provider_started=false`. The sole accepted candidate's Google News wrapper
then failed its 5s direct-read attempt.

This confirms queue starvation, not its complete root cause. Earlier requests'
still-running provider threads occupying the shared pool are a plausible cause;
this audit did not capture thread stacks or per-provider outstanding-task counts
and must not present that hypothesis as measured proof. Next isolate it offline
with sequential slow-provider controls, pool occupancy and provider-level
admission/cancellation telemetry before more network testing. Do not remove
concurrency limits, bypass access gates or enlarge every timeout.

### P1: discovery selection does not consistently reach substantive bodies

Infosys retained four investor/results index pages and an irrelevant careers
page. The careers page is surfaced under PRIMARY evidence and marked
`PRIMARY_DOCUMENT`; that label does not make it useful financial evidence.
Two observed financial PDF reads failed. No financial claim was resolved and
zero findings were returned. Prefer observed substantive filing links while
keeping index leads inspectable; do not promote them into financial conclusions.

Nike's six failed read selections included Wikipedia, corporate/storefront
pages and Google News wrappers. Wikipedia exceeded the existing 1MB response
limit; the other five attempts recorded 5s timeouts. No threat body was acquired.
Normal storefront/Wikipedia selection does not demonstrate counterfeit or
impersonation investigation. Fix relevance/usefulness ranking and wrapper
resolution without silently weakening response-size/SSRF protections.

### P2: one publisher observation is not trend measurement

NVIDIA retained an 806-word publisher article at
`https://blogs.nvidia.com/blog/local-ai-rtx-spark-windows-laptops-celebration/`.
The single finding's sentence occurs verbatim in that retained body; its
canonical citation `ev_02bfb85bef74` resolves to the returned source record.
It is correctly marked `UNVERIFIED` and `observation_only`, with entailment
verification false. No independent corroboration or measured virality follows.
Captured author metadata says Gerardo Delgado while the extracted article body
names Shreevar Rastogi; reconcile feed versus body provenance rather than
treating either author field as independently verified identity.

## Frontend verification

Exact saved SSE responses were replayed through real page buttons and unmodified
renderers in Chromium at 320, 390 and 1440px. This is **not a second acquisition
or deployed-site test**. All 12 states showed matching finding/acquired/discovery
counts, visible shared reports, no missing finding text, no horizontal overflow
and no uncaught page exceptions. Source inspection opened with keyboard Enter
in all six source-bearing states. Both failed agents prominently displayed
`ACQUISITION FAILED` and explained that failure does not mean no information
exists, at every tested width.

One 390px report screenshot per agent was visually inspected. External fonts
were intentionally blocked; six console resource errors were retained (four
blocked-font failures and two 404s). The 404 paths were not individually mapped
by the response observer. This is not a clean-console claim, manual screen-reader
acceptance, contrast audit or all-browser certification. See the
[durable evidence index](../testing/evidence/2026-10-19_four_prompt_verification/README.md).

## Reproduction and preservation

Executed commands below are summaries, not invented raw transcripts. Set
`SERVER_MODE=1` only for these subprocesses. All `<...>` paths must be selected
locally; never paste credential values into a command or report.

```text
python scripts/audits/run_terminal_agent_quality.py --allow-live --env-file <existing-env> --output-dir <fresh-terminal-dir> --case scout:Infosys --case trending:NVIDIA --case brandshield:Nike --case "personal_watch:Tim Cook"
python scripts/audits/run_phase9_four_agent_browser_audit.py --env-file <existing-env> --output-dir <fresh-browser-dir> --chart-js <pinned-chart-4.4.1-js> --replay-dir <terminal-dir> --case scout:Infosys --case trending:NVIDIA --case brandshield:Nike --case "personal_watch:Tim Cook"
```

Both runners exited 0, meaning their transport/rendering invariants passed, not
that research acceptance passed. Full raw captures, source bodies, logs, temporary
databases and screenshots remain in system-temp directory
`aegis-four-prompt-01bfed99-de4b-40af-a178-bbabfcc00001`.
Only selected sanitized measurements and report screenshots are
copied into this new evidence directory. Historical dossiers, frozen benchmarks
and existing artifact proof were not overwritten. No application implementation
was changed. No new hosted CI or production verification is claimed for this
audit.

## Offline regression results for this verification

Executed after the four live cases; AI credentials/network are isolated by the
test harness. These green checks do not override the live acquisition failures.

```text
python -m pytest tests/ -q --tb=short --show-capture=no
python -m pytest tests/unit tests/chaos tests/security -q --tb=short --show-capture=no
python -m flake8 backend tests scripts --count --select=E9,F63,F7,F82 --show-source --statistics
python scripts/validation/verify_frozen_benchmarks.py
```

Full: 1,456 passed in 76.65s, exit 0. Fast: 1,248 passed in 45.27s,
exit 0. Fatal lint: zero errors, exit 0. Frozen hashes verified, exit 0.
Additional executed commands:

```text
python scripts/validate_release_candidate_smoke.py
python scripts/validate_rollback_compatibility.py
node tests/frontend/test_*.js
```

The final line is notation for running each of the nine matched files separately,
not a portable shell wildcard invocation. All nine exited 0. Smoke returned
`OFFLINE_SMOKE_PASS`, exit 0; rollback reader returned `OFFLINE_PERSISTENCE_PASS`,
exit 0. Historical archive inspection and deployed rollback remain NOT VERIFIED
in this isolated worktree. Relative evidence links and JSON syntax were checked;
`git diff --check` passed and protected tracked paths had no diff. Only this new
audit documentation/evidence and its handoff-index entry remain uncommitted.
No new hosted CI is claimed.
