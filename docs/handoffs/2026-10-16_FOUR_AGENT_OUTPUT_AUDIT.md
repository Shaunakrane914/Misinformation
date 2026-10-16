# Four-agent output audit handoff — 2026-10-16

## Outcome and scope

User requested three distinct inputs per agent, local agent execution followed
by actual frontend checks and a clear report. Completed two full real matrices:
12 direct API investigations, then 12 new Chromium-button/local-SSE
investigations. Also replayed the first 12 exact responses at two widths to
isolate display loss. **Research quality FAIL; frontend acceptance PARTIAL.**

- [Report, both 12-input tables and prioritized code owners](../testing/FOUR_AGENT_OUTPUT_AUDIT_2026-10-16.md).
- [Durable screenshot index](../testing/evidence/2026-10-16_agent_output_audit/README.md).
- [Sanitized machine measurements and request bodies](../testing/evidence/2026-10-16_agent_output_audit/measurements.json).

Branch `release/phase9-acquisition-20261015`, HEAD
`ff6d246bfe1e9cfd0f21d8e32135582e631636f1`, plus existing uncommitted Slice A
changes. Original IDE worktree remains separate and older. This task changes
documentation/evidence only, not application source, settings or credentials.
No commit, push, remote CI, merge or deployment was performed.

## Findings and continuation

1. BrandShield interprets Tata's own job-scam warning as a high-severity scam
   vector with hard-coded 0.78 confidence. Fix contextual interpretation and
   ownership; do not indiscriminately expand a domain allowlist.
2. Navigation/headline/profile metadata becomes SUPPORTED/KNOWN_FACT findings;
   Scout can report NOMINAL/LOW from a weak homepage. Stronger epistemic gates
   are needed even if Gemini later becomes available.
3. BrandShield/Personal normalization regenerates IDs without rewriting finding
   references. Preserve canonical identities/aliases and test actual joins.
4. BrandShield's zero-source early return hides shared findings and telemetry.
   Exact Nike response replay reproduces this at both widths. The second live
   Nike run acquired a record, so its successful rendering does not fix the bug.
5. Acquisition remains shallow; all first-pass funnels halted adaptive discovery
   at its time ceiling, with no primary source reported. Browser waits are not
   internal research budgets. Inspect actual candidate/read failures first.
6. Non-Scout agents do not export the same bounded discovery corpus. Findings
   citing undisplayed leads cannot be inspected; do not promote leads to bodies.
7. SKIPPED query records count as submitted in shared telemetry but not in the
   native funnel. Unify lifecycle definitions.
8. Shared findings lack the existing list inset; menu text and literal Markdown
   dominate the result. A count brief is not strategic intelligence.

The report links exact owners and proposed regression criteria. Findings above
are observed defects, not claims that every empty source could have produced
relevant data. Do not weaken evidence gates to increase numbers.

## Configuration and safety boundaries

`GEMINI_API_KEY` is present/nonempty, but its current value did not pass the
provider's configured prefix check. Live Gemini was unavailable in both complete
passes; mocks were explicitly false. Upstream credential validity was not
tested. Do not print it, bypass the gate or claim full LLM synthesis. A securely
configured provider-accepted key followed by actual successful inference is an
owner follow-up, not an excuse to ignore the deterministic bugs above.

Both backend processes used fresh temporary SQLite/dossier directories,
disabled Supabase/notification credentials, no phone numbers and lifespan off
to prevent background ingestion. Acquisition itself was real. Existing
operator-enabled local Reddit flag remained true; no provider approval or
production configuration change is established. Protected archives/datasets
were not restored, repaired or overwritten.

## Actual command/result record

Reconstructed command record, **not a raw transcript**. From the tested checkout,
`<audit-temp>` was a fresh OS-temp directory named
`aegis-twelve-live-264fa77672124089b572006bf1aceb37`.

| Command/check | Exit / result |
|---|---|
| `python <audit-temp>/live.py` | 0; 12/12 real local POSTs HTTP 200; six zero-record cases; six records total |
| `python <audit-temp>/browser.py` | 0; exact-response replay, 24 states; Nike's shared report hidden in two states; zero overflow/uncaught exceptions |
| First `python <audit-temp>/ui_live.py` | Stopped audit process after capture-tool errors; seven streams started, six completed in backend logs, one interrupted; excluded from acceptance counts |
| Corrected `python <audit-temp>/ui_live.py` | 0; 12/12 real button/SSE result events, 29 progress events each, 24 matching DOM states, no overflow/uncaught page exceptions |
| `python <audit-temp>/analyze.py` and same with UI-output directory argument | 0 each; body text measured separately from JSON/discovery projections |
| `python <audit-temp>/stable_capture.py` | 0; exact Tim Cook payload, four repeated viewport captures; natural paint/font waits, no CSS replacement/provider acquisition |
| `python scripts/validation/verify_frozen_benchmarks.py` | 0; frozen hashes verified |
| `git diff --check` / protected tracked-path diff | 0 / empty at audit checkpoint; rechecked after documentation |

The first browser harness used Chrome's response-body API, which did not expose
the fetch-consumed SSE body. Corrected observation used a cloned browser
Response while returning the original to application code. This was an
instrumentation failure, not an agent/backend failure. Its extra seven starts
are disclosed separately, not silently treated as part of the two complete
12-input matrices.

One Tim Cook desktop capture was blank despite populated DOM; stable exact-
payload replay displayed content twice at desktop. This does not prove a
persistent application defect or universal visual acceptance. 18 console
resource errors were recorded in the completed live browser matrix; blocked
external resources/static 404s were not individually mapped to URLs.

The offline full/fast suites, lint, smoke and rollback were **not rerun for this
documentation-only audit**. Their prior 1,243/1,035 counts belong to the
[implementation checkpoint](2026-10-16_REPORT_PRESERVATION_IMPLEMENTATION.md),
not this live audit. No axe, contrast measurement, screen reader, cross-browser,
all-operation sweep or production acceptance is claimed.

## Reproduction guidance

The temporary one-off runners are not a maintained test suite and may expire.
Durable JSON preserves all 12 inputs and actual endpoint/request bodies. Use
the same matrix, do not substitute easier passing cases. Before live reruns:

1. Verify the intended worktree and preserve its dirty diff.
2. Construct an isolated subprocess environment before importing backend code;
   set `SQLITE_DB_PATH`, `AEGIS_SQLITE_PATH`, `AEGIS_DOSSIER_DIR` to new temp
   locations, explicitly disable mock LLM, blank remote-write/notification
   credentials, supply no phone number, and prevent `.env` from reintroducing
   excluded values. Assert effective settings before any request.
3. Serve `backend.main:app` on loopback with lifespan off; use normal handlers,
   existing source permissions and bounded retrieval. No audit POST retries.
4. For browser runs, serve the actual frontend and point only its API resolver
   at that local backend. Fill actual fields/click actual buttons. Capture SSE
   progress/result/error events without replacing agent or renderer functions.
5. Save each response once and inspect both 390/1440px renderings. Normalize
   whitespace for text checks; verify screenshots after natural paint/layout,
   not only DOM counts. Separate fixture replay from new acquisition.
6. Preserve failures, per-source depth, canonical IDs and useful-text counts;
   avoid summing repeated snapshots into unique evidence totals. Save outputs
   to new locations, never tracked evaluation files or old dossiers.
