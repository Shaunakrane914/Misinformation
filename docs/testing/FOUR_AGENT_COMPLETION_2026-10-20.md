# Four-agent source-to-browser completion — 2026-10-20

Later continuation: [Trending fresh-source completion](TRENDING_FRESH_ACQUISITION_COMPLETION_2026-10-20.md)
records two new autonomous fresh-article acquisitions and corrected current-code
browser reporting. The historical zero-current-source observation below is preserved.

## Decision

**Functional corrections implemented; overall research acceptance remains PARTIAL.
Do not merge or deploy.** BrandShield now autonomously acquires a real enforcement
report and its corrected source interpretation reaches the API/browser in offline
reprocessing. Personal Watch's quotation survives the complete current specialist
and shared-report path. Scout retains its seven acquired articles, with explicit
financial uncertainty. Trending still has **zero qualified current articles**.
Its correct abstention is not completion of the fresh-research requirement.

This supersedes the remaining-work section of the
[expanded-harvesting checkpoint](EXPANDED_HARVESTING_TWO_LAYER_REPORT_2026-10-20.md),
not its original measurements. Worktree `.scratch/phase9-remediation-20261016`,
branch `fix/p0-lenovo-acquisition-20261018`, base HEAD
`39a514b68388450bbc5e6061aba97bda2077fc7f`, plus preserved inherited changes.
No commit, push, merge, deployment, credential/access-flag change or protected-data
repair was performed.

## A. Final four-agent status

Article words mean retained native text, not complete remote articles or verified
facts. Qualified words are exact selected passages; publisher hosts do not prove
independence. Samsung/Pichai acquisition is the preceding real checkpoint, not a
new network run in this cycle. Their current intelligence was reprocessed offline.

| Agent / subject | Real article acquisition | Current qualification | Intelligence correctness | Browser status |
| --- | --- | --- | --- | --- |
| Scout / Samsung | Prior live: 7 bodies / 6,544 words / 6 hosts | Offline: 7 sources / 805 passage words | Bounded source-context checks verified; financial truth/filing reconciliation NOT established | Current source-backed SSE replay verified; production/live-browser acquisition unverified |
| Trending / grid-scale energy storage | New post-fix live: 1 body / 1,469 words; stale | 0 current sources / 0 useful words | Correct abstention verified; fresh-research acceptance NOT MET | Empty/freshness/access explanation and separate leads verified in replay |
| BrandShield / Adidas | New live: 1 body / 1,092 words / 1 host | Offline correction: 1 source / 79 passage words | Historical enforcement, not an attacker endpoint or confirmed current threat; broader active-threat accuracy partial | Corrected report, source inspection and attribution verified in replay |
| Personal Watch / Sundar Pichai | Prior live: 5 bodies / 4,161 words / 5 hosts | Offline: 1 source / 53 passage words | Correct source-attributed quote/offsets; speech authentication, impersonation and identity UNASSESSED | Quote, uncertainty, readable baseline and source inspection verified in replay |

The final shared report retains 7/0/1/1 qualified source cards, respectively, and
22/18/8/38 separate lead/unqualified-capture cards. Raw capture counts and displayed
qualified evidence counts intentionally differ. Adidas has two displayed finding
strings referencing the same source, not two independent incidents.

## B. Root causes and code changes

### BrandShield

- [intelligence.py](../../backend/agents/brandshield/intelligence.py)
  `classify_brand_source` / `contextualize_brand_threat` separate suspicious direct
  behavior, allegations, complaints, official/general warnings, historical
  enforcement, background and insufficient evidence. Reporting URLs never become
  actor URLs merely because the article mentions fraud. Source assertions remain
  UNVERIFIED; warning and report records are not active threats.
- [assessment.py](../../backend/agents/brandshield/assessment.py) classifies both
  legacy output paths against original acquired source context, not a shortened
  excerpt. This prevents an enforcement report reverting to a counterfeit-listing
  label after paragraph selection. Duplicate non-threat classifications collapse;
  warnings are retained separately as advisories.
- [PassageExtractor](../../backend/services/research/passage_extractor.py)
  `_brand_context_window` fixes the actual WWD first loss: the subject paragraph
  named Adidas and an illicit operation, while the next paragraph supplied usable
  incident context. A bounded, physically adjacent actual-article span preserves
  both; it cannot borrow a headline, sidebar, unacquired text or unrelated warning.
- [scanning.py](../../backend/agents/brandshield/scanning.py) preserves selected
  offsets; assessment revalidates them against native text before support export.
  [dossier.py](../../backend/agents/brandshield/dossier.py) removes automatic
  takedown recommendations and preserves actor versus reporting-source attribution.

### Trending

- [harvesting.py](../../backend/services/research/harvesting.py) generates concise,
  task-diverse/date-hinted queries; reads undated leads provisionally and prioritizes
  recent observations. Discovery hints are not publication proof.
- [standard_handlers.py](../../backend/infrastructure/acquisition/routing/standard_handlers.py)
  `_execute_feed` no longer allows stale-only Bing results to suppress the existing
  Google fallback. Stale results stay inspectable; undated leads may still be read.
- [search_matching.py](../../backend/infrastructure/acquisition/adapters/web/search_matching.py)
  permits provisional topic overlap only for multi-token general/topic targets.
  In the first live trace, final-strength matching had rejected titles omitting
  “grid” or “scale” before reading. Named person/company matching and final captured
  body/date qualification remain strict.
- [NativeNormalizer](../../backend/services/agent_reach/native/normalizer.py)
  preserves the already observed `url` fallback key as well as `link`; it does not
  invent locators. The first trace contained 64 invalid-locator decisions from that
  shape mismatch.
- [body_context.py](../../backend/services/research/body_context.py),
  [harvest_pipeline.py](../../backend/application/research/harvest_pipeline.py) and
  [synthesis.py](../../backend/application/research/synthesis.py) establish temporal
  requirements **before** reconciliation. A feed date, crawl time, sitemap lastmod
  or editorial update cannot stand in for an observed captured publication date.
  The offline qualification CLI applies the same rule at the original observation
  time.
- [Trending agent](../../backend/agents/trending/agent.py) no longer runs an
  unbudgeted extra headline sweep after empty research or a pipeline exception.
  [clustering.py](../../backend/agents/trending/clustering.py) uses event-specific
  headline context, including same-subject/day financing-angle normalization;
  this is narrative grouping, not proposition equivalence. Source grouping remains
  heuristic, independence unknown, popularity/velocity unmeasured without an
  appropriate time series. No LOW risk is inferred from a small article count.

### Personal Watch and Scout

- [Personal normalization](../../backend/agents/personal_watch/monitoring.py)
  `attribution_metadata` retains allowlisted observed article/selection markers.
  Their loss previously removed quotation attribution between research and the
  complete agent response even though isolated passage tests passed.
- [Personal assessment](../../backend/agents/personal_watch/assessment.py),
  [passage records](../../backend/services/research/passage_records.py) and the
  extractor preserve correct full-name speaker attribution, exact quote/context
  spans and UNVERIFIED status. An explicit related-story tail is excluded from
  the display span, never deleted from the original capture. Missing identity
  abuse is UNASSESSED; initial baseline objects have readable descriptions.
- [Scout assessment](../../backend/agents/scout/assessment.py) and the financial
  extractor prefer subject-bearing financial passages over comparisons to another
  company. Forecasts/mixed context are unresolved, not bullish conclusions. Native
  source observations retain currencies, period labels, entity/affiliate ambiguity
  and exact offsets. Filing comparison is NOT_PERFORMED when no comparable filing
  assessment took place; different headlines are not established contradictions.

### Shared output and browser

- [ReportBuilder](../../backend/services/report_builder.py) projects recent
  developments, brand source assessments, financial context and reported quotes.
  Rejected acquired text remains inspectable separately from qualified evidence;
  it is no longer described as necessarily unread. Empty Trending reports explain
  the 48-hour/date/read-failure limitation. Native `event_description` is preserved
  instead of appearing as “Unknown”. Recommended actions require evidence review,
  not an automatic accusation or takedown.
- [Renderer](../../frontend/unified-report-renderer.js) preserves exact source
  IDs/URLs, displays attributed/unassessed states, and uses readable expandable
  financial context. Observed timeline timestamps sort chronologically; unknown
  timing stays unverified. This was a correctness/readability change, not redesign.

## C. Genuine source examples

Dates are publisher declarations, not authenticated event dates. Bodies are
bounded retained captures. No article URL below was manually supplied to make
autonomous discovery pass.

| Source | Observed publication | Retained words / interpretation |
| --- | --- | --- |
| [WWD / Sourcing Journal](https://wwd.com/sourcing-journal/industry-news/los-angeles-california-counterfeit-bust-nike-adidas-streetwear-1239180559/) | 2026-09-02T12:51:10+00:00 | 1,092; reported counterfeit seizure/enforcement, not WWD as seller/attacker |
| [Yahoo Finance market-outlook article](https://finance.yahoo.com/energy/articles/grid-scale-stationary-battery-storage-083900047.html) | 2026-09-25T08:39:00Z | 1,469 in post-fix check; too old for current Trending evidence |
| [Hindustan Times source-attributed quotation](https://www.hindustantimes.com/lifestyle/art-culture/quote-of-the-day-by-sundar-pichai-i-am-optimistic-not-because-i-believe-in-technology-but-because-i-believe-in-people-101781005535173.html) | 2026-06-10T07:05:34+05:30 | 783 in qualified record; quote span 991–1076, contextual span 926–1258; attribution UNVERIFIED |
| [Korea Times Samsung reporting](https://www.koreatimes.co.kr/business/companies/20261008/samsung-electronics-1st-korean-firm-to-top-80-bil-in-quarterly-operating-profit) | 2026-10-07T22:55:03Z | 765; Samsung estimate selected instead of the unrelated Aramco comparison |

Saved Apple guidance (629 substantive words) remains an OFFICIAL_WARNING with no
active threat; Adidas's earlier five product/lifestyle captures remain background.
The old 240-word DOJ “positive” capture is navigation, **not** enforcement-body
proof. It was rejected as a positive control. No missing text was fabricated.

## D. Before/after and live-request accounting

| Observation | URLs | Reads | Article bodies / words | Qualified current/task sources | Elapsed |
| --- | ---: | ---: | ---: | ---: | ---: |
| Prior Adidas checkpoint | Product/lifestyle material; API packaging error | See prior report | 5 page captures / 2,950 words, not verified body metadata | Not accepted | Prior measurement |
| This cycle Adidas live | 9 | 6 | 1 / 1,092 | 0 before adjacent-passage correction | 38.85s |
| Same Adidas text, corrected full API/SSE replay | Same 9; no fresh discovery | Original observations replayed | Same 1 / 1,092 | 1 / 79 useful words, historical enforcement | Offline processing, not live latency |
| First Trending live | 3 | 3 | 1 / 1,472 | 0 | 22.17s |
| Separately authorized post-fix Trending live | 18 | 9 | 1 / 1,469 | 0 | 29.43s |

Both live batches retained stable application fingerprints within their own runs;
later offline changes are not relabeled as part of those live versions. All three
investigations used AI disabled. No audit-level retry or paid model/key probe.
The conditional extra Microsoft check was **not run**: Adidas yielded genuine
incident content, so its condition did not apply. No unused old budget was reused.

The first Trending trace had 54 provider observations, 34 response-received
observations and 264 result decisions: 190 subject mismatches and 64 invalid
locators. Offline correction admitted 30 additional provisional observations over
nine unique locators, not nine acquired articles. The new live check then discovered
18 candidates, including recent-looking feed entries. **Fresh article acquisition
still failed at publisher resolution/read access**, not the total deadline.

Post-fix Trending used 75 native HTTP admissions, below 120; no deadline exhausted.
Three opaque wrapper resolutions failed. Observed Energy-Storage.News and
StreetInsider hubs returned HTTP 403; another read failed with a 200 response.
The three successful captures were stale/undated and did not qualify. Several
other fresh-looking feed leads were not read under the bounded wrapper-selection
policy. This does not prove all sources inaccessible or no new developments exist.
No CAPTCHA, paywall, approval or SSRF restriction was bypassed.

## E. Browser validation

The current agent routes first processed hash-validated genuine source bytes in
isolated ASGI requests. Only acquisition was replaced; qualification, passages,
specialist logic, API and SSE serialization ran normally. Then saved SSE traversed
the real page buttons, stream consumer and native/shared renderers in Chromium.
Readiness was an explicit harness stub; other backend calls/external browser
resources were blocked. This is **offline source-backed browser replay**, not fresh
browser-to-provider acquisition, production parity or deployed health proof.

Four cases × 320/390/1440px = 12 final states. Each stream contained 20 actual
offline-processing progress events and one result, no errors. The unmodified
progress renderer was observed through 25 update calls per page: loading button
disabled state observed, reported/rendered step values and maxima match, and the
button returns to enabled. Replay does not establish original network timing/ETA.

Native/DOM acquired-card counts, source IDs, titles, URLs, inspection text hashes
and passage previews agree. All nine finding-reference observations resolve to
retained source records; this is join validity, not entailment. Lead cards stay
separate. Keyboard Enter opens the available captured-source inspections (nine
viewport checks); Trending has no qualified source inspection, correctly N/A.
No uncaught exceptions or detected document-width overflow. Fonts were deliberately
blocked and their resource errors retained separately, not called resolved.
Nine resource-console entries include blocked fonts, two HTTP404 and three HTTP503
entries; individual HTTP404 resources were not mapped or declared resolved.

Mobile and desktop intelligence screenshots were actually inspected. A long raw
enum-heavy financial panel was made readable/expandable; Personal's lost timeline
description was corrected. Exact captures remain in the new temporary run; selected
proof and screenshots are linked from the evidence index below. Manual screen
reader, measured contrast/WCAG, axe, Safari/Firefox and hardware-mobile acceptance
remain UNVERIFIED.

## F. Validation

Final command results and selected proof are recorded in
[the evidence index](evidence/2026-10-20_four_agent_completion/README.md).
Full/fast suites, all nine frontend scripts, fatal lint, frozen verification,
offline smoke and persistence were executed. No hosted CI was triggered.

| Final command / scope | Actual result |
| --- | --- |
| `python -m pytest tests/ -q` | 1,742 passed / 56.23s, exit 0 |
| `python -m pytest tests/unit tests/chaos tests/security -q` | 1,534 passed / 45.20s, exit 0 |
| Fatal flake8 E9/F63/F7/F82 | Zero findings, exit 0 |
| Nine `tests/frontend/test_*.js` Node scripts | Each exit 0 |
| Frozen verifier / protected-path diff | Hashes match; protected paths unchanged |
| Isolated release smoke / persistence | OFFLINE_SMOKE_PASS / OFFLINE_PERSISTENCE_PASS; historical/deployed rollback NOT_VERIFIED |
| Four current source-to-API/SSE replays | Exit 0, exact source identity/body hashes preserved, external/model calls 0 |
| Final Chromium saved-SSE acceptance | Exit 0, stable app bytes, 12 viewport states, no step/card/citation mismatches |

An initial full run failed 10 tests (1,732 passed) and fast run failed seven
(1,527 passed). Seven hash failures were an unnecessary new false temporal flag
on financial legacy records; removing that unrelated mutation restored original
goldens without regenerating fixtures. The calibration evaluator assumed numeric
independence, used an unsupported phishing-positive fixture, and exposed a real
financing-headline grouping gap. It now checks grouping versus unknown independence,
uses explicit **synthetic** captured credential solicitation for its positive
control, and the generic bounded financing-angle correction is tested. A mistaken
test filename collected zero tests; the correctly named suite was then run.
These intermediate failures are retained, not presented as passes.

## G. Remaining limitations and next smallest action

1. **P0 Trending fresh-body acquisition is NOT MET.** Dates/qualification must not
   be weakened. Inspect the already observed fresh publisher/feed locators and
   bounded wrapper/continuation allocation before any new request. Another live
   acquisition needs a new small authorization; the three permissions here are
   consumed. Do not repeat a broad sweep, raise every timeout or treat a feed as a
   body to force acceptance.
2. BrandShield proves autonomous incident-report acquisition and corrected
   historical/warning/background interpretation, not broad active-phishing,
   counterfeit storefront or impersonation accuracy. Direct-positive controls
   are synthetic calibration, not new live confirmed attacker evidence.
3. Personal Watch proves source-attributed text reaches the user, not that the
   person actually spoke it or that identity/media/abuse was independently verified.
4. Scout is a source-backed corporate-news briefing here. Comparative filings,
   financial truth, affiliate scope, periods and currencies need independent review.
5. Independent held-out accuracy, hosted CI, production stack parity, deployed
   rollback and the historical malformed-dossier collection remain unverified.
   The earlier 55-file integrity issue was not silently repaired.

## H. Release recommendation and handoff

**Not ready for a separately authorized merge/deployment verification while the
required fresh Trending acquisition gate remains unmet.** Browser correctness and
passing offline tests do not override that gate. No deployment was attempted.

[Next-agent handoff](../handoffs/2026-10-20_FOUR_AGENT_COMPLETION.md) records commands,
ownership and safe continuation. Raw native/SSE captures, original failures, fresh
isolated dossiers, screenshots and logs remain under the new system-temp basename
`aegis-final-four-agent-f01d3247011f4e2c826da0357a420e4f`; temporary files may expire.
Durable proof excludes full article bodies and secrets. This is an engineering
record, not private reasoning or an invented raw transcript.
