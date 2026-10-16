# Agent startup waits, live progress and diagnostics

Applies to Scout, Trending, BrandShield and Personal Watch. The four pages use
[`agent-research-client.js`](../../frontend/agent-research-client.js); do not
restore independent 25/35-second timeouts or automatic alias retries.

## Waiting policy

- Before a research POST, retry **read-only** `/api/healthz` for up to 90 seconds.
  Individual health checks wait at most 15 seconds. This accommodates a free
  Render cold start without starting duplicate investigations. Health `ok`
  establishes application reachability, not provider health or valid evidence.
- After connection, the browser waits up to 300 seconds for analysis. The SSE
  observation window on the server is 240 seconds, leaving transport margin.
  These are ceilings, not promised durations; provider research budgets remain
  unchanged. Startup time is separate from the analysis wait.
- Progress, errors and the final result arrive over a POST SSE response. A
  heartbeat every five seconds confirms the stream is connected; it does not
  prove that a provider or worker is making progress.
- A timeout/disconnect stops observation, **not necessarily the worker**. The
  existing agent lock remains held until the actual worker finishes. Do not
  automatically resubmit. Busy agents return 429; wait before explicitly retrying.

## Truthful progress

The overall bar measures three confirmed stages: worker execution started,
agent analysis finished/report assembly underway, and final report received.
It remains indeterminate during startup. Completed-stage counts are not equal
fractions of elapsed time or an ETA. A separate bar shows actual completion of
13 shared pipeline steps, including discovery, ranking, reading, synthesis and
dossier registration. Multiple passes are numbered separately; a completed pass
does not mean the whole agent is done. Failure never increments a failed step.
No pipeline bar is claimed when an execution mode bypasses that pipeline.

An error does not turn a partial bar into 100%. Personal Watch no longer calls
`finish()` from a failure cleanup. Trending no longer converts a failed request
into zero observed metrics, claims the server is definitely offline, or silently
uses a cached report as the newly completed scan.

## Protocol and compatibility

| Agent | POST stream route | Same validated request schema as |
|---|---|---|
| Scout | `/api/scout/analyze/stream` | `/api/scout/analyze` |
| Trending | `/api/trending/scan/stream` | `/api/trending/scan` |
| BrandShield | `/api/brandshield/scan/stream` | `/api/brandshield/scan` |
| Personal Watch | `/api/personal/scan/stream` | `/api/personal/scan` |

Events are `progress`, `heartbeat`, `result`, or `error`, with JSON data and a
server-generated `analysis_id`. Result events contain the original report under
`result`; existing synchronous endpoints and report schemas remain available.
Streamed errors can follow HTTP 200, so clients must inspect the terminal event.
Streaming responses request no caching/proxy transformation; the supported
Starlette gzip middleware excludes `text/event-stream` (covered by tests).

Only an initial stream-route 404/405 enables one legacy POST fallback: that route
did not start research. Legacy progress is explicitly unknown. There is no
automatic retry after timeouts, 429, 5xx or a partially received stream.

The bounded in-memory observation queue is not a durable task store. A worker
may outlive the observer, but a process restart loses the stream and there is no
resume/reconnect-by-analysis-ID contract. Durable jobs/polling are future work.

## Debugging without secrets

Expand **Connection diagnostics** for startup attempts/status, elapsed time,
last backend event, actual pipeline stage, transport status and analysis ID.
The browser console and backend `[Analysis] id=...` logs correlate that ID with
execution start/completion/error class. Do not log request bodies, credentials,
full provider exception text or personal identifiers to add diagnostics. Render
API keys are management credentials, not application tokens; no key belongs in
these page scripts or public requests.

If startup fails, inspect connectivity/service status. If health works but
research stalls, inspect the last confirmed stage and source timeouts. A
heartbeat alone is not enough to claim a stuck worker recovered. Overall
completion is not an evidence-quality, source-coverage or verdict-accuracy PASS.

## Reproduction

```text
python -m pytest tests/unit/test_agent_progress_stream.py tests/unit/test_api_hardening_regressions.py tests/unit/test_research_pipeline_golden.py -q
node tests/frontend/test_agent_research_client.js
python scripts/audits/validate_agent_progress_ui.py --output-root <new-directory>
```

The browser runner requires optional Playwright/Chromium. It uses a local
synthetic HTTP stream, prevents external browser requests and labels its proof.
It checks all four pages at 390px/1440px in success/failure scenarios, keyboard
diagnostics and real streamed increments. Final report rendering, live provider
quality, actual cold-start duration and manual screen-reader acceptance are
separate checks. See the [dated handoff](../handoffs/2026-10-16_ALL_AGENT_PROGRESS_AND_TIMEOUTS.md).
