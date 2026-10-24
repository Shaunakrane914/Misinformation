# Four random-pool prompt recheck — 2026-10-19

## Result

**Research-quality acceptance: FAIL for this sample. Bounded frontend replay: PASS.**

The user requested four new prompts after the offline repair. One input per agent
was selected using PowerShell `Get-Random` from small predeclared pools. These are
unseen smoke inputs, not an independently labeled evaluation or a representative
random sample of all user requests. No application source was changed during this
check. The preceding uncommitted repairs were preserved.

| Agent / input | Live local seconds | Retained records | Words | Decimal KB | Qualified findings | Interpretation |
| --- | ---: | ---: | ---: | ---: | ---: | --- |
| Scout / SONY | 36.95 | 4 | 3,892 | 34.011 | 0 | Partial news/press indexes and storefront content; no useful financial adjudication |
| Trending / quantum computing | 32.52 | 0 | 0 | 0 | 0 | Discovery returned candidates, but none passed current qualification |
| BrandShield / LEGO | 37.11 | 0 | 0 | 0 | 0 | Six publisher-resolution acquisition attempts failed; explicit ACQUISITION_FAILED |
| Personal Watch / Lisa Su | 44.71 | 1 | 10 | 0.053 | 0 | Profile metadata only; five article-wrapper resolutions failed |

Total retained text: **3,902 words / 34.064 KB in five records**, not five useful
articles or verified facts. Words count whitespace tokens in one native
content/snippet field per record; KB = UTF-8 bytes/1,000, excluding JSON metadata
and discovery cards. No source-backed specialist conclusion was established.

All four valid local HTTP/SSE investigations completed with HTTP 200 and result
events. That is transport completion, not successful research.

## Scope and reproducibility

- Branch: `fix/p0-lenovo-acquisition-20261018`; HEAD
  `39a514b68388450bbc5e6061aba97bda2077fc7f`, plus the uncommitted
  [production repair](PRODUCTION_RESEARCH_FAILURE_REPAIR_2026-10-19.md).
- Application fingerprint before/after terminal and browser checks:
  `df0dcf9bd27b5c7290fece6ffe9a505fa1ff36b4a24e6c9759d98e5f8052f442`.
  Both runners recorded unchanged application bytes.
- Actual local `backend.main:app` routes and normal acquisition; not deployed
  Cloudflare/Render verification. Temporary SQLite/dossier storage, lifespan
  ingestion disabled, notifications/Supabase credentials blanked.
- **AI generation disabled, zero live AI calls.** No mock generation substituted.
  Runtime log reports zero Gemini keys. Existing `.env` was read only inside the
  isolated subprocess, not printed, edited or copied to durable proof. Existing
  configured provider/access flags were retained, not authenticated or changed.
- Pools: Scout `ADBE/ORCL/SONY`; Trending `quantum computing/solid state batteries/robotaxis`;
  BrandShield `LEGO/Adidas/Samsung`; Personal Watch `Lisa Su/Sundar Pichai/Jensen Huang`.
  Inputs were fixed before their valid run and not changed to obtain better output.
- Four valid cases ran sequentially, one POST each, without audit-level retries.
  Browser verification replayed their exact SSE: **no second provider matrix**.

Instrumentation failure disclosed: an initial PowerShell array-expression error
concatenated the four selections into one malformed Scout input. Its identified
Python process was stopped, and its logs retained separately. Provider calls had
already occurred; this is **one additional interrupted launch**, not one of the
four valid observations. It is not hidden as a successful test. Case arguments
were then constructed separately and their count checked before the valid run.
No AI was enabled for either launch. Total underlying provider HTTP request count
was not independently measured; do not describe this task as only four HTTP calls.

## What failed and what the repairs actually proved

### Scout / SONY

Six acquisition attempts yielded four partial-content records: Sony Group news
releases, Sony India press centre, a Business Today Sony topic page and Sony
Electronics storefront. Inspected excerpts contain menus, archive links and
merchandising. They are not acquired financial statements or claim comparisons.
One SonyLIV attempt reports generic PROVIDER_FAILURE without an upstream HTTP code;
one article wrapper is PUBLISHER_UNRESOLVED. No more precise failure cause is claimed.

Entity resolution returned UNRESOLVED_LISTING, no proposed validated symbol/currency
and `quote_validated=false`. Company research continued without invented market
telemetry. Root pipeline status is COMPLETED because records exist; the report
does not establish that the financial research objective was completed.

### Trending / quantum computing

Twenty raw candidates were returned; all were rejected before reading. In that
raw-candidate set, observed rejection metadata groups as:

- Nine TEMPORAL_STALE items outside the existing 48-hour Trending window.
- Three static encyclopedia references, inappropriate as current trend evidence.
- Eight ambiguous single-token matches. The resolver describes `quantum` as a
  first name and `computing` as a surname when the full topic phrase is absent.

The personal-name rule is in
[EntityResolver](../../backend/services/research/entity_resolver.py); applying its
surname framing to a broad technical topic is a generalization concern. Some
rejected results really are generic/unrelated, so this audit does **not** label all
eight as false rejections or weaken the gate to inflate counts. Useful topical
planning/qualification and honest rejected-lead explanations remain needed.

The current response is INSUFFICIENT_EVIDENCE, zero deep reads and zero shared
discovery cards. Raw rejected leads remain in the saved corpus. It is inaccurate
to describe this case as all searches timing out: nine query records are SUCCESS.

### BrandShield / LEGO

Twenty raw candidates, eighteen accepted leads, six distinct acquisition attempts,
zero bodies. **All six fail at PUBLISHER_UNRESOLVED**, before a matching publisher
body can be requested. Each resolver retained three returned candidates, all
TITLE_MISMATCH; observed title-token overlaps range from 0 to 0.167. Examples
include a LEGO scam headline resolving to generic international-news pages and
a counterfeit headline returning official LEGO storefronts.

This makes the remaining bottleneck inspectable: the lookup did not provide a
matching article URL. It does not establish that the article is inaccessible,
that a publisher HTTP timeout occurred, or that lowering the 75% join is safe.
The specialist stage exercised six bounded attempts rather than stopping after
the initial three-candidate batch. Replacement opportunity works, but repeating
poor headline lookup across alternatives did not produce useful content.

The frontend prominently displays **ACQUISITION FAILED — UNABLE TO RETRIEVE
EVIDENCE**, keeps eighteen inspectable discovery leads and makes no safety claim.

### Personal Watch / Lisa Su

Six acquisition attempts yield one PROFILE_METADATA record and five
PUBLISHER_UNRESOLVED failures. The entire retained text is a captured profile
heading and “Chair and CEO of @AMD”; this is not independent role verification,
identity-abuse analysis or a substantive public-statement investigation.

The report correctly says zero task-related captures and no exposure conclusion.
Rendered doxxing and quote-authenticity labels are UNASSESSED. Pipeline COMPLETED
means a profile record was retained, not that Personal Watch's job succeeded.

### Timing and execution lifecycle

| Case | Query records / reported started | SUCCESS | TIMEOUT | Other | Acquisition attempts / successes | Remaining discovery seconds at initial snapshot |
| --- | ---: | ---: | ---: | --- | ---: | ---: |
| SONY | 16 / 16 | 14 | 1 | 1 AUTH_REQUIRED | 6 / 4 | 26.875 |
| quantum computing | 14 / 14 | 9 | 5 | — | 0 / 0 | 23.783 |
| LEGO | 12 / 12 | 10 | 2 | — | 6 / 0 | 26.360 |
| Lisa Su | 12 / 12 | 8 | 2 | 2 FAILED | 6 / 1 | 35.840 |

The aggregate reports **54 started queries**, but only **48 main records have
explicit measured provider starts**. Six adaptive records omit `provider_started`
and are inferred as started from their result statuses; equivalent lifecycle
instrumentation remains unverified (existing defect D13). None is QUEUE_TIMEOUT,
NOT_SUBMITTED or SKIPPED. Nested wrapper-resolution queries are additional and
not included in that 54-record denominator. SUCCESS may return no useful records.
“Acquisition attempt” does not mean a publisher HTTP read started: unresolved
wrappers fail earlier. Main query counts do not include every HTTP fallback.

Each initial capability snapshot took under 0.2ms and recorded zero synchronous
doctor calls. The 120s total research window was not exhausted. The remaining
discovery numbers are stage snapshots, not final remaining request time. Some
individual provider chains still timed out; no unsupported claim is made about
their precise upstream cause. This sample does not support diagnosing all failures
as sleeping backend, slow doctor or overall timeout starvation.

## Frontend verification and limits

Exact result/event files were replayed through actual agent buttons, stream client
and native/shared renderers in Chromium at **320, 390 and 1440px**. Twelve states
had visible reports, matching finding/source/discovery counts, no missing finding
text, no horizontal overflow and no uncaught page exceptions. Source inspection
opened by keyboard for Sony and Lisa Su at all three widths. Four focused 390px
report screenshots were visually inspected.

Readiness is explicitly a replay harness stub; other backend APIs are blocked.
Nine console resource-error entries occurred across four loads, with external
font blocking and unavailable stubbed APIs recorded; they are not declared fixed
or counted as real readiness. No manual screen-reader, measured contrast, axe,
other browser/device, live source-inspection request, production parity or
independent verdict accuracy is established.

[Selected measurements and screenshots](evidence/2026-10-19_four_random_prompt_recheck/README.md)
are durable. Full raw responses/events/logs and temporary dossiers remain in a
new `aegis-four-random-20261019-*` system-temp tree. No protected historical record
or tracked benchmark result was overwritten.

## Commands / next action

The existing terminal audit ran with `--allow-live`, four explicit `--case`
arguments, an existing local `--env-file` and a new temporary `--output-dir`:
**exit 0**. No `--allow-live-ai` or `--capture-from` was supplied. Then the browser
audit ran those same cases with `--replay-dir` and a local pinned Chart.js asset:
**exit 0**. Both are evidence collection, not research-quality acceptance gates.

No application changes, repeated full regression, hosted CI, commit, push, merge
or deployment occurred in this check. Earlier repair test counts are historical,
not claimed as rerun here. Debugging/E2E skills guided terminal-first inspection,
actual negative-case diagnostics and exact-response frontend replay.

Highest-value next repair is **publisher-link resolution/search result quality**,
not another timeout increase. Then separate broad-topic relevance from personal
name ambiguity and promote issuer indexes to observed financial documents only
when relevant links are actually read. Keep the honest failure/UNASSESSED behavior.
Any implementation or further live sampling should be a separately scoped task;
this audit does not authorize deployment or blind repeated provider runs.
