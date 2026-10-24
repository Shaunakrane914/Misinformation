# Acquisition reliability and evidence selection repair — 2026-10-22

## Scope and acceptance

Implementation continuation from the [October 21 twelve-case audit](TWELVE_PROMPT_WORD_YIELD_AND_RELEVANCE_2026-10-21.md).
Worktree `.scratch/phase9-remediation-20261016`, branch
`fix/p0-lenovo-acquisition-20261018`, base HEAD
`39a514b68388450bbc5e6061aba97bda2077fc7f`, with substantial inherited uncommitted
work preserved. No commit, push, merge, deployment, credential/access change,
historical dossier rewrite or frozen benchmark update.

**Targeted repairs verified; overall research/release acceptance remains PARTIAL.**
Fresh Apple acquisition recovered. Tim Cook's already-acquired incident text now
survives corrected offline processing. Final code has not been freshly reacquired
or deployed. Closeout is dated October 23; original live observations below are
preserved separately. Passing regressions/replay are not broad live acceptance.
The expanded QUICK/STANDARD/DEEP harvester, raw pool, observed feed/publisher
continuation, strict second-layer gates and canonical source identities remain.

## Transport: proven mechanisms versus incident uncertainty

The saved Apple BrandShield batch recorded DNS `getaddrinfo`/Windows 11001 errors
under SSRF-layer access failures. This proves a lookup failed, not that a public
publisher resolved to a forbidden/private address. The later empty investigations
do not alone identify whether host networking, resolver saturation or upstream
provider failures caused them.

Code inspection and deterministic fault injection found mechanisms that could
amplify a failure across sequential requests:

- Resolver errors were negatively cached for 60 seconds and surfaced as security
  rejections. The repair uses a brief one-second failure cache and explicit
  DNS error/timeout/capacity categories; genuine private/mixed/reserved address
  answers still fail closed. Positive cache hits never authorize a hostname
  connection: fresh validated numeric-address pinning remains mandatory.
- A failed URL could mark the entire `web.read` operation unavailable. Explicit
  destination-scoped failures no longer suppress unrelated publisher reads.
  Provider throttling, authentication and policy restrictions remain enforced.
- Review found a late in-flight DNS failure could overwrite a 429 observation.
  An independent original-expiry rate-limit fence now survives later outcomes.
- A socket timeout could be reused after TCP connection/TLS consumed the budget.
  The repair carries one original deadline through DNS, connection, TLS and body
  reads rather than granting each stage a new full allowance.

Only OS-declared transient DNS errors (`EAI_AGAIN`/Windows 11002) receive one
bounded lookup retry inside the original deadline. Windows 11001/NXDOMAIN,
private-IP answers, 403, authentication and challenges are not recovery signals.
No resolver/proxy/provider proliferation, CAPTCHA/paywall bypass or unbounded
retry was introduced. An OS DNS call already running in a daemon thread cannot
be force-cancelled; the eight-slot bound prevents unlimited outstanding lookups.

These are reproducible code mechanisms, **not a proven complete causal account
of the historical host outage**. Fresh DNS/transport observations must be read
separately from fresh article acquisition outcomes.

## Layer 2 implementation

- `PassageExtractor.extract_passages()` ranks exact current-event lead paragraphs
  above keyword/number-rich historical background. It chooses complete paragraphs,
  preserves negations and source bytes, and retains character offsets.
- `trend_context.classify_source_context()` labels competitive context separately
  and rejects former-affiliation-only interviews as target developments. This is
  a disclosed lexical role heuristic, not proposition entailment or identity
  authentication. Direct-topic evidence precedes competitive context before the
  shared six-finding cap.
- Trending, shared reporting and the renderer retain competitive captures but
  display them under competitive context. An otherwise empty primary-topic set
  is explicitly described as competitive-context-only, not direct coverage.
- Financial context retains exact period/currency labels and reported/forecast
  sentence spans. Publication recency is a disclosed 366-day display policy,
  not fiscal-period reconciliation. Old captures remain inspectable background;
  default current findings do not combine historical guidance with new results.
- Corporate branding/strategy remains context, not financial verification.
  Filing comparison remains `NOT_PERFORMED`. Unknown dates/currencies/issuer
  alignment are not invented or normalized into certainty.
- Raw-pool reconstruction preserves recorded observation clocks; reprocessing
  must not silently advance acquisition time to the replay date.

## Evidence and verification

See the [new evidence index](evidence/2026-10-22_reliability_selection/README.md).

### Genuine saved-body before/after

The [machine-readable comparison](evidence/2026-10-22_reliability_selection/passage-comparison.json)
checks original raw article IDs, URLs and body hashes plus selected character
offsets. All five inventories remain intact. These are reprocessed October 21
captures, not fresh searches or independent truth judgments.

| Case | Before | After | What this establishes |
| --- | --- | --- | --- |
| Tata Motors / Scout | One 1,186-word article; selected 689-word branding block | Complete 209-word event lead; `CORPORATE_STRATEGY_CONTEXT`, no financial catalyst | More concise, correctly bounded context, not financial verification |
| Infosys / Scout | Three articles / 2,845 retained words, mixing 2010, 2025 and 2026 | All bodies retained; one current native finding; old items explicitly historical | Publication/period separation, not reconciled fiscal accounts |
| Apple / Scout | Six sources / 6,001 words; 323 selected words | Same six bodies and 323 selected words; exact periods/currencies and unknowns disclosed | Context safeguards improved; no word-yield or selection gain claimed here |
| NVIDIA / Trending | TorchTPU/TorchNeuron selections emphasize historical background (100/78 words); 84-word incidental VC interview selection | Exact announcement leads (49/60 words); former-affiliation-only story excluded from findings, body preserved | Two competitive developments, **zero direct NVIDIA announcements**, no measured virality |
| OpenAI / Trending | 89-word DeepSeek passage presented among target developments | Same exact passage, explicitly competitive context; no direct target development | Attribution/context corrected, not additional acquisition |

Infosys title labels such as Q4FY26/FY27 are not substituted for a captured
Q3FY26 paragraph. Historical forecasts and current reported figures remain
separate. Bare `Rs`/`$` labels are not silently assigned a currency; explicit
currency codes do not authenticate issuer identity. All filing comparison remains
`NOT_PERFORMED`, fiscal alignment `NOT_RECONCILED`, source assertions unverified.

### Four-agent boundaries

- **Scout:** genuine-source period/context and concise-lead regressions pass.
  Apple selection is unchanged; claim adjudication and financial filing matching
  are not independently accepted.
- **Trending:** genuine-source event selection and competitive-context projection
  pass. Topic/source role remains a lexical heuristic; accuracy, chronology and
  virality are not established by these samples.
- **BrandShield:** the older genuine Adidas enforcement capture remains a
  source-reported allegation/enforcement observation, not a confirmed attacker.
  Replaying the failed Apple capture remains `ACQUISITION_FAILED`; no body is
  invented to turn it into success.
- **Personal Watch:** the older Pichai quotation remains source-attributed public
  speech, not authenticated identity or proof of an identity threat. Replaying
  the failed Tim Cook capture remains `ACQUISITION_FAILED`.

### Read-only network observations

Four public host DNS lookups returned address records on October 22 (Bing,
Google News, TechCrunch and Help Net Security). Two bounded, one-attempt robots
GETs through the actual safe transport then returned mixed results: Bing HTTP
200 / 2,676 bytes / 0.771s, Help Net Security no observed HTTP response /
`BUDGET_EXHAUSTED` / 5.009s. Each GET was capped at five seconds and 64 KiB,
with no redirect or retry. These are transport probes, **not article acquisition
or proof that host networking has fully recovered**. They do not explain the
earlier outage retrospectively.

The user separately authorized exactly one Apple/BrandShield and one Tim
Cook/Personal Watch investigation, AI disabled, each bounded to 180 seconds,
16 reader attempts and 80 native HTTP admissions. Their fresh results and final
command outcomes are recorded at closeout; no other live investigation or model
request is authorized by this report.

### Implementation map

| File/function | Responsibility |
| --- | --- |
| `security/url_validator.py::resolve_public_addresses`, `validation_failure_kind` | Bounded DNS taxonomy/recovery, public-address checks retained |
| `network/http.py::_fetch_public_http`, pinned connection classes | One transport deadline, safe numeric-address connection, observed rate-limit status |
| `native/operation_capabilities.py::record_observation`, `assess` | Destination-scoped failures and original-expiry rate-limit fence |
| `services/research/trend_context.py`, `PassageExtractor.extract_passages` | Exact event lead selection and explicit competitive/incidental roles |
| `application/research/synthesis.py::synthesize_grounded_findings` | Current/historical separation and primary-before-competitive selection |
| `services/research/financial_context.py::financial_passage_context` | Exact financial period/currency/scope annotations, explicit unknowns |
| `agents/scout/assessment.py`, `agent.py`; `services/research/raw_pool.py::to_evidence_items` | Conservative financial output and preserved original observation clocks |
| `agents/trending/agent.py`; `services/report_builder.py`; `frontend/unified-report-renderer.js` | Distinct competitive-context contract and safe presentation |
| `scripts/validation/isolated_runtime.py::isolated_environment` | Blank parent-discovered dotenv credentials as well as local credentials |

Paths in the first three rows are under `backend/infrastructure/acquisition/`
and `backend/services/agent_reach/` as applicable. The dotenv repair matters for
nested worktrees: the installed dotenv version ignores `PYTHON_DOTENV_DISABLED`,
so explicit blanking, not that flag alone, supplies isolation. Early replay
initialization loaded a Supabase configuration in memory; the independent offline
socket guard prevented outbound traffic. No external write or secret logging is
claimed or required.

Focused regressions are `test_transport_failure_taxonomy.py`,
`test_scout_financial_context.py`, `test_oct21_event_selection.py`,
`test_raw_acquisition_pool.py`, `test_process_hardening.py`, the report projection
tests and frontend renderer controls. Genuine excerpts are labeled fixtures;
synthetic fault controls are not described as live captures.

## Authorized fresh verification: two sequential cases

Ran exactly the two approved ordinary local API/SSE requests, once each, with
normal provider restrictions, temporary SQLite/dossiers and no lifespan ingestion
or notifications. AI credentials were blanked and generation was disabled: zero
model checks, reservations or generation calls. No article URL was supplied.
The runner exited 0 for complete observation/unchanged bytes, **not research PASS**.
Application fingerprint stayed
`2ea7b182bf1f6b6f57e6c5052fdf9ae51b4d2cd5b87626cc13e0dc066a565058`.

[Native discovery funnel](evidence/2026-10-22_reliability_selection/live-funnel.json)
and [body-free raw-harvest measurements](evidence/2026-10-22_reliability_selection/live-raw-harvest.json)
retain the actual saved counts, source URLs/hashes, transport observations,
qualification and citation joins. Search URL observations can repeat; they are
not distinct publishers. Instrumented provider observations are not a complete
HTTP request count. The explicit HTTP admission cap was 80 per case.

| Observation | Apple / BrandShield | Tim Cook / Personal Watch |
| --- | ---: | ---: |
| Elapsed seconds | 66.42 | 31.13 |
| Main generated query records | 18 | 18 |
| Instrumented provider observations / search responses | 32 / 25 | 49 / 33 |
| Candidate URL observations in sampled search results | 202 | 191 |
| Normalized candidate records | 62 | 42 |
| Reader attempts / failed attempts | 16 / 5 | 8 / 5 |
| Raw records classified article bodies / their words | 7 / 5,197 | 1 / 833 |
| Qualified retained sources / words / UTF-8 KB | 4 / 3,044 / 20.333 | 0 / 0 / 0 |
| Selected useful excerpt words | 97 | 0 |
| Native research findings | 4 | 0 |
| Shared displayed finding strings | 7 | 0 |
| Native investigation status | COMPLETED | INSUFFICIENT_EVIDENCE |

The October 21 same-input baseline retained zero sources for both. New Apple
results demonstrate autonomous transport of real task-related articles, including
Financial Express/CryptoSlate lawsuit reporting, AsiaOne phishing/enforcement
reporting and a historical Hindu counterfeit seizure article. Four endpoint hosts
do not prove independent corroboration; the lawsuit stories may describe the same
event. Some source dates are historical. No active actor or current safety verdict
is established, and the seven displayed strings include generic role explanations,
not seven independently discovered incidents.

Apple's failed reads include an actual Forbes 403, two provider failures, one
connection failure and one exhausted per-attempt budget. They remain failures;
the successful publishers were not suppressed. Tim Cook returned 33 search
responses after Apple in the **same process**, so this sample does not reproduce
the previous all-empty sequential DNS cascade. It still has three unresolved
publisher paths and two HTTP failures. That is bounded recovery evidence, not a
proof that every resolver/provider or all subjects are reliable.

### First loss and follow-up on the new captured bytes

Tim Cook's sole article-classified capture is Financial Express reporting
Trump's comments **about** Cook. Its rejection `NO_RELEVANT_PASSAGE` is correct:
it is not Cook speaking and does not establish identity abuse. Another successfully
captured WION page contains 1,040 words, including actual source-reported fake
Cook livestream/crypto-impersonation prose, but was recorded as `DISCOVERY_LEAD`
with `NO_STRUCTURAL_BODY`. Its navigation-heavy body-fallback classification is
a distinct, actionable extraction/eligibility loss. Other candidates lose at
publisher resolution/HTTP; their uncaptured relevance cannot be asserted.

The Apple captures also expose conservative but wrong context labels: two concrete
lawsuit reports were called warning-only because acquired prose mentions earlier
warnings. A third source's police disruption role disagreed across two type fields.
These are downstream interpretation defects, not transport failures. The
October 23 closeout corrects them offline against the immutable fresh captures;
those results must not be substituted for the original live observations above.

### Browser boundary

[Fresh-capture browser measurements](evidence/2026-10-22_reliability_selection/live-browser-measurements.json)
verify those exact live response events through current page buttons/SSE/native
and shared renderers at 320/390/1440px. Six states had matching findings/cards,
intact ID/URL/hash joins, no horizontal overflow or uncaught JavaScript exceptions.
They visibly reproduce the original Apple label defects and Tim Cook abstention.
Two resource-console errors per case remain disclosed (blocked font and intentional
diagnostic 503). Browser provider traffic was blocked; this is presentation of
fresh captures, not two more live investigations.

Earlier [NVIDIA/OpenAI saved-SSE browser proof](evidence/2026-10-22_reliability_selection/browser-measurements.json)
also passes six viewport states with competitive context explicit. Three resource
errors per case remain disclosed. Manual screen-reader, measured contrast, axe,
Firefox/Safari, real mobile hardware and deployment parity are not verified.

## Offline completion — 2026-10-23

### Captured article recovery, not a new network success

`page_extraction.observe_anchored_article_body()` now recognizes a bounded partial
body in a body-fallback capture only when it has a unique **observed heading**
matching the captured title, an adjacent explicit byline/publication label and
at least three substantial prose paragraphs / 80 words. There is no publisher,
person or topic allowlist. Recovery stops at subsequent headings after prose has
started, including short related-story headings. Short initial photo labels do
not by themselves establish a body. A byline label does not supply a verified
publication timestamp.

The helper records exact source-hash-bound spans; it does not rewrite content.
`body_context.reconcile_captured_context()` preserves the original weak DOM-quality
observation and invalidates stale recovery if source bytes change. The harvest
pipeline reconciles before raw-pool structural classification. Pool serialization
retains bounded spans and original quality without arbitrary adapter metadata;
invalid recovery cannot inflate article counters.

The same scope applies to the normal passage selector, BrandShield's adjacent
paragraph fallback, specialist passage/quotation records, contextual source
classification, the legacy selected-excerpt path and public native serialization.
Review found and closed bypasses where related-card text could otherwise re-enter
after selection. Negative controls include short “Related stories” boundaries,
unrelated incident/quotation cards, replaced bytes and malformed/hash-mismatched
recovery. This is **structural extraction heuristic**, not entailment or truth.

On genuine saved Tim Cook bytes, the WION capture changes from discovery-only
`NO_STRUCTURAL_BODY` to one qualified source with an exact **42-word** selected
incident passage. All **1,040 words** of the original readable capture remain
available, including rejected surrounding chrome; they are not 1,040 useful
incident words. The unrelated 833-word Trump article remains rejected.
No legitimate Cook public statement is manufactured from the fake-stream report.
The historical September 2024 source-date observation is retained, not advanced
to the replay date, and current activity is not established.

The fixture is explicitly a genuine **saved readable-text** capture with observed
heading offsets, not the original HTML. The full readable text, canonical ID/URL,
title and acquired clock are checked. The original transport raw-capture hash is
an inherited observation; missing original HTML bytes cannot be independently
re-hashed in this continuation. No original capture or historical dossier is
rewritten.

### Conservative specialist and shared-report corrections

- BrandShield gives actual filed lawsuit allegations precedence over incidental
  warning language. Hypothetical “a complaint could be filed” guidance remains
  advice. Attributed police-disruption reports use consistent source-reported
  enforcement roles. Reporting URLs remain non-actor URLs and all allegations
  remain unverified; no takedown or live-threat conclusion follows.
- Scout's shared report no longer appends a legacy forecast/catalyst headline to
  canonical exact financial findings. Legacy-only inputs retain their fallback.
- Personal Watch's shared report likewise gives canonical passage findings
  precedence over stringified legacy threat dictionaries. The recovered fake-Cook
  report must remain an unverified source allegation, not an authenticated account,
  current high-risk incident or calibrated probability.

New focused controls are `test_anchored_article_recovery.py`,
`test_recovered_scope_projection.py`, `test_brand_incident_precedence.py` and the
expanded report-projection controls. The genuine-source helpers and replay continue
to block networking and model generation; they do not create new evidence bytes.

### Final offline results and browser acceptance

[Final offline measurements](evidence/2026-10-22_reliability_selection/final-offline-results.json)
compare **every** original raw record's ID, URL, title, readable-text hash/text,
acquired clock and declared publication field. Both inventories are unchanged:
62 Apple records and 42 Tim Cook records. Structural/qualification labels are
recomputed; they are not new captured content. Earlier intermediate replay
manifests remain in the evidence folder and are not silently replaced.

| Final current-code replay | Qualified sources / retained words / UTF-8 KB | Selected useful excerpt words | Interpretation |
| --- | --- | ---: | --- |
| Apple / BrandShield | 4 / 3,044 / 20.333 | 97 | Two source-reported allegations and two historical-enforcement observations, all unverified/non-active endpoints |
| Tim Cook / Personal Watch | 1 / 1,040 / 6.587 | 42 | One source-reported impersonation allegation; risk UNASSESSED, confidence unavailable, no observed actor handle/URL or current activity |

The final Apple shared report has six strings: four exact findings plus two role
explanations, **not six independent incidents**. Tim has one canonical exact
finding, no stringified legacy threat dictionary, no duplicate HIGH alerts and no
legitimate Cook public statement manufactured from the report. A scope-aware brief
now counts its one task-related capture instead of rejecting the whole noisy raw
buffer. This is useful incident-report context, not verified current exposure.

[Final Chromium measurements](evidence/2026-10-22_reliability_selection/final-browser-measurements.json)
record exit 0 at 320/390/1440px for both exact corrected reports: six states,
intact source/citation ID/URL/title/hash/passage joins, keyboard source inspection,
matching findings/cards, no horizontal document overflow or uncaught JavaScript
exception. Final application fingerprint:
`3b8fc973e011eaf4db6a0ff0bec130b003e7240df087f3d03857adf19a84cd2a`.
The initial closeout browser run failed at Tim/320px (336px document width). A
narrow wrapping/min-width fix in `personal-watch-agent.html` repaired the compact
history/action row; no clipping or redesign. Earlier failure evidence remains.
Two deliberately blocked-resource console errors per case remain disclosed.
No new provider/model requests occurred during any browser replay.

## Final verification actually run

Commands ran from the dirty repair worktree, using fresh temporary logs/outputs.
Full and fast suites overlap; do not add their counts. Unit mocks and saved-source
replay are not live acquisition. No remote CI, push, merge or deployment ran.

| Command / scope | Actual final result |
| --- | --- |
| `python -m pytest tests/ -q` | Exit 0; **1,969 passed / 79.26s** |
| `python -m pytest tests/unit tests/chaos tests/security -q` | Exit 0; **1,761 passed / 65.46s** |
| `python -m flake8 backend tests scripts --count --select=E9,F63,F7,F82 --show-source --statistics` | Exit 0; zero fatal findings |
| Each of nine `tests/frontend/test_*.js` Node scripts | Exit 0 each |
| `python scripts/validate_release_candidate_smoke.py --output <new-temp-json>` | Exit 0; OFFLINE_SMOKE_PASS |
| `python scripts/validate_rollback_compatibility.py --output <new-temp-json>` | Exit 0; OFFLINE_PERSISTENCE_PASS; historical archive/deployed rollback NOT_VERIFIED |
| `python scripts/validation/verify_frozen_benchmarks.py` | Exit 0; frozen content hashes match |
| Protected-tree Git diff, whitespace and documentation-link checks | Exit 0; protected-tree diff empty; 322 relative links resolve at final closeout |
| Two-case live terminal runner | Exit 0 observation/stable bytes; original Tim research result insufficient, not a research PASS |
| Final genuine-source/API replays | Exit 0 each; all original raw identities/body hashes/clocks preserved; zero network/model calls |
| Final saved-SSE Chromium runner | Exit 0; six states; not fresh final-code acquisition |

### Failed/intermediate runs, not hidden as passes

- Initial full regression: **10 failed / 1,877 passed**. True-SSRF API detail
  compatibility was restored; two new controls used the wrong shape for the new
  structured context field and were corrected. Seven historical core-hash
  differences were additive financial annotations: the existing golden core
  projection excludes that additive metadata only, with separate annotation
  tests. No frozen fixture or historical golden manifest was changed.
- Later full/fast runs: **2 failed / 1,958 passed** and **2 failed / 1,750 passed**.
  One exposed preventive scam guidance lacking the literal word “warning”; the
  code now recognizes concrete inspection/verification advice, while real filed
  lawsuits retain precedence. The other expected two HIGH duplicates from one
  Jensen allegation. The golden test now explicitly asserts the old baseline
  and the precise intended delta to one unassessed source report, checking IDs,
  absent actor proof and all unrelated fields. The recorded manifest is intact.
- Independent review reproduced related-card, fallback and serializer scope
  bypasses using synthetic additions to genuine text. These were fixed and
  regression-tested, not relabeled as live incidents.
- Early offline/browser initialization assertions exposed parent dotenv loading;
  explicit blanking fixed isolation. The older disable flag alone was not trusted.
  A presentation run with concurrent backend edits failed the fingerprint check;
  the clean rerun is separately recorded. Final-browser-v1 exposed the mobile
  overflow and incorrect zero-task brief; final-browser-v2 passes corrected bytes.
- Some exploratory file reads/patch attempts used nonexistent paths or stale
  contexts; they made no edits and are not test results. Fresh outputs are always
  new files, never tracked benchmark replacements.

## Acceptance and remaining work

| Area | Status | Remaining boundary |
| --- | --- | --- |
| Exact event/period/context selection on saved Scout/Trending cases | PASS for sampled offline controls | General recall, financial filing reconciliation, direct-topic coverage and accuracy remain PARTIAL |
| Apple/BrandShield autonomous acquisition | PARTIAL | Four useful retained sources freshly acquired; subsequent interpretation fixes verified offline only |
| Tim Cook/Personal Watch end-to-end output | PARTIAL | Relevant bytes autonomously acquired, then corrected offline; no fresh final-code acquisition run |
| DNS taxonomy, deadline/cooldown isolation and security regressions | PASS offline | Original host-outage cause NOT_VERIFIED; public DNS success does not prove universal recovery |
| Corrected source-to-browser contracts | PASS for bounded saved-SSE checks | Full accessibility, cross-browser and deployed parity NOT_VERIFIED |
| Independent research accuracy and current threat verification | NOT_VERIFIED | Human held-out review, independent source support and direct actor/media evidence still needed |
| Release readiness | NOT ACCEPTED | No final-code live reliability gate, hosted CI or deployed rollback verification |

Remaining P0 acceptance work is a **new separately approved small final-code live
check**, not a source/provider expansion or another model run. Some publishers
still fail with 403, unresolved wrappers, connection/provider errors or bounded
timeouts; inaccessible sources must remain failures. The structural recovery is
deliberately narrow and does not guarantee every publishing layout. Preserve
unknowns rather than loosening body/entity/date/security gates to raise counts.

The independent reviewer packet remains the accuracy gate. Filing comparison,
measured virality, identity/media authentication and current actor exposure were
not established here. The original historical archive previously reported 55
malformed dossiers; it was neither independently re-inventoried nor recovered
in this isolated run. No historical record was silently repaired.

All two-investigation permissions and tiny transport probes are consumed.
**Zero live AI generation/model checks in this repair continuation. No commit,
push, merge, deployment, credential/access change or protected-data rewrite.**
