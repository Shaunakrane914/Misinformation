# Four-agent, sixteen-prompt website yield evaluation — October 28, 2026

## Decision

**The requested sixteen investigations were attempted once each. This is not a
sixteen-case research-quality PASS.** We recovered 65 acquisition-backed article-body records
and 62,686 article words from 30 observed article hosts in the accountable cases.
One investigation lost its acquisition pool after a pipeline exception; another
completed research but its original native response was lost by the audit writer.
Those missing measurements remain unknown. Several substantial reports fail the
specific question despite their word count.

Implemented scoped pipeline, qualification, routing, audit and frontend repairs.
The strongest demonstrated gains are fewer false findings, correct requested
time windows, recoverable instrumentation and easier access to existing evidence.
There is no claimed 20× useful-evidence improvement, independent accuracy score,
new deployment or successful reproduction of every requested primary disclosure.

## Versions, authorization and preservation

Implementation: `.scratch/deployment-20261028`, branch
`fix/personal-evidence-20261028`, HEAD
`8b5a9a55a8df030ccb86ccbd1f99be959e6885d7`, plus preserved dirty work.
Recorded `origin/main` is the same SHA; its application baseline is
`ec5bef19ff701d62fc10546a4a9bcc7b569f95f8`. No remote fetch or new deployment
inspection was performed; these are recorded Git references, not fresh hosting
attestation. The earlier [reconciliation](OCT28_RELEASE_RECONCILIATION_AND_BENCHMARK_AUDIT.md)
and [production baseline](DEPLOYED_FOUR_AGENT_WORD_YIELD_2026-10-28.md) remain separate.

Original root: `feat/phase8-real-acquisition-proof` / `222a4ad` with preserved
uncommitted changes. Older remediation: `release/specialist-task-20261024` /
`7ad13a5`, also dirty. Neither tree replaced this implementation. The
[workspace snapshots](evidence/2026-10-28_16prompt_yield/implementation-before.json)
and [final state](evidence/2026-10-28_16prompt_yield/implementation-state.json)
identify the actual checkout and inventories. No commit, push, merge, deployment,
secret change, paid reader, protected dossier rewrite or frozen-data change.

The user authorized sixteen local cases, once each, at **240 seconds, 24 deep
reads and 120 native HTTP admissions per case**, with a four-agent pilot first.
The user separately requested enabling AI. Existing bounded Gemini query advice
was therefore enabled; report synthesis/evidence advice and paid readers remained
disabled. There were no investigation retries or extra source sweeps.

Application fingerprints, not just HEAD:

| Scope | Backend/frontend SHA-256 |
| --- | --- |
| S1/B1/T1/P1 pilot | `ee16620e1175ed1f7f03b3d11549368061cc74a5911b9d451e9c370bed0c1f1d` |
| Remaining twelve investigations, after first offline repairs | `22ae91c59257336e8a37db01f51520a1871aa8c412f83a3ef99105e82545b89b` |
| Final local application, including later offline qualification/UI repairs | `9d1c37f6dee03b38126d6075880724ad01f89a504b3cdb08a22aadafce87d52d` |

Each live process reported stable application bytes. Final offline corrections
must not be described as freshly retested acquisition. Cache state was shared
within a process and differed across waves; latency is not a paired performance
benchmark. Private captures used new temporary SQLite/dossier paths without app
lifespan ingestion, notifications or production persistence.

## Definitions and trustworthy accounting

The [URL ledger](evidence/2026-10-28_16prompt_yield/website_word_yield.json)
and [CSV](evidence/2026-10-28_16prompt_yield/website_word_yield.csv) contain
**2,067 rows**: 544 retained source records, 696 rejected search leads and 827
otherwise unassigned transport observations. Discovery/transport rows are
explicitly different from article records; a successful search/index download
is not an acquired article. Wrapper/search hosts are not relabeled as publishers.

- A word is a whitespace-delimited occurrence, not a distinct vocabulary token.
- Article words require an acquisition-backed `ARTICLE_BODY` capture. Partial
  bodies retain depth/truncation observations; the count does not mean complete
  remote coverage or that every captured word is useful.
  The raw count uses retained structural classifications; it is not a claim
  that an independent reviewer checked every paragraph in all 65 records.
- Structural body words, whole qualified-body volume, selected exact passages,
  published passages and older background have separate fields. Whole qualified
  bodies are **not** all asserted to be relevant words.
- “Qualified” means the existing automated gates accepted the record. Sample
  review below identifies off-task material that survived those gates. It is not
  an independent human relevance/accuracy label.
- Passage accounting validates source identity, body SHA-256 and exact offsets.
  Text/span deduplication also applies across cases and source copies. Citation
  identity is not entailment, authenticity or independent corroboration.
- Native admissions include admitted retries/redirects and can fail before a
  socket opens. They are not provider receipts, paid quota use or complete
  accounting of every external SDK. Reading lookups remain separate transport
  rows when attribution to an article is not observed; no cost is prorated to
  manufacture per-article efficiency.
- Host-level word/admission rankings exclude shared discovery costs and any
  unassigned lookup cost. They are not end-to-end acquisition efficiency.
  Observed reader endpoints are matched to their source capture, while actual
  admission hosts remain explicit; a reader/mirror is not renamed as publisher.
- Missing observations are null. T2 retains body-level counts and a dossier
  read total, but its original per-URL read durations/backends and frontend
  projection were not saved. They are not invented from one-body/one-read guesses.

[Website totals](evidence/2026-10-28_16prompt_yield/website_totals.csv),
[agent/website totals](evidence/2026-10-28_16prompt_yield/agent_website_totals.csv),
[rankings](evidence/2026-10-28_16prompt_yield/website_rankings.json) and
[case/agent summary](evidence/2026-10-28_16prompt_yield/agent_word_yield_summary.json)
provide the complete website list, original/final locators, dates, acquisition
times, permissions where retained, errors, body hashes, stage counts and yields.
Website contributions can overlap; use the explicit cross-case/global union
metrics instead of summing repeated publisher text. No unrecorded source family
or permission approval is inferred.

## Actual sixteen-case outcomes

The complete [prompts](evidence/2026-10-28_16prompt_yield/prompts.json) preserve
the user's text. “Published” below is the original saved report's all-pages
workbench collection, not all text physically above the fold. “Older” is separate.

| ID / subject | Bodies | Raw article words | Qualified sources | Published / older words | Reads / native admissions | Seconds |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| S1 NVIDIA | 8 | 14,919 | 7 | 5,685 / 0 | 24 / 70 | 86.39 |
| S2 Tata Motors | 1 | 672 | 1 | 282 / 0 | 10 / 72 | 117.82 |
| S3 Apple | 7 | 10,876 | 6 | 2,388 / 0 | 24 / 80 | 102.94 |
| S4 Infosys | 2 | 907 | 2 | 294 / 0 | 15 / 71 | 105.53 |
| B1 Nike | 7 | 6,628 | 2 | 126 / 0 | 14 / 72 | 116.77 |
| B2 Dyson | 0 | 0 | 0 | 0 / 0 | 3 / 65 | 100.90 |
| B3 Pfizer | 2 | 1,024 | 2 | 240 / 0 | 14 / 89 | 134.35 |
| B4 Apple | 0 | 0 | 0 | 0 / 0 | 16 / 81 | 184.26 |
| T1 battery recycling | Unknown | Unknown | Unknown | 0 / 0 | Unknown / 86 | 149.82 |
| T2 Shah Rukh Khan | 12 | 7,682 | 2 | Unknown / unknown | 23 / 85 | 167.71* |
| T3 Indian semiconductor manufacturing | 5 | 4,205 | 0 | 0 / 1,074 | 16 / 71 | 125.65 |
| T4 Virat Kohli | 5 | 3,061 | 1 | 132 / 432 | 24 / 80 | 114.31 |
| P1 Tim Cook | 7 | 5,626 | 5 | 334 / 0 | 17 / 78 | 99.75 |
| P2 Sam Altman | 9 | 7,086 | 8 | 1,111 / 0 | 24 / 96 | 123.26 |
| P3 Mary Barra | 0 | 0 | 0 | 0 / 0 | 11 / 80 | 124.63 |
| P4 Shah Rukh Khan | 0 | 0 | 0 | 0 / 0 | 21 / 83 | 197.00 |

*T2 latency is the saved application SSE completion log, not a recovered runner
measurement. Its sealed dossier records 23 attempts; its source pool survives.
The original native/frontend response does not. T1 really displayed an explicit
acquisition failure; that zero displayed output does not establish zero reads or
bodies. Overall there were **1,259 observed native admissions**. Observed cases
remained within their authorized caps; do not assert a verified T1 read total.

All sixteen normal requests were issued. Fifteen native responses were saved,
including T1's explicit failure. T2 completed its engine sequence but the runner
failed while exporting response metadata. The failed process was stopped;
subsequent runs contained only previously unrun IDs. It is not represented as
one successful sixteen-case runner invocation.

## Where useful information was lost, and whether the output is enough

This is agent review of titles, dates and selected passages, not an independent
claim-accuracy adjudication. The exact website rows retain the underlying detail.

| Case | First observed loss / question gap | Sufficiency |
| --- | --- | --- |
| S1 | Article retrieval works. The pilot promoted research instructions into findings. Financial assertions and forecasts survive, but original issuer/period agreement is not established. | Substantial reading material; partial financial answer, not verified latest figures. |
| S2 | The sole article describes a 2025 scheduled results meeting. Source selection does not supply the requested latest reported performance. | 282 words do not close the financial question. |
| S3 | Seven bodies include a third-party filing mirror and commentary. No demonstrated original-disclosure/period/currency reconciliation. | Substantial relevant context; primary adjudication remains missing. |
| S4 | Retained articles are dated 2010 and 2025. Qualification permits background despite the “most recent results” objective. | Not enough current financial evidence, regardless of 294 words. |
| B1 | Bodies exist. A fashion description qualified because `recalling` matched `recall`. Actual counterfeit reporting remains after correction. | One limited incident brief; no established current active campaign or independent corroboration. |
| B2 | Three selected leads: unresolved publisher, denied read and an FTC discovery index. No article body. | Retrieval failure/gap; not evidence that Dyson has no public information. |
| B3 | Two reports discuss the same alleged counterfeit-drug investigation and quoted officials. Original manufacturer/regulator notice is absent. | Useful bounded allegation reporting, not a verified manufacturer finding or two independent cases. |
| B4 | Article acquisition fails: unresolved wrappers, denials, provider/budget failures; retained successful captures are indexes/landing material. | Not enough evidence about specific fake-support/phishing campaigns. |
| T1 | Progress reaches passage analysis, then a `ValueError` aborts before synthesis. Duplicate-owner/read-order disagreement reproduces an exception at that boundary offline. | Failed. The original stack/pool is missing, so exact live trigger remains unproved. |
| T2 | Acquisition and body qualification succeed; the **audit writer**, not the scraper, loses the original response on UTF-16 surrogate metadata. | Two current source reports survive; offline rendering supplies 239 words. Original live frontend yield remains unknown. |
| T3 | Five bodies are outside the requested seven-day window. Fresh discovery is the gap; the date gate correctly rejects them as current. | No current answer; 1,074 separately labeled older words provide background. |
| T4 | One fresh report concerns a newly reported retrospective about a 2017 conversation. Other retained material is older. | A narrow recent public report plus 432 older words; not a new 2017 event, official confirmation or measured virality. |
| P1 | Five relevant records provide reported statements, including historical interviews. The pilot also treated instructions as findings. | 334 useful-context words, with visible dates; not proof these are the most recent original/authenticated statements. |
| P2 | Plural “misattributed statements” missed FALSE_QUOTE routing and admitted ordinary interviews. A hypothetical plural “zero scams” quotation also became a scam signal. | Much of 1,111 words misses the exact deception task. Corrected risk abstains; no identified specific impersonation evidence is established. |
| P3 | Eleven reads retain discovery/index/landing material, no article body. Publisher resolution and eligible body discovery fail before statement qualification. | Not enough evidence. |
| P4 | Twenty-one attempts still yield no article body; wrapper/access/transport losses precede exact-claim assessment. | Not enough evidence; not a clean bill of health or absence claim. |

For T2 the observed acquired publisher is **bdnews24.com**, not Google News.
Two eligible captures declare October 27–28 publication dates: a film-poster
report and birthday/fan-meeting reporting. Those are genuine captured publisher
bodies discovered by the normal query. No URL was supplied. Their offline
projection is not silently substituted for the missing original response.

## Website-level findings

The machine-readable rankings answer “which websites” for every case, including
unsuccessful reads and permission/transport outcomes. The following highlights
are **diagnostic counts**, not recommendations that the highest-yield site is
trustworthy or task-sufficient.

| Agent | Actual body suppliers / significant observations | Published-word diagnosis |
| --- | --- | --- |
| Scout | Insider Monkey supplies 9,490 raw words; other bodies include CNBC, Motley Fool, Note, StockTitan, Blockonomi, News18, CIOL and Fortune India. | Note 2,102, Motley Fool 1,429 and CNBC 1,184 cross-case unique published words. High volume does not replace issuer verification. |
| BrandShield | WWD supplies 6,628 raw words; Free Press Journal 439 and CNBC-TV18 585. Dyson/Apple cases supply no article bodies. | Original WWD 126 includes the rejected 47-word fashion paragraph; corrected Nike is 79. Pfizer reporting supplies 111 + 129 words. |
| Trending | Bodies include News18, India TV, bdnews24, CricTracker and Rediff. Search/index providers remain distinct. | Original known current yield is 132 words; older background 1,506. T2 original output is unknown; replayed current yield is 239. |
| Personal Watch | Bodies include Financial Express, Digit, Business Today, Firstpost, Indiatimes, Business Insider, Gujarati Samachar, Marca and other retained reporting. Mary/SRK have no bodies. | Much of the volume is context, not exact identity-deception evidence. No source ranking establishes speaker authenticity. |

Original known cross-case unique published task/current words are Scout **8,098**,
BrandShield **366**, Trending **132** and Personal Watch **1,445**; total **10,041**.
Older background adds **1,506**, separately. These are lower-bound observations
with unknown cases excluded, and automated relevance still contains the defects
identified above. Summing the individual case totals would double-count 551
repeated words. Do not call these numbers independently verified useful words.

## Repairs and identical-capture comparisons

| File / function | Demonstrated issue and correction |
| --- | --- |
| [harvest_pipeline.run_harvest_pipeline](../../backend/application/research/harvest_pipeline.py) | Align exact-body owner ordering with the raw pool before passage deduplication; concurrent completion order must not qualify a different duplicate and abort the report. Pool rejection invariant remains intact. |
| [ClaimIntelligenceEngine.decompose_claims](../../backend/services/research/claim_intelligence.py), [GroundedSynthesisStage.run](../../backend/application/research/synthesis.py) | Do not turn imperative research objectives into atomic factual claims; retain source observations when no actual proposition was supplied. Declarative and quoted claims remain testable. |
| [requested_trending_window](../../backend/services/research/temporal_guard.py), [TrendingAgent.scan](../../backend/agents/trending/agent.py), harvesting/synthesis/background gates | An explicit last/past hours/days request, bounded to one week, reaches query hints and every final gate. Defaults remain 48h. Seven days is the requested scope, not permission to accept missing/future dates. |
| [matches_objective](../../backend/services/research/content_roles.py) | Whole recall forms and explicit product-recalling constructions avoid treating fashion recollection as a product-safety incident. |
| [classify_passage](../../backend/services/research/passage_records.py) | Plural scam/fraud context follows the same mechanism requirement as singular forms; hypothetical “zero scams” is context, not a reported scam. |
| [specialist_planning._PATTERNS](../../backend/services/research/specialist_planning.py) | Plural misattributed quotes/statements select FALSE_QUOTE instead of ordinary PUBLIC_STATEMENT. Fresh post-fix discovery for P2/P4 was not rerun. |
| [ForensicExplorer](../../frontend/forensic-explorer.js), [shared renderer](../../frontend/unified-report-renderer.js), [theme](../../frontend/aegis-theme.css) | Render actual epistemic state, expose a top evidence jump, keep dates/credits visible and make capture IDs/language/offsets expandable. Fixed-header landing is verified. Source text/counts are preserved. |
| [Terminal audit runner](../../scripts/audits/run_terminal_agent_quality.py), [observer](../../scripts/audits/website_yield_observer.py) | Explicit prompt/category manifests; unchanged bounded HTTP calls observed without retries. Preserve partial pools/error frames, save raw SSE before export, and escape Unicode metadata safely. |
| [Website accounting](../../scripts/audits/website_word_yield.py), [desktop audit](../../scripts/audits/measure_desktop_evidence.py) | Explicit article/lead/transport types, unknowns, cross-case deduplication, source hashes/offsets and real browser geometry/pagination. |

| Same saved input | Original → corrected passage words | Actual benefit |
| --- | ---: | --- |
| S1 NVIDIA | 5,685 → 5,685 | Research instructions removed from findings; source observations retained. No new acquisition. |
| B1 Nike | 126 → **79** | One fashion source excluded; genuine incident passage remains. Lower count is correct. |
| P1 Tim Cook | 334 → 334 | Instructions removed from findings; attributed source context retained. |
| P2 Sam Altman | 1,111 → 1,111 | False scam observation 1 → 0; identity risk becomes UNASSESSED. Exact-task discovery remains inadequate. |
| T2 recovered source pool | Original output unknown → 239 in replay | Two retained current articles reach current native/API/SSE and browser processing offline. |

[Replay identity checks](evidence/2026-10-28_16prompt_yield/replay-comparison.json)
preserve source IDs, URLs, titles, publication dates and body hashes. Replays make
zero provider/model calls. They do not establish a new live improvement from the
later keyword/routing/UI repairs. Earlier production Adobe/Dyson/Mary/battery
measurements use different prompts/source sets and are not paired causal baselines.

## Desktop sufficiency, gaps and next work

[Desktop content sufficiency](DESKTOP_FRONTEND_CONTENT_SUFFICIENCY.md) records
all 64 states, per-section geometry/words, first-page versus paginated output,
controlled genuine-passage layout subsets, screenshots and reviewed readability.
The desktop does not require 450–750 evidence words merely to appear occupied.
Nor does passing a soft word target establish task sufficiency.

[Source-gap recommendations](source_gap_recommendations.md) give the prioritized
implementation plan, estimated engineering cost and source-specific acceptance
checks. The main remaining work is exact-task/period-aware source selection and
authoritative source acquisition, particularly Personal Watch and current
financial results. Do not raise every read limit or weaken freshness/access
checks to meet an editorial count.

## AI and verification actually performed

AI was enabled with the configured `gemini-3.5-flash-lite` advisory model. The
shared UTC-day ledger advanced **3 → 8**, consuming **five new reservations**:
two successful generations (**773 provider-reported total tokens**) and three
read timeouts whose token usage is unknown. Four bounded exact-model capability
GETs returned 200. The last wave was budget-blocked before another model lookup.
Its zero scope-local counter is not a reset of the daily ledger. No key/model
rotation, quota probe, budget reset, paid reader or generated evidence/verdict.
[Actual accounting](evidence/2026-10-28_16prompt_yield/ai-accounting.json).

Final checks:

| Scope | Actual result |
| --- | --- |
| Initial HTTP/security observation controls | 14 passed |
| First implementation/source/claim/security subset | 50 passed |
| Later source-role/pipeline/security subset | 104 passed |
| Final new audit regressions | 23 passed |
| Full `python -m pytest tests/ -q` | **2,867 passed / 99.75s**, exit 0 |
| Fast unit/chaos/security | **2,659 passed / 65.80s**, exit 0 |
| Fatal flake8 E9/F63/F7/F82 | Exit 0; zero fatal findings |
| All frontend Node scripts | **11 scripts**, exit 0 each |
| Frozen verifier / protected-path diff / whitespace | Exit 0 |
| Isolated release smoke / persistence | OFFLINE_SMOKE_PASS / OFFLINE_PERSISTENCE_PASS |
| Offline body/API/SSE comparisons | Four native-capture replays plus recovered T2 pool; source identity/hash/date checks pass |
| Final Chromium replay | **64 states**; exact passage/background matching, pagination, detail controls, navigation, no page exceptions or horizontal overflow |

[Final gate evidence](evidence/2026-10-28_16prompt_yield/final-gates.json).
The earlier full/fast run passed 2,865/2,657 before two additional metric/pool
regressions were added. Newly introduced failing controls, the Unicode writer
failure, initial anchor overlap and intermediate audit counters remain in temp
logs; corrected results are separate. No remote CI was run. The historical
archive's previously recorded 55 malformed dossiers remain untouched; isolated
persistence is not historical recovery or deployed rollback verification.

Private native responses, complete source pools and raw logs remain under the
system-temp basename `aegis-16prompt-20261028-wycljnqk`; temporary storage may
expire. Durable deliverables retain permitted metadata/counts/hashes rather than
republishing whole publisher bodies. The [capture manifest](evidence/2026-10-28_16prompt_yield/capture-manifest.json)
locates and hashes the available private originals and explicitly identifies T2's
missing native response. No absent body, permission, citation or benchmark success
is inferred from an HTTP 200.
