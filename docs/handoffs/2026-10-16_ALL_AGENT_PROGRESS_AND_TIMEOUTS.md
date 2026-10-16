# All-agent progress and timeout remediation — 2026-10-16

## User scope and starting state

The user reported an Infosys Scout browser timeout, requested debugging, longer
waiting and exact loading progress, expanded the request to **all four agents**,
and explicitly approved **Deploy after checks**. No plan upgrade, provider
credential/approval change or historical data repair is authorized by this work.

Work started on `release/phase9-acquisition-20261015` at local documentation
commit `0a1edb60de2d65fe32f871031e26525ddd1be02b`, based on the deployed
`4b484c4` release. The worktree was clean. The original IDE worktree and the
other agent's worktree were left untouched. A later fetch found remote main
`0db6128c79aad17cb8cb95c25d3f5686580bd80a` containing the independently merged
reasoning/discovery work; integration must preserve those commits without a
force push, dataset relabeling or an unrelated architecture rewrite.

## Implementation and decisions

- [Shared browser client](../../frontend/agent-research-client.js): 90-second
  read-only startup health wait, five-minute browser analysis deadline,
  incremental SSE parsing, diagnostic analysis ID/stage/elapsed/HTTP status,
  semantic progress elements, text-only untrusted titles and no simulated ETA.
- All four agent HTML pages use this client. Duplicate local submissions are
  guarded. Automatic alias retries after ambiguous failure were removed.
  Fallback is allowed only for a missing stream route (404/405), with unknown
  legacy progress. Trending no longer disguises failure as a cached success or
  zero measured metrics; Personal Watch no longer finishes a failed progress bar.
- [Additive API routes](../../backend/api/agents.py) reuse the existing handlers,
  payload validation, synchronous response contracts and per-agent scan locks.
- [Stream transport](../../backend/api/research_stream.py) sends bounded queued
  observations, five-second heartbeats, sanitized failures and the original
  result. Server observation ends after 240 seconds; browser transport has a
  300-second ceiling. Disconnect/deadline is **not** thread cancellation. Strong
  task references retain active work; the real worker keeps its admission lock.
- [Context-local observer](../../backend/application/research/progress.py) and
  [13 existing pipeline stages](../../backend/application/research/pipeline.py)
  emit completion only after execution. No research budgets, evidence ranking,
  claim/verdict rules or serialized dossiers were changed by the progress hooks.
  Concurrent agents must not receive one another's progress. Telemetry failures
  must not change investigation behavior.
- Overall stages are exact counts, not equally weighted durations. The current
  research pass has its own 13-step counter; future passes are not predicted.
  Completing the response is not proof of truth, coverage or sufficient evidence.
- This is an ephemeral streaming response, **not** a durable resumable job
  system. Worker-process restart, lost connections and resumable result lookup
  remain limitations, explicitly described in the
  [operations runbook](../operations/AGENT_PROGRESS_AND_TIMEOUTS.md).

## Regression tests and proof

- [Backend stream tests](../../tests/unit/test_agent_progress_stream.py): all four
  routes, model validation, busy admission, error redaction, heartbeat/deadline,
  disconnect lock retention, context isolation, failed-step counting and unchanged
  reviewed research serialization.
- [Browser-client contracts](../../tests/frontend/test_agent_research_client.js):
  split UTF-8/CRLF events, terminal errors, incomplete reports, timeout, startup
  failures, rollback fallback, no ambiguous POST retries, text escaping and no
  timer-driven completion. The existing security harness now loads the client
  with a shortened test-only startup deadline instead of omitting its dependency.
- [Repeatable browser runner](../../scripts/audits/validate_agent_progress_ui.py):
  actual Chromium and local streamed HTTP, all four pages × two widths × two
  outcomes. Explicit synthetic test responses; no provider calls.
- [16-case summary](evidence/2026-10-16_agent_progress/summary.json),
  [Scout mobile waiting state](evidence/2026-10-16_agent_progress/scout-390-success-SYNTHETIC.png),
  [BrandShield desktop waiting state](evidence/2026-10-16_agent_progress/brandshield-1440-success-SYNTHETIC.png).
  Screenshots show confirmed in-progress counts before a synthetic terminal
  response, not a live investigation. Raw run output remains in a new temporary
  directory; no tracked evaluation proof was overwritten.

## Commands actually run before integrating concurrent main

This table is a reconstructed execution summary, not a raw transcript.

| Gate | Actual result |
|---|---|
| Targeted Python stream/API/research characterization | Exit 0; 55 passed in 2.80s |
| `python -m pytest tests/ -q -o "addopts=--tb=short -ra"` | Exit 0; 1,221 passed in 75.09s |
| `python -m pytest tests/unit tests/chaos tests/security -q -o "addopts=--tb=short -ra"` | Exit 0; 1,013 passed in 35.38s |
| Fatal flake8 selection from AGENTS.md | Exit 0; zero errors |
| All eight Node frontend scripts | All passed |
| Offline smoke / persistence validators | Exit 0; OFFLINE_SMOKE_PASS / OFFLINE_PERSISTENCE_PASS |
| Frozen benchmark hash validator | Exit 0; hashes verified |
| Protected tracked benchmark/dossier/research/artifact diff | Empty |
| Final Chromium HTTP-stream UI run | Exit 0; all 16 cases passed, no page exceptions or observed horizontal overflow; keyboard diagnostics passed |

Early development checks found an import path error in a new test and an older
simulated-DOM harness missing the new script. Both were corrected and rerun;
their initial failures are not represented as passing runs. Historical archive
and deployed rollback remain NOT_VERIFIED. No manual screen-reader or fresh
real-world investigation accuracy acceptance is claimed.

## Publication boundary

User authorized deployment after checks. The local results above do not certify
the concurrent remote reasoning changes. Record the normal merge, combined-tree
checks, exact hosted CI, Render release and Cloudflare publication separately
before reporting deployment complete. The preceding local Render verification
notes are included in this normal publication; their earlier local-only status
was a dated snapshot, not a restriction on this user-approved release.

## Combined release validation

Normal merge `50bc75758888326fd5ed1b0f6617fd5b03f4a60d` preserved all eight
concurrent main commits, including their new benchmark files, without conflicts
or fixture updates. A small follow-up declares the SSE response class explicitly
and tests its OpenAPI media type. On that final combined application tree:

- Full suite: **1,221 passed in 36.93s**, exit 0.
- Fast suite: **1,013 passed in 17.91s**, exit 0.
- Fatal flake8: zero errors, exit 0. All eight Node scripts also passed on the
  merged frontend (unchanged by the OpenAPI-only follow-up).
- Offline smoke and persistence: exit 0; archive and deployed rollback still
  NOT_VERIFIED. Frozen hashes passed; protected tracked outputs were unchanged.
- Additional isolated real-handler smoke used the existing test runtime before
  importing the app: each of the four actual stream routes returned HTTP 200,
  29 progress events and a terminal report. Explicit Python exit status was 0.
  No production provider request or dossier was involved. This is separate from
  the unit tests that substitute handlers and the synthetic UI transport test.
- Changed-text secret-pattern scan: zero matches. Changed Markdown local links
  had no missing targets. The existing `.env` remains ignored and untracked.

Remote CI and deployment are not inferred from these local results. The release
publication/verification closeout records their independently observed IDs.

## Hosted ordering regression and correction

Initial publication `af539bed6462838414aa9e80ad6964cc482041e7` reached main.
[Hosted run 38851807553](https://github.com/Shaunakrane914/Misinformation/actions/runs/38851807553)
passed lint/frontend, full regression and Python 3.11/3.12 fast jobs, but failed
two fast-completion progress assertions on Python 3.13 (1,011 passed, two failed).
This was not dismissed as infrastructure flakiness and frontend publication was
withheld. Render's existing on-commit auto-deploy proceeds independently of CI;
the operator setting was not changed during this task.

Cause: progress used `call_soon_threadsafe`, but terminal events went directly
into the async queue. A sufficiently fast callback could enqueue its result
before scheduled progress callbacks, ending observation before those updates.
Both terminal event types now use the **same FIFO event-loop bridge**. A new
deterministic immediate-callback test requires accepted/analysis/report progress
to precede the result, without sleeps, retries or weakened assertions.

Fresh local gates after this correction: full **1,222 passed in 49.88s**, fast
**1,014 passed in 28.78s**, all 15 stream unit cases passed, fatal lint zero,
smoke/persistence/frozen checks passed. Protected outputs remained unchanged.
These new results supersede, but do not erase, the preceding counts and failure.
Hosted verification of the correction is still required before publication is
reported complete.
