# Four-agent local output audit — 2026-10-16

## Decision

**Research-quality acceptance: FAIL. Rendering acceptance: PARTIAL.**
Successful HTTP responses do not establish successful research. The fixed
12-input API pass returned six native source records in total; three were
corporate homepages and three were short X profile descriptions. Six inputs
returned no acquired records. No primary sources were reported in that pass.
The frontend also has a reproducible zero-source branch that hides findings.

This is an audit, not a remediation or deployment. Existing uncommitted Slice A
changes were preserved. No application source was changed during this audit.

## Scope and method

- Checkout: `release/phase9-acquisition-20261015`, HEAD
  `ff6d246bfe1e9cfd0f21d8e32135582e631636f1`, **plus uncommitted changes** described
  in the [preservation handoff](../handoffs/2026-10-16_REPORT_PRESERVATION_IMPLEMENTATION.md).
  The original IDE checkout is a different worktree. This does not test the
  deployed site or prove that either remote contains these changes.
- Pass A: three fixed inputs for each of four agents; one real local HTTP POST
  per input through `backend.main:app`, normal acquisition and report assembly.
  Requests were sequential, without audit-level POST retries.
- Pass B: exact Pass A responses replayed through actual agent-page buttons,
  the stream client and unmodified native/shared renderers at 390 and 1440px.
  Result-only SSE transport and health responses were harness stubs. This
  isolates API-to-display loss without requesting the providers again.
- Pass C: the same 12 inputs submitted again through real Chromium buttons,
  the real local streaming endpoints and real acquisition. Screenshots at both
  widths share each input's single completed result. Trending categories were
  explicitly Technology for OpenAI/NVIDIA and Business for electric vehicles;
  Pass A left the optional category unspecified. These are separate real
  observations, not identical-request deterministic comparisons.
- Local servers used newly created temporary SQLite databases and dossier
  directories. Supabase and notification credentials were blanked, no phone
  numbers supplied, background ingestion disabled with Uvicorn lifespan off.
  Existing scraper bounds, access gates and fallback behavior were not changed.
- The previously operator-enabled local Reddit flag was retained; it is not
  evidence of provider authorization or a production configuration change.
- **LLM limitation:** `GEMINI_API_KEY` exists and is nonempty in the original
  workspace `.env`, but the saved value did not pass the current provider's
  `AIzaSy` prefix check at process initialization. Mock output was explicitly
  disabled. Logs report live Gemini unavailable and heuristic fallbacks. No
  upstream key-validity assertion or successful live-Gemini inference is made.
  The secret was neither printed nor edited. Credential presence alone is not
  runtime availability; see [provider](../../backend/infrastructure/llm/providers/gemini.py).
- Actual pinned Chart.js 4.4.1 bytes were served to Chromium; external browser
  resources/fonts were blocked. Provider traffic came from the real backend,
  not browser-response fixtures. Startup resource/console failures are recorded
  separately from JavaScript exceptions.

Fresh raw responses, event streams, logs, temporary dossiers and full screenshots
were kept outside the repository in a new `aegis-twelve-live-*` system-temp tree.
The durable evidence index below contains only selected measurements and images,
not full investigation dossiers or credentials.

## Pass A — fixed local API matrix

All 12 POSTs returned HTTP 200. `Records` means retained native source records,
**not** verified bodies, relevant claims, independent corroboration or web coverage.
Words use whitespace-delimited tokens in one retained `content`/`snippet` string
per native evidence record. KB is UTF-8 bytes / 1,000, excluding JSON metadata,
discovery-only text and duplicated projections. Repeated Tata text across two
agents is counted twice; totals are not a deduplicated research corpus.

| Agent | Input | Seconds | Records | Body KB | Words | Shared findings | Discovery cards |
|---|---|---:|---:|---:|---:|---:|---:|
| Scout | TATAMOTORS.NS | 18.91 | 1 | 4.005 | 623 | 2 | 18 |
| Scout | INFY.NS | 27.81 | 0 | 0 | 0 | 1 | 4 |
| Scout | AAPL | 25.18 | 0 | 0 | 0 | 0 | 0 |
| Trending | OpenAI | 27.60 | 0 | 0 | 0 | 0 | 0 |
| Trending | NVIDIA | 17.85 | 0 | 0 | 0 | 0 | 0 |
| Trending | electric vehicles | 12.56 | 0 | 0 | 0 | 0 | 0 |
| BrandShield | Nike | 15.88 | 0 | 0 | 0 | 2 | 0 |
| BrandShield | Apple | 15.26 | 1 | 4.031 | 666 | 2 | 0 |
| BrandShield | Tata Motors | 10.05 | 1 | 4.005 | 623 | 2 | 0 |
| Personal Watch | Sam Altman | 7.57 | 1 | 0.101 | 18 | 1 | 0 |
| Personal Watch | Tim Cook | 7.35 | 1 | 0.059 | 8 | 1 | 0 |
| Personal Watch | Satya Nadella | 7.76 | 1 | 0.073 | 10 | 1 | 0 |

Total: **12 displayed finding strings, six retained source records and 1,948
retained-text words**. Findings include legacy projections, not 12 adjudicated
claims. Of 18 supporting-reference observations, one resolves to a source
record, four to discovery-only candidates and 13 are unavailable in the shared
report. These observations count references, not distinct verified claims.

## Confirmed defects and priorities

### P1 — Safety notices are promoted into high-severity threat signals

BrandShield/Tata Motors classified `https://www.tata.com/` as a suspected phishing
or scam vector, severity `high`, confidence `0.78`. The captured page contains
Tata's own job-scam warning, not an observed attacker listing. The fallback
classifier searches the entire navigation-heavy body for scam keywords. Its
fixed official-domain list includes `tatamotors.com`, not `tata.com`, and the
keyword branch assigns the hard-coded score without contextual entailment.

Owner: [BrandShield assessment](../../backend/agents/brandshield/assessment.py),
especially the official-source check and `scam_kw` branch. Fix requires
entity-linked ownership plus passage-level role/context classification. Do not
simply whitelist every corporate domain or suppress genuine external reports.
Regression: official anti-scam notice must not become an attacker/threat; a real
unauthorized listing must remain investigable. Confidence must be labeled as a
heuristic, not a calibrated probability.

### P1 — Finding states overstate the actual evidence

- Scout/Tata Motors labels corporate navigation as `SUPPORTED`, while its
  misinformation assessment returns `NOMINAL` / `LOW` despite no primary filing.
- Scout/Infosys labels a headline `SUPPORTED` although zero bodies were acquired;
  the same response correctly says `INSUFFICIENT_EVIDENCE` elsewhere.
- BrandShield/Apple labels homepage merchandising/navigation `KNOWN_FACT`.
- Personal Watch promotes short profile bios into findings. These are not
  impersonation investigations, independent identity confirmation or media
  forensics. Captured role text is not independently verified current identity.

Owners: [synthesis](../../backend/application/research/synthesis.py) falls back
from investigated items to ranked candidates and assigns `SUPPORTED` whenever
the group is nonempty. `KNOWN_FACT` can come from an official/primary label
without proving that the selected passage supports a substantive proposition.
[Scout assessment](../../backend/agents/scout/assessment.py) only handles total
source absence conservatively; a weak homepage can still unlock normal/low
output. Require relevant passage support, content-depth and uncertainty gates;
navigation/profile/search metadata must remain observations, not corroboration.

### P1 — Citation IDs are regenerated before shared reporting

BrandShield uses IDs such as `ev_001` for returned evidence while structured
findings cite the research engine's IDs. Personal Watch similarly recomputes a
hash from URL/title/author. For example, Tim Cook's finding cites
`ev_0b120dbc5f29`, but its returned profile record is `ev_e339bf5c3e`.
The shared renderer truthfully shows `UNAVAILABLE`, but cannot repair a broken
upstream join. Five references in cases with acquired records fail this join;
Nike's other eight unavailable references instead lack inspectable discovery
records in the returned report.

Owners: [BrandShield scanning](../../backend/agents/brandshield/scanning.py),
[Personal Watch monitoring](../../backend/agents/personal_watch/monitoring.py).
Trending also regenerates IDs in [its adapter](../../backend/agents/trending/agent.py);
the empty evidence in Pass A does not independently reproduce a Trending join.
Preserve canonical IDs and explicit aliases through agent normalization; test
joins end-to-end without treating ID presence as proof of claim support.

### P1 — BrandShield's empty-state return hides available findings and telemetry

Pass A/Nike has two findings in `unified_report`, but neither viewport renders
the shared report. The page displays a zero-source banner and returns before
`renderUnifiedReport`, also suppressing query diagnostics. No uncaught page
exception occurs: this is a deterministic presentation branch, not a browser
crash. Pass B reproduces it with the exact returned payload at both widths.

Owner: [BrandShield page](../../frontend/brandshield-agent.html), zero-source
branch around line 478 versus shared renderer around line 701. Always render
the completed report's uncertainty/findings/telemetry, even when no acquired
records exist. Keep the honest empty-acquisition banner; do not invent sources.

### P2 — Discovery/read budgets do not reliably deliver useful depth

All Pass A research funnels report `discovery_timeout_reached`, no adaptive
rounds and zero primary sources. Timeouts and provider cooldown/empty states
are visible. Scout/Infosys discovered 30 candidates, retained four, attempted
two reads and acquired none. Scout/Apple rejected all 11 candidates.

[Broad discovery](../../backend/application/research/acquisition.py) can receive
10 seconds while the adaptive discovery ceiling for a 15-second request is
6.75 seconds. [Deep reading](../../backend/application/research/reading.py)
gets the remainder, not an independently enforced reserved slice. Longer
browser waiting does not change these internal bounds. Diagnose page selection,
overlong queries, qualification reasons, bounded read opportunity and per-source
backoff before expanding fan-out. Do not weaken the relevance gate to inflate
counts; the audit does not prove that all rejected candidates were relevant.

### P2 — Discovery context is not consistently exported by all agents

Scout returns `research_corpus`; Trending, BrandShield and Personal Watch do not
return that corpus at the same boundary. The shared completion helper builds
discovery cards from `research_corpus`. Nike therefore has findings with eight
unavailable references and zero discovery cards, despite 12 accepted/ranked
candidates in its trace. A missing body should not erase inspectable leads,
selection reasons or failed-read context. Export a bounded, explicit discovery
contract separately from acquired evidence; never promote candidates to bodies.

### P2 — Query submission counters disagree

For Pass A/BrandShield Tata Motors the native funnel reports four submitted
queries and two skipped, while shared telemetry reports six submitted and two
skipped. [QueryTelemetry](../../backend/schemas/unified_report.py) counts every
status other than `PLANNED` as submitted, including `SKIPPED`; corpus assembly
subtracts skipped records. Define one execution lifecycle and add cross-layer
invariants. A successful query may also return zero normalized records; do not
equate query-success counts with successful source acquisition.

### P2 — Readability and strategic presentation remain incomplete

From the visual evidence, findings hug the card border while summaries and
evidence notes have normal insets. Pass B measured a 1px finding inset. The
new findings `<ul>` lacks the existing `ur-list` class; see
[renderer](../../frontend/unified-report-renderer.js) and
[theme](../../frontend/aegis-theme.css). Long citation strings and menu text
dominate the report, and profile Markdown markers appear literally. The small
count brief is honest, but is not an executive explanation or strategic result.
Generic next steps are not linked to observed case-specific gaps; avoid implying
that impersonators or counterfeit listings were actually found.

## Browser evidence and remaining acceptance

Pass B: 24 states, no detected horizontal overflow or uncaught page exceptions.
22 states render matching findings/evidence/discovery card counts. Nike's two
states hide the entire shared report. Whitespace was normalized when comparing
finding text to the DOM. The four available Scout discovery controls respond
to keyboard Enter. These limited checks are not an accessibility certification.

Pass C completed all 12 real button-to-backend SSE investigations: HTTP 200,
one result event and 29 observed progress events each, with no SSE error events.
All 24 viewport states had matching findings/evidence/discovery DOM counts,
no missing finding text, no uncaught page exceptions and no horizontal overflow.
This does not remove the Pass B/Nike defect: Pass C/Nike happened to acquire a
record, so did not exercise that zero-source branch.

| Agent | Input | Browser seconds | Retained records | Body KB | Words | Findings | Discovery cards |
|---|---|---:|---:|---:|---:|---:|---:|
| Scout | TATAMOTORS.NS | 18.44 | 1 | 4.005 | 623 | 2 | 18 |
| Scout | INFY.NS | 29.83 | 0 | 0 | 0 | 2 | 5 |
| Scout | AAPL | 29.87 | 0 | 0 | 0 | 2 | 7 |
| Trending | OpenAI | 18.35 | 0 | 0 | 0 | 1 | 0 |
| Trending | NVIDIA | 14.11 | 0 | 0 | 0 | 0 | 0 |
| Trending | electric vehicles | 12.32 | 0 | 0 | 0 | 0 | 0 |
| BrandShield | Nike | 17.07 | 1 | 4.027 | 678 | 2 | 0 |
| BrandShield | Apple | 13.98 | 5 | 12.200 | 1,551 | 5 | 0 |
| BrandShield | Tata Motors | 5.90 | 2 | 4.118 | 639 | 3 | 0 |
| Personal Watch | Sam Altman | 13.25 | 1 | 0.101 | 18 | 1 | 0 |
| Personal Watch | Tim Cook | 8.13 | 1 | 0.059 | 8 | 1 | 0 |
| Personal Watch | Satya Nadella | 6.70 | 1 | 0.073 | 10 | 1 | 0 |

Pass C totals: 20 finding strings, 12 retained records, 3,527 retained-text words;
five zero-acquisition inputs. Its 25 reference observations resolve as one
source record, 12 discovery-only and 12 unavailable. Do not add these to Pass A
as if they were unique sources. Apple accounts for five records: two homepages,
one support page and two X profiles. Three Apple pages are labeled primary
documents by the backend; that is not three independent filings. The Nike
storefront identifies itself as official, but this audit did not authenticate
ownership of its `nike.in` domain or adjudicate the counterfeit signal.

At least one focused capture was visually inspected for each of the 12 fresh
Pass A responses and each of the 12 live Pass C responses, plus selected desktop
counterparts. Navigation text, missing inset, literal profile markup and
unsupported state labels are visible. One initial Tim Cook desktop screenshot
showed blank cards despite populated DOM. Replaying its exact fresh payload
with natural font/layout/frame waits produced content in four repeated viewport
captures (both desktop captures visually inspected). This is a capture-stability
limitation, not a confirmed persistent app defect; originals/rechecks remain.

Pass C logged 18 console resource errors across its 12 page loads. External
resources were deliberately blocked and the static harness also saw 404s, but
the runner did not retain a per-resource failure map: those entries are not
individually attributed or declared resolved. They are not uncaught exceptions.

An earlier browser capture harness failed to read fetch-consumed SSE through
Chrome's response-body API. Seven investigations started in that attempt;
backend logs show six completed and one was interrupted when only that harness
process was stopped. Those attempts are excluded from the complete acceptance
matrices, not hidden as successful measurements. The corrected observer used
`Response.clone().text()` while returning the unmodified response to the app's
stream consumer. No application fix was made for this instrumentation issue.
No additional provider request was used for the stable Tim Cook recheck.

See [durable screenshot/evidence index](evidence/2026-10-16_agent_output_audit/README.md)
and [machine-readable measurements](evidence/2026-10-16_agent_output_audit/measurements.json).

**UNVERIFIED:** manual screen-reader behavior, measured WCAG contrast, axe,
Safari/Firefox, real mobile hardware, authenticated provider depth, successful
live-Gemini synthesis, all 16 operation contracts, production parity, hosted CI
and production-launch readiness. Empty-state/failure semantics and strategic
research quality are not accepted merely because the pages have no overflow.

## Safe next implementation order

1. Fix context-sensitive false positives and conservative epistemic states.
2. Preserve citation identities and bounded discovery/failed-read context.
3. Remove the BrandShield report-hiding early return and restore findings inset.
4. Reconcile lifecycle counters; enforce measured discovery/read reservations.
5. Re-run this fixed matrix with a provider-accepted, successfully verified LLM
   configuration, then assess whether outputs answer each agent's actual job.

No merge, commit, push, deployment or historical dossier recovery is authorized
or performed by this report. Preserve frozen benchmarks and historical records.
