# Expansion four-case live retest — 2026-10-24

## Result

**Live research acceptance remains PARTIAL; 20× useful-evidence growth is not
demonstrated.** Four newly authorized local investigations ran once each, with
AI disabled. Scout and BrandShield produced qualified source assertions.
Trending and Personal Watch returned INSUFFICIENT_EVIDENCE with zero published
passages. Successful HTTP200/result events do not make those two research successes.

The run used `release/specialist-task-20261024`, HEAD
`1a90d681361b8e027a12feb88266932a5cb5d1d1` plus preserved dirty work. Application
fingerprint remained `d6916d41e5716e178d56a31cb5c642bf4f66f152452c3d376e665b3bd74a449e` throughout the live batch.
One later offline-only passage correction is described separately below.

No deployment, paid readers, notification/background jobs, production writes,
audit-level retries or additional model/capability probes. **Zero AI reservations.**
All four permissions are now consumed. New temporary SQLite/dossiers were used;
historical dossiers and frozen benchmarks remain unchanged.

[Sanitized measurements and accounting](evidence/2026-10-24_expansion_live_retest/measurements.json)

## Actual discovery-to-publication funnel

Raw words/KB count structurally classified acquired article/document bodies,
not profiles, search cards, all downloaded bytes or guaranteed useful text.
Qualified sources and published passages are code-selected source assertions,
not independently verified facts or independent publishers.

| Case | Seconds | Candidate URLs | Read attempts | Article bodies | Raw words / UTF-8 KB | Qualified sources | Published passages / selected words | Native HTTP admissions |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Scout / Adobe |40.24|45|24|14|16,254 /113.013|13|117 /6,484|80|
| BrandShield / Dyson |25.97|30|15|8|7,656 /46.262|4|15 /774|82|
| Trending / battery recycling |52.19|51|21|8|9,596 /68.421|0|0 /0|88|
| Personal Watch / Mary Barra |24.38|18|7|1|484 /3.009|0|0 /0|74|

Each case generated18 main queries. Bounds were240 seconds,24 deep-reader attempts,
120 native HTTP admissions per case; observations stayed below or at those limits.
Admissions include normal native redirects/retries and reservations that can fail
before connection. The system reports `complete_network_accounting=false`:
these are not a claim of total sockets, billed requests or total network traffic.
There were no audit-level POST retries. Exactly four local POST investigations ran.

The four response envelopes contain13/4/0/0 native source records. Their legacy
record-word metric is15,855/1,653/0/0; it differs from the full raw-pool body metric
above. Neither should be silently substituted for selected frontend words.

## Comparison with the preceding authorized sample

This is an observational comparison with the prior batch, not a simultaneous
controlled before/after trial. Source availability and provider ranking can vary.

| Case | Prior → new raw article words | Prior → new selected frontend words | Interpretation |
| --- | ---: | ---: | --- |
| Adobe |17,104 →16,254|6,948 →6,484|Useful source acquisition persists; no observed volume gain |
| Dyson |9,089 →7,656|792 →774|Relevant incident reporting persists; no observed volume gain |
| battery recycling |12,280 →9,596|0 →0|Acquisition occurs, but live publication still fails |
| Mary Barra |484 →484|0 →0|No improvement in usable specialist evidence |

Zero baselines are not treated as infinite growth. The new expansion route did
not establish a broad recall or20× result.

## What the new adapter route actually did

| Planned route | Observed outcome |
| --- | --- |
| `yahoo_finance|Adobe` | Provider started;3 discovery records; one independently read URL survived qualification and publication |
| `news_wires|Dyson` | Provider started; successful query lifecycle but zero matching records; no new acquired source from this route |
| `bluesky|Battery Recycling` | Explicit FAILED query: expanded discovery providers failed; no acquired evidence |
| `substack|Mary Barra` | Provider started; successful query lifecycle but zero matching records |

The Yahoo contribution is traceable from query `hv_q_017` to canonical source
`ev_hv_046482bd51ae2588b5fc`, actual acquired content and publication:
[observed Yahoo article](https://finance.yahoo.com/markets/stocks/articles/adobe-systems-adbe-dips-more-204501496.html).
The other three routes did not add a qualified source. Registration is not
sufficient evidence that all expanded websites are productive.

## First useful-source losses and actual relevance

**Adobe:** discovery and acquisition succeeded.24 reads reached the allowed
attempt ceiling, leaving20 eligible candidates unread. Recorded failures were
four ACCESS_DENIED, three PUBLISHER_UNRESOLVED and one PROVIDER_FAILURE.
The workbench contains29 financial-statement,23 historical,17 article-context
and48 forecast/mixed-context paragraphs. Preserve those distinctions: this is
not117 confirmed current financial facts, a primary-filings assessment or a
validated claim-verdict evaluation.

**Dyson:** source text concerns reported counterfeit products, a reported legal
complaint, a recall report and attributed brand statements. The shared report
labels allegations and historical enforcement separately; the reporting URL
is not an attacker endpoint. Four sources contribute15 passages:11 unverified
allegations, one safety report, one reported enforcement and two source-context
passages. These are relevant research leads/assertions, not independent proof
of an active seller, current threat prevalence or authenticated counterfeit.
Fifteen further wrapper leads were left under the wrapper-read bound.

**Trending:** this is not simply inability to download text. Eight article
bodies were acquired. Two long IndexBox bodies were stale; several energy-storage
articles did not match recycling; additional catalogue/hub captures were not
articles. Critically, one fresh374-word article passed structural/body relevance
but was lost at passage extraction with `NO_RELEVANT_PASSAGE`:
[observed ESS News article](https://www.ess-news.com/2026/10/23/swedish-industry-seeks-battery-recycling-checks-for-grid-service-access/).
Its captured publication declaration is2026-10-23T11:15:00Z, inside48 hours at
the recorded run. Exact body paragraphs discuss recycling of batteries.
That is a confirmed downstream selection defect, not a legitimate freshness
abstention. Provider/access/host-bound failures also limited breadth; preserving
the security and freshness bounds remains necessary.

**Personal Watch:** discovery produced leads, but only three body-like captures:
a1,143-word Economic Times page without an accepted structural article marker,
a484-word2021 Business Roundtable appointment article without a usable requested
specialist passage, and a2,513-word publisher homepage without the target.
Ten wrapper leads remained unread; three publisher-resolution failures and one
access denial were recorded. Zero source-backed identity-threat or attributed
statement conclusions were justified. The unclassified page is a concrete
extraction follow-up; no claim that it lacks all useful text or that the person
has no public information is made.

## Offline correction after the measured batch

The existing paragraph selector compared topic tokens literally:
`battery` did not match `batteries` inside the paragraph containing
`recycling`. Generic request profiles use `general`, not always `topic`;
the repair covers the same topic-like profile classes as the existing entity
relevance gate.

[PassageExtractor.extract_passages](../../.scratch/phase9-remediation-20261016/backend/services/research/passage_extractor.py)
now normalizes conservative regular consonant-`ies` plurals **only** for
Trending topic/general/concept/product token matching. Named identity matching,
overlap thresholds, date/depth checks, source bytes and exact passage offsets
are preserved. No URL, subject, article body or event was hardcoded into production.

[Eight regressions](../../.scratch/phase9-remediation-20261016/tests/unit/test_topic_plural_passages.py) cover
battery/recycling, municipal policies, industry regulations, the real generic
request classifier, unrelated topics, ineligible dates, index snippets and person
names. Two initial positive controls failed before the correction. The first
topic-only version did not repair the genuine generic-profile replay; that scope
was corrected and the real classifier path is now tested.

The **same captured pool and fixed reference time** were requalified offline:
0 →1 qualified source, with one exact56-word passage, offsets428–811.
Input SHA and original-pool SHA match before/after. Other stale, unrelated and
unstructured captures remain rejected. No new requests, model calls, dossiers,
verdicts or frontend report were generated by that requalification.

This is **replay proof of corrected selection**, not a new live Trending pass or
a corrected native report/browser acceptance. The measured live table remains
unchanged. No fifth investigation was performed.

## Browser and regression checks

The four exact fresh API reports were replayed through the actual shared renderer
on their native pages at320/390/1440px:12 states passed passage pagination,
keyboard access, filters, overflow and uncaught-exception checks. All published
passage spans matched the retained source bodies. Scout and Trending mobile
workbench screenshots were visually inspected. These are saved-report render
checks with external browser traffic blocked, not new form submission, a complete
manual visual audit or accessibility certification. The offline-corrected Trending
passage was not substituted into the captured live report.

After the offline correction:

| Gate | Actual outcome |
| --- | --- |
| Full Python suite | exit0;2,300 passed /51.62s |
| Fast unit/chaos/security | exit0;2,092 passed /38.29s |
| Fatal flake8 | exit0; zero fatal findings |
| All ten Node frontend scripts | exit0 each |
| Release smoke, new temp report | exit0; OFFLINE_SMOKE_PASS |
| Release rollback validator, new temp report | exit0; OFFLINE_PERSISTENCE_PASS; empty archive NOT_VERIFIED |
| Frozen verifier and protected Git diff | exit0; unchanged |
| Four-case live runner | exit0; transport completion only; two research cases remain insufficient |
| Fixed-time offline requalification | exit0; one exact source passage; no new network/model calls |

The original protected55 malformed dossiers were not recovered or overwritten.
The original checkout application code was not modified during this continuation;
its preceding test snapshot is not relabeled as a fresh rerun.

## Next focused work

The useful next targets are current relevant-publisher discovery and passage
preservation, not larger buffers. Verify the narrow Trending correction through
a separately authorized live budget if needed, and investigate the saved Personal
Watch page's structural extraction before another live request. Improve diversity
when hub expansion spends a host's entire read allowance on tangential articles.
Do not relax freshness/identity/access checks or fill empty reports with profiles.

[Continuation handoff](../handoffs/2026-10-24_EXPANSION_LIVE_RETEST.md)
