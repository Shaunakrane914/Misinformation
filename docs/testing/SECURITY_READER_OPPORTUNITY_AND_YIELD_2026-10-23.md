# Security, reader opportunity and useful source yield — 2026-10-23

## Decision

**Known defects repaired; offline regression green; research acceptance PARTIAL.
No commit, push, merge or deployment.** This is not a claim that all project
vulnerabilities are eliminated, or that every agent now returns enough evidence.

The user authorized up to six AI-disabled local investigations. Exactly six ran:
Adobe, Dyson, battery recycling and Mary Barra, followed by one Mary Barra and
one Dyson post-fix investigation. All returned a result event; none returned an
SSE error. Zero AI reservations/calls, paid Firecrawl calls, supplied article
URLs, audit-level retries or production mutations. The six-case permission is
consumed. Another live investigation needs a new bounded authorization.

Checkout: `.scratch/phase9-remediation-20261016`, branch
`fix/p0-lenovo-acquisition-20261018`, HEAD
`39a514b68388450bbc5e6061aba97bda2077fc7f` plus inherited dirty implementation.
Changes from older iterations were preserved, not all authored in this task.
[Selected measured proof](evidence/2026-10-23_hardening_reader_yield/measurements.json)
binds captures to response hashes and stable application fingerprints.

## Repaired causes and safety tradeoffs

| Owner / function | Observed defect and implemented correction |
| --- | --- |
| [PublicRequestBudget](../../backend/infrastructure/acquisition/network/budget.py), `reserve_reading_capacity`, `public_request_phase` | Broad search could consume HTTP opportunity needed by publisher resolution/direct reads. A shared locked phase budget now fences discovery; DEEP retains at least half of the 120-admission helper budget for reading, with four per-host slots reserved from discovery. Total/per-host caps, closed-budget guards and deadlines remain enforced. Reader-stage publisher lookup legitimately uses reading capacity. This reserves opportunity, not a guarantee of useful content. |
| [HarvestingEngine.run](../../backend/services/research/harvesting.py) | Stop submitting discovery waves after the discovery allowance is spent, with explicit `DISCOVERY_HTTP_RESERVE_FOR_READING` / not-submitted diagnostics. Observed publisher-hub continuation is available across all four domains after opaque-wrapper slots are spent, within existing read/host caps. No guessed article URLs or new provider. |
| `_BudgetedService.read` in the same file | An accidental 12,000-character clamp discarded part of the reader's supported 20,000-character capture request. It now honors requests up to 20,000. The 1 MB wire limit, bounded run storage/time and normal access/security checks remain. No arbitrary unlimited scraping. |
| [result_fit](../../backend/infrastructure/acquisition/adapters/web/search_observations.py) | A matching-headline opaque Google/Bing wrapper could pass *publisher URL resolution* and suppress the next existing search fallback, then fail later at reading. Resolution now rejects it as `UNRESOLVED_SEARCH_WRAPPER`; ordinary discovery still retains wrappers. The existing headline-overlap gate is unchanged. The final live Mary result shows this is not a complete wrapper-resolution solution. |
| [run_harvest_pipeline](../../backend/application/research/harvest_pipeline.py), [discovery_funnel](../../backend/services/research/discovery_funnel.py) | Navigation/link audit rows inflated candidate-rejection counts. Counts now distinguish distinct rejected sources, audit decisions, actual captures, bodies and qualified/displayed sources. Stage/reason scope and samples are explicit; actual read loss cannot point backward to pre-read filtering. |
| [ReportBuilder](../../backend/services/report_builder.py), [acquisition status](../../backend/services/research/acquisition_status.py) | Raw captures with no qualified passage were described as no acquisition. Reports now explain captured-but-ineligible content and actual read failures. Copy working candidate lists instead of mutating input corpus lists during rendering/report assembly. |
| [PassageExtractor](../../backend/services/research/passage_extractor.py), [content roles](../../backend/services/research/content_roles.py) | Quiz questions, repeated titles and webcast logistics could become financial findings. Standalone questions/titles are excluded; exact monetary-result paragraphs are preferred while quotations, warnings and incident prose survive. Raw source bodies and exact span attribution remain unchanged. |
| [Financial context](../../backend/services/research/financial_context.py), [financial observations](../../backend/services/research/financial_observations.py) | Prompts cannot unlock an asserted result; forecast/consensus context stays separate. Bare dollar glyphs remain `DOLLAR_SYMBOL_UNSPECIFIED`, not invented USD; ambiguous-currency comparisons abstain. This is not complete issuer/period/table adjudication. |
| [Specialist brief](../../backend/services/research/specialist_brief.py), [BrandShield intelligence](../../backend/agents/brandshield/intelligence.py) | Brand reports borrowed Personal Watch profile/media limitations. Domain wording is corrected. A sourced product recall/correction is described as product safety, not an observed scam/counterfeit seller; it remains unverified, non-threatening, with no actor URL. |

### Optional integrations/security

[Huginn adapter](../../backend/infrastructure/acquisition/adapters/events/huginn.py)
and [event routes](../../backend/api/events.py) remain **disabled/unregistered by
default**, consistent with the owner's refusal to configure Huginn.

When explicitly enabled, shared-token authentication precedes body processing.
POST requires JSON and enforces a 128 KB declared/streamed-body cap. DNS and
SQLite ingestion run off the event loop. GET requires the same secret. Payload
types/dates, nested metadata, content and retention are bounded; mismatched
checksums reject. Repeated IDs are idempotent; altered reuse returns 409;
persistence failure returns 503. Versioned SQLite state preserves the legacy
table. An event is never treated as independent confirmation simply because it
has a unique ID. Duplicate originals retain their lineage after retention eviction.

**Correction to the older integration handoff:** the shared secret is token
authentication, not HMAC signing of the payload. A matching checksum is not
source authenticity or independent corroboration. Bounded deduplication is not
an infinite historical identity register.

[Firecrawl](../../backend/infrastructure/acquisition/adapters/web/firecrawl.py)
and [Jina](../../backend/infrastructure/acquisition/adapters/web/jina.py) no longer
echo raw provider exceptions/credential-shaped origins. Sanitized numeric HTTP
status is preserved for honest 429 diagnostics. Firecrawl recognizes embedded
denial/throttle and upstream non-success metadata even under outer HTTP 200.
Jina does not route around terminal authorization, robots, paywall, rate-limit,
security or budget failures. Live paid Firecrawl and Huginn were not exercised.

## Offline-first implementation cycle

Genuine saved Adobe responses were reprocessed with networking blocked. Body
hashes and 9,460 raw article words were unchanged. Selected excerpt words fell
420 → 411 because noise was removed: the 17-word quiz became zero; a 55-word
webcast paragraph was replaced by a 39-word reported-results paragraph.
This is an interpretation improvement, not new acquisition.

Synthetic held-out controls exercise shared/copy-context HTTP budgets, closed
budgets, observed hubs, wrapper-only/mixed/no-result resolution, exact passages,
ambiguous currencies, malformed/oversized events, persistence failures and
embedded provider errors. Replay/synthetic positives are not live proof.

Subtask decisions and exact tests:
[passage controls](../handoffs/2026-10-23_PASSAGE_SIGNAL_CONTROLS.md) and
[diagnostic/wording repair](../handoffs/2026-10-23_ACQUISITION_DIAGNOSTICS_REPAIR.md).
Root controls:
[reader reservations](../../tests/unit/test_reader_opportunity_reservation.py),
[publisher resolution](../../tests/unit/test_publisher_resolution_transport.py),
[optional-reader security](../../tests/unit/test_optional_reader_security.py).

## Fresh autonomous acquisition: first four cases

Normal local agent routes/SSE, DEEP, at most 240 seconds, 24 reads and 120 native
HTTP admissions per investigation. Temporary SQLite/dossiers; notifications,
background ingestion, model generation and paid reader access disabled. No
manually supplied publisher/article URL.

Application fingerprint was stable during the first four:
`0430b4b49f0aff586a12e2f5fbbbe4a402b98e276645e1b937fe4a58a3c9eb3f`.
These observations precede the final wrapper-resolution and wording correction.

| Agent / input | Seconds | Candidate URLs | Reads / captures | Article bodies | Raw article KB / words | Code-qualified sources / selected excerpt words |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Scout / Adobe | 52.92 | 35 | 24 / 15 | 14 | 118.115 / 16,908 | 13 / 650 |
| BrandShield / Dyson | 23.58 | 11 | 9 / 6 | 1 | 4.936 / 781 | 1 / 48 |
| Trending / battery recycling | 43.89 | 59 | 22 / 16 | 7 | 77.904 / 10,916 | 1 / 28 |
| Personal Watch / Mary Barra | 35.60 | 22 | 12 / 7 | 1 | 3.009 / 484 | 0 / 0 |

Counts are saved code classifications, not an independent truth evaluation.
Words are whitespace tokens; KB is retained UTF-8 article bytes / 1,000, excluding
metadata and duplicate captures. Raw words include stale/irrelevant content.
Selected excerpt words are not whole qualified-body words or verified claims.
No article body in these six cases was flagged a duplicate; repeated bodies
across investigations must not be summed as new unique evidence.

The first four contain **23 raw article bodies / 29,089 words / 203.964 KB**.
The previous [four-case snapshot](SCRAPER_REPAIR_AND_STRENGTH_2026-10-23.md)
contained 12 bodies / 11,952 words with 180s/16-read/80-admission limits.
These are different budgets and fresh provider responses, **not a controlled
causal before/after benchmark**. Per-case raw words changed:
Adobe 9,460 → 16,908; Dyson 0 → 781; battery recycling 2,008 → 10,916;
Mary Barra 484 → 484. Increasing size did not solve Mary's task.

### Are the results useful enough?

- **Adobe:** source acquisition demonstrated, with actual reported-results
  paragraphs rather than the former quiz/logistics selection. Thirteen retained
  records contain 16,509 body words; 650 words were selected. This is not proof
  of correct financial adjudication, independent publishers or fiscal alignment.
  Multi-company earnings previews can still carry weak issuer-level entailment.
- **Dyson:** a 781-word Cybernews capture contains a product-issue report and
  explicit correction/company response. The 48-word selected correction survives.
  One unverified safety report is not confirmed fraud, counterfeit evidence or
  broad threat coverage. It must not be marketed as a detected scam.
- **Trending:** seven captured articles reduce to one task/freshness-qualified
  587-word Electrek report about Rivian/Redwood battery recycling; its selected
  development is 28 words. Other acquired bodies are rejected. This is a useful
  sourced development, not established virality or a multi-source trend.
- **Mary Barra:** the 484-word 2021 appointment article has no relevant
  task-specific public-statement/incident passage. Other captures are hubs or
  structural/entity mismatches. Qualified evidence remains zero. **Not enough.**

Selected exact source URLs, publication declarations, body/capture hashes and
observed transport endpoints are in the measurements. Dates are captured
publisher declarations, not independently verified timestamps; publisher labels
from search feeds are not ownership authentication.

### Funnel bottlenecks and request phases

| Input | Native discovery / reading admissions | Main remaining loss |
| --- | ---: | --- |
| Adobe | 38 / 30 | Ten eligible leads remain unread at the 24-read limit; nine attempted reads fail (six access denied, three provider failures). Bodies do reach qualification. |
| Dyson | 58 / 19 | Three unresolved publisher reads; two additional opaque leads remain unread. One relevant body survives. |
| battery recycling | 58 / 31 | Three unresolved publishers, two access denials, one provider failure; many acquired bodies fail relevance/freshness. Eight opaque and 29 host-budget-limited leads remain unread. |
| Mary Barra | 57 / 23 | Three unresolved publishers plus access/provider failures restrict useful bodies. The only article then fails passage relevance. Ten opaque leads remain unread. |

Discovery reserve refusals were 0 / 7 / 5 / 2 respectively. All total/per-host
helper admissions remained within 120 / 24. **Complete network accounting remains
false**: helper admissions do not claim to count every internal/legacy/provider
operation. A successful query lifecycle does not imply a useful body acquisition.
A rejection may have multiple reasons; link audits are not extra source rejections.

## Final two post-fix cases

After the first four, exact-title wrapper-only suppression was fixed and
BrandShield wording was corrected using saved captures. The final two were
separately bounded reruns, not hidden retries within the first matrix.

Stable final application fingerprint:
`7ac1b23a84c9798074933f93f99c253d428bf3cd1f2b32dc80446e50f5256bcd`.

| Input | Seconds | Candidates | Reads / captures | Raw article KB / words | Qualified sources / selected words | Discovery / reading admissions |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Mary Barra | 29.74 | 20 | 12 / 9 | 3.009 / 484 | 0 / 0 | 58 / 21 |
| Dyson | 25.77 | 13 | 11 / 8 | 4.936 / 781 | 1 / 48 | 55 / 25 |

Mary still has three unresolved publisher reads and eight unconsumed opaque
leads. Extra successful captures (7 → 9) are homepages/indexes, not useful new
article evidence. Raw capture words increased 6,744 → 11,754 while useful words
stayed zero: **do not present that as a research-quality improvement**.
The final status is `INSUFFICIENT_EVIDENCE`, explicitly explaining raw captures
and their rejection, not claiming no public information exists.

Dyson's final report retains the exact correction, gives product-safety wording
and brand-specific limits, emits no independently verified threat and no actor
URL. Three publisher-resolution failures remain. Its source-backed output is
not comprehensive threat detection. Neither rerun exhausted its total deadline;
simply adding more waiting time would not remove these barriers.

## Actual verification

Final backend code was frozen before the last two live checks. Normal tests use
isolated storage and mocked/disabled external/model traffic.

| Command / scope | Exit / actual outcome |
| --- | --- |
| `python -m pytest tests/ -q --tb=short -p no:cacheprovider` | 0; **2,124 passed / 69.58s** |
| `python -m pytest tests/unit tests/chaos tests/security -q --tb=short -p no:cacheprovider` | 0; **1,916 passed / 63.36s** |
| `python -m flake8 backend tests scripts --count --select=E9,F63,F7,F82 --show-source --statistics` | 0; zero fatal findings |
| Each of nine `tests/frontend/test_*.js` Node scripts | 0 each |
| `python scripts/validate_release_candidate_smoke.py` (final repeat) | 0; OFFLINE_SMOKE_PASS, acquisition disabled/mocked, not live acceptance |
| `python scripts/validate_rollback_compatibility.py` (final repeat) | 0; OFFLINE_PERSISTENCE_PASS; actual historical archive and deployed rollback NOT_VERIFIED |
| `python scripts/validation/verify_frozen_benchmarks.py` | 0; content hashes match |
| Protected tracked diff / whitespace | 0; protected trees unchanged relative to HEAD |
| New documentation links / saved measurement invariants | 0; 44 relative links resolve; six cases satisfy recorded time/read/helper-admission bounds, stable fingerprints and zero AI reservations |
| Separate read-only root-change review / focused tests | 0; 32 passed / 0.80s, no new bounded-scope blocker found |
| First four and final two live terminal runner batches | 0 each; six completed result events, no SSE errors; research outcome assessed separately above |

Intermediate failures are not erased: the first full/fast attempt each had one
chaos failure because safe status redaction also removed the numeric 429 needed
for diagnostics. Keeping only the numeric status fixed it without returning the
raw secret-bearing exception. Other initial adversarial passage/wording and
fixture failures are recorded in the subtask handoffs. Overlapping focused
counts must not be added to the full-suite inventory.

Portable live command (documentation only; authorization already consumed):

```text
python scripts/audits/run_terminal_agent_quality.py --allow-live --env-file <server-env> --output-dir <new-temp-directory> --research-profile DEEP --timeout-seconds 240 --max-deep-reads 24 --max-http-admissions 120 --case scout:Adobe --case brandshield:Dyson --case "trending:battery recycling" --case "personal_watch:Mary Barra"
```

The final command used only `personal_watch:Mary Barra` and `brandshield:Dyson`,
with identical caps and a new temp directory. Neither command included
`--allow-live-ai`. The offline summarizer read saved outputs without acquisition.

## Remaining work / release boundary

1. **Personal Watch P0:** strengthen observed publisher resolution and task-shaped
   public-statement/incident recall. Use these saved rejected/wrapper records
   first; never count appointment/hub text as proof merely to satisfy a quota.
   Another live verification requires a new small case/request authorization.
2. **Research accuracy:** independently review issuer/period/amount support,
   safety-report scope, publication claims, citation entailment and abstentions.
   Existing count/label gates are not independent evaluation.
3. **Security coverage:** no dependency-advisory scan or penetration test was
   performed; Bandit/pip-audit were unavailable. Token-authenticated Huginn is
   not HMAC-signed; optional integrations remain unverified live. Do not claim
   the whole project is vulnerability-free.
4. **Release:** no new rendered-browser, hosted CI, production-parity, deployment,
   real rollback or historical-dossier integrity acceptance. The documented
   historical 55 malformed dossiers were not repaired or silently skipped into
   acceptance. This isolated checkout's archive inspection remains NOT_VERIFIED.

Original logs/native responses/event streams/pipeline captures/temp dossiers:
`aegis-hardening-yield-a5abf902b68549aabd022efa70ddaba1` and
`aegis-hardening-postfix-af88fe398f344302818c9a57bcabe474` under system temp.
They may expire. Durable selected measurements omit bodies, credentials, headers
and private data; hashes allow matching originals if retained. Historical evidence
and prior reports were preserved. No secret, approval flag or frozen label was
changed. This document records engineering conclusions, not a private reasoning
transcript.
