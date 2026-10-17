# Role-aware evidence and bounded AI review — 2026-10-17

**Overall PARTIAL. Research-quality acceptance FAIL. No main merge/deployment.**

User requested the suggested content-role, agent-specific retrieval, financial
document and frontend improvements, plus an AI layer for suggestions when needed.
This is an implemented and measured iteration, not acceptance of every agent.
Starting commit `d37b35f`; development branch
`feat/continuous-source-intelligence-20261017`. Application checkpoints:
`6666b08` (role/AI/PDF), `19bf350` (counterfeit word boundaries),
`3d628e1` (public metadata). See [handoff](../handoffs/2026-10-17_ROLE_AWARE_AI_EVIDENCE.md),
[evidence index](evidence/2026-10-17_role_aware_ai_evidence/README.md) and
[measurements](evidence/2026-10-17_role_aware_ai_evidence/measurements.json).

## A. Source-by-source improvements

### Shared processing and advisory AI

The implemented path is acquisition → bounded raw capture → content-role and
agent-objective checks → optional AI paragraph suggestions → deterministic
validation → unverified observations/citation checks → public inspection.
It reuses the existing centralized LLM gateway and source planner.

- **Content roles:** author biographies, navigation, legal disclosures, profile
  metadata and document indexes no longer compete as ordinary shared event
  passages. Captured text remains available; source ownership is not truth.
  Known index/landing/profile roles are discovery-only in inspection.
- **Agent objectives:** financial passages must concern financial/corporate
  events; brand passages must concern relevant abuse/risk; personal passages
  require identity-abuse/authenticity context. Brand/identity queries precede
  generic company searches; entity-only brand/personal plans no longer begin
  with publisher product feeds.
- **AI source suggestions:** automatic only with live configured credentials
  and mocks off; at most one validated search action within the existing query
  budget. No model-suggested reads/URLs, invented subreddit targets, authority,
  access overrides or fabricated retrieval.
- **AI passage suggestions:** complete enumerated paragraphs selected by
  existing evidence ID and exact offsets. Model prose never replaces source
  text. Subject, objective and content role are rechecked; no new facts, URLs,
  citations or verdicts. Personal-watch text and likely sensitive captures are
  skipped; the privacy filter is conservative, not comprehensive.
- **Bounds:** 2–2.5s caller deadline, one provider attempt per advisory call,
  output-token limits and at most two outstanding advisory workers process-wide.
  Late model results cannot mutate the returned investigation. Source planning
  and passage advice are separate bounded calls, not a claim that all legacy
  agent reasoning uses only one LLM request.
- **Provider fix:** Gemini previously ignored caller timeout kwargs. The
  provider now honors per-call timeout/total budget/attempt/token/JSON options;
  existing default fallback semantics remain when those options are omitted.
- **Live AI is BLOCKED/UNAVAILABLE, not working inference:** model-list HTTP
  200 lists the configured generation models, but the minimal real structured
  generation attempt returns HTTP 429 (diagnostic exit 2). This is not proof
  of an invalid key, exact quota type or successful live selection. No models,
  credentials, billing or production settings were changed.
- **Public boundary:** Scout previously discarded raw/page metadata and kept
  only a truncation flag. Scout/BrandShield now use an explicit public metadata
  allowlist. No arbitrary cookies/auth/provider envelope is forwarded. PDF
  offsets are clipped to retained text; omitted/partial pages remain explicit.

### Bounded PDF extraction

Native web reading recognizes PDFs before UTF-8/HTML decoding, using pinned
`pypdf==6.10.0` in a secret-stripped subprocess: 1MB source cap, eight pages,
24k text characters, 2.5s wall limit, 384MiB process memory and two CPU seconds
(POSIX limits / Windows Job Object). Unsupported resource limits, malformed and
encrypted files fail closed. This is resource isolation, not a complete OS
security sandbox. No OCR or verified table-cell/period/unit alignment.

Issuer following remains bounded: maximum three observed same-origin link hops,
up to two reserved followup reads **inside the existing read/time budget**.
No unbounded crawling or guessed document URLs.

A real observed Infosys `q1-2027.pdf` direct read returned HTTP 200,
153,742 source bytes, 1,597 retained layout-text words / 24.024 KB. The file has
six pages; the 24k character cap retains four complete pages plus part of page
five, with explicit truncation. The existing adapter's 12k research capture
retains 966 words / 12.018 KB and clips page references accordingly. A separate
combined audited-results PDF exceeded 1MB and was rejected (direct diagnostic
exit 1). **The source cap was not enlarged to obtain a pass.**

The final normal Infosys run acquired another observed document,
`ifrs-usd-press-release.pdf`, with 1,456 retained words and a passage about
large-deal TCV plus an attributed management quotation. Other passes acquired
only indexes or different PDFs. This establishes useful accessible document
depth, not consistent financial statement coverage or a verified investment
conclusion.

### All 52 operation observations

All 52 registered executable operations remain; all 16 protected routes sampled.
Final run: **53 executions = 52 original targets plus one additional observed
PDF web.read target**, 79 observations, 69 bounded captured samples. Eleven
operations returned none; source fingerprint unchanged during the run.

The table pairs identical operation/target hashes with the preceding checkpoint.
The extra PDF is reported separately above, not added to web.read's before/after
comparison. Words are whitespace-delimited, KB UTF-8 bytes / 1,000. These changing
public services are time-separated observations, not causal effect estimates.
CJK whitespace counts are not linguistic token counts. Fields: T title, U URL,
A author, D publication date, B body; number is records missing that field.
“none” is inventory completeness, not authenticated field accuracy.

Every nonempty source remains PARTIAL for research acceptance; authenticated
access requirements remain BLOCKED. FAIL means this probe returned no records
without an established resolution. Each captured inspection reached all four
page templates at 320/390/1440px in a **labeled display scaffold**, not 52 fresh
normal investigations. Source display: 69 samples / 12 states / zero measured
failures. The real PDF alone also passed 12 display states across four pages.
No screenshot or native source content was invented.

| Operation | Readable words before → after | Final KB | Runtime | Acceptance | Missing fields | Content scope / remaining limit |
| --- | ---: | ---: | --- | --- | --- | --- |
| `github.read` | 4749 → 4749 | 42.167 | SUCCESS | PARTIAL | A1, D1 | README body; author/date absent, not repository-wide audit |
| `github.issues` | 710 → 710 | 5.843 | SUCCESS | PARTIAL | none | bounded issue bodies/comments; not all discussions |
| `github.prs` | 97 → 97 | 1.146 | SUCCESS | PARTIAL | none | bounded PR text; not full diff/review |
| `github.commits` | 302 → 302 | 2.897 | SUCCESS | PARTIAL | none | commit messages/metadata; not changed-code analysis |
| `github.releases` | 124 → 124 | 2.651 | SUCCESS | PARTIAL | none | release notes; not independently checked release claims |
| `youtube.read` | 379 → 379 | 2.546 | SUCCESS | PARTIAL | none | video description/metadata, not spoken content |
| `youtube.transcript` | 675 → 675 | 4.263 | SUCCESS | PARTIAL | T1, A1, D1 | captions retained; title/author/date missing; no audiovisual verification |
| `youtube.comments` | 49 → 17 | 0.086 | SUCCESS | PARTIAL | none | two sampled comments, not sentiment population |
| `v2ex.latest` | 24 → 50 | 1.002 | SUCCESS | PARTIAL | none | bounded latest topics; Chinese whitespace undercounts tokens |
| `v2ex.search` | 95 → 95 | 2.065 | SUCCESS | PARTIAL | none | bounded topic results; not exhaustive search |
| `v2ex.topic` | 165 → 165 | 3.622 | SUCCESS | PARTIAL | none | topic text; no independent verification |
| `v2ex.replies` | 19 → 19 | 0.314 | SUCCESS | PARTIAL | none | two replies, not whole conversation |
| `web.read` | 333 → 333 | 2.258 | SUCCESS | PARTIAL | A1, D1 | main/article extraction: 680 raw to 333 readable words; author/date absent |
| `rss.read` | 376 → 358 | 2.469 | SUCCESS | PARTIAL | A2 | feed summaries plus bounded linked-read context; missing authors |
| `xiaoyuzhou.podcast` | 17 → 17 | 0.443 | SUCCESS | PARTIAL | none | podcast metadata, not audio transcript |
| `xiaoyuzhou.episodes` | 116 → 116 | 4.052 | SUCCESS | PARTIAL | none | episode show notes, not audio transcript |
| `reddit.read` | 210 → 210 | 1.264 | SUCCESS | PARTIAL | B1 | old AMA sample plus removed/empty item; not current broad coverage |
| `reddit.comments` | 4 → 4 | 0.021 | SUCCESS | PARTIAL | B1 | four words plus deleted/empty marker; not full thread |
| `twitter.status` | 5 → 5 | 0.024 | SUCCESS | PARTIAL | none | five-word historical public post; no current coverage proof |
| `twitter.profile` | 16 → 16 | 0.133 | SUCCESS | PARTIAL | D1 | 16-word bio; no observed publication date or identity authentication |
| `hackernews.read` | 184 → 184 | 1.053 | SUCCESS | PARTIAL | B1 | parent plus sampled comments; one empty parent body |
| `hackernews.search` | 484 → 484 | 2.888 | SUCCESS | PARTIAL | B2 | bounded parents/comments; two records lack bodies |
| `stackexchange.read` | 2319 → 2319 | 13.740 | SUCCESS | PARTIAL | none | question and bounded answers; not all answers |
| `stackexchange.search` | 3548 → 3548 | 21.277 | SUCCESS | PARTIAL | none | two bounded Q&A bundles; not all discussions |
| `sec_edgar.read` | 0 → 0 | 0.000 | CONFIG_REQUIRED | BLOCKED | none | SEC_USER_AGENT configuration required; retained blocked state |
| `nist_cve.read` | 103 → 103 | 0.713 | SUCCESS | PARTIAL | none | vulnerability description/metadata, not exploit verification |
| `arxiv.read` | 166 → 166 | 1.136 | SUCCESS | PARTIAL | none | abstract and metadata, not full paper |
| `fact_check.search` | 0 → 0 | 0.000 | AUTH_REQUIRED | BLOCKED | none | Google Fact Check credential unavailable; no fabricated ClaimReview |
| `arxiv.search` | 514 → 514 | 3.730 | SUCCESS | PARTIAL | none | two abstracts, not full papers |
| `bilibili.search` | 34 → 34 | 1.076 | SUCCESS | PARTIAL | none | video metadata; real returned publication date, no transcript |
| `boss.search_jobs` | 0 → 0 | 0.000 | AUTH_REQUIRED | BLOCKED | none | configured authenticated browser/CDP access unavailable |
| `facebook.oembed` | 10 → 10 | 0.270 | SUCCESS | PARTIAL | D1 | ten-word embed/bootstrap HTML; not substantive post body |
| `facebook.search` | 0 → 0 | 0.000 | AUTH_REQUIRED | BLOCKED | none | required server-side access unavailable |
| `github.search` | 23 → 23 | 0.284 | SUCCESS | PARTIAL | A2, D2 | repository search metadata only |
| `instagram.oembed` | 0 → 0 | 0.000 | DEGRADED | FAIL | none | empty degraded embed; no substantive post body |
| `instagram.search` | 0 → 0 | 0.000 | AUTH_REQUIRED | BLOCKED | none | required server-side access unavailable |
| `jina_reader.read` | 333 → 333 | 2.258 | SUCCESS | PARTIAL | A1, D1 | same public page as web.read; not independent corroboration |
| `linkedin.jobs` | 30 → 30 | 0.565 | SUCCESS | PARTIAL | D2 | 30 words of job metadata; missing dates stay unknown |
| `news.search` | 58 → 60 | 0.334 | SUCCESS | PARTIAL | A2 | syndicated discovery; not original article bodies |
| `nist_cve.search` | 104 → 104 | 0.675 | SUCCESS | PARTIAL | none | bounded vulnerability metadata |
| `reddit.search` | 0 → 0 | 0.000 | DEGRADED | FAIL | none | empty final probe; earlier 84-word observation was not reproduced |
| `rss.search` | 30 → 30 | 0.188 | SUCCESS | PARTIAL | A2 | summary/discovery only; missing authors |
| `sec_edgar.search` | 0 → 0 | 0.000 | CONFIG_REQUIRED | BLOCKED | none | SEC_USER_AGENT configuration required; retained blocked state |
| `twitter.read` | 5 → 5 | 0.024 | SUCCESS | PARTIAL | none | same status alias, not another independent source |
| `twitter.search` | 16 → 16 | 0.133 | SUCCESS | PARTIAL | D1 | profile fallback, not matching post search |
| `v2ex.hot` | 14 → 14 | 1.076 | SUCCESS | PARTIAL | none | bounded hot topics; Chinese whitespace undercounts tokens |
| `web.search` | 59 → 59 | 0.410 | SUCCESS | PARTIAL | D2 | search-index snippets; missing publication dates |
| `web_search.search` | 59 → 59 | 0.410 | SUCCESS | PARTIAL | D2 | same search-index alias; do not double-count independence |
| `xiaohongshu.search` | 0 → 0 | 0.000 | AUTH_REQUIRED | BLOCKED | none | required server-side access unavailable |
| `xiaoyuzhou.search` | 0 → 0 | 0.000 | DEGRADED | FAIL | none | empty search; no useful text acquired |
| `xueqiu.search` | 0 → 0 | 0.000 | AUTH_REQUIRED | BLOCKED | none | required server-side access unavailable |
| `youtube.search` | 72 → 72 | 0.455 | SUCCESS | PARTIAL | D2 | search metadata; publication dates absent |

Most non-web adapters were preserved and remeasured, not individually rewritten.
Direct Reddit/X samples remain bounded/variable; profile fallback is not
matching-post retrieval. The pre-existing local Reddit flag was observed true;
this is not independent platform authorization. Access restrictions were not
bypassed. Frozen JSONL, historical dossiers, research/artifact bytes, scrapers
and compatibility shims are unchanged.

## B. Actual four-agent improvements

### Normal twelve-input matrix

Actual Chromium page buttons → real local SSE/backend → real acquisition →
processing → native/shared renderers. One normal request per fixed input,
390/1440px views of the same result. Mocks off for these live runs; temporary
SQLite/dossiers, remote persistence/notifications/background ingestion disabled.
Pinned actual Chart.js 4.4.1 bytes; external fonts blocked.

Final application fingerprint
`3d5290a779c290764ddb770c9168141d14d0731867da9fd1dbc339ebefc40d48`
was stable throughout; code was subsequently committed at `3d628e1`.
The captured HEAD/dirty flag remains in the JSON rather than pretending the
commit existed before measurement.

Before: preceding final matrix, 33 native records / 11,336 retained-text words.
After: **29 records / 12,736 words**, two zero-acquisition inputs (now OpenAI and
Brand/Tata). Counts include profiles, index pages and storefronts, **not 29
useful documents or ten successful investigations**. Variable network/source
results and overlapping local audit processes preclude controlled latency or
causal accuracy claims.

| Agent / input | Native records before → after | Words before → after | Final KB | Browser seconds | Findings / discovery |
| --- | ---: | ---: | ---: | ---: | ---: |
| scout / TATAMOTORS.NS | 2 → 2 | 680 → 666 | 5.434 | 19.51 | 2 / 27 |
| scout / INFY.NS | 6 → 6 | 947 → 2331 | 17.207 | 29.33 | 4 / 30 |
| scout / AAPL | 8 → 7 | 676 → 502 | 5.770 | 29.69 | 2 / 21 |
| trending / OpenAI | 1 → 0 | 119 → 0 | 0.000 | 15.26 | 0 / 6 |
| trending / NVIDIA | 5 → 4 | 7787 → 5531 | 38.525 | 14.55 | 4 / 8 |
| trending / electric vehicles | 1 → 2 | 624 → 2085 | 12.564 | 12.54 | 2 / 0 |
| brandshield / Nike | 0 → 3 | 0 → 1266 | 7.305 | 17.61 | 3 / 17 |
| brandshield / Apple | 7 → 2 | 467 → 319 | 1.837 | 16.89 | 2 / 12 |
| brandshield / Tata Motors | 0 → 0 | 0 → 0 | 0.000 | 14.06 | 0 / 7 |
| personal_watch / Sam Altman | 1 → 1 | 18 → 18 | 0.101 | 16.12 | 0 / 12 |
| personal_watch / Tim Cook | 1 → 1 | 8 → 8 | 0.059 | 19.34 | 0 / 11 |
| personal_watch / Satya Nadella | 1 → 1 | 10 → 10 | 0.073 | 16.43 | 0 / 7 |

### Content review, not count inflation

- **Scout / Infosys — PARTIAL improvement:** six retained records / 2,331 words,
  including a genuinely read PDF (1,456 words). One structured UNVERIFIED
  observation resolves to that source. Three other strings are unresolved
  legacy index labels. No complete financial table/period/unit adjudication;
  the quarterly hub can still receive a PRIMARY label when its summary contains
  financial prose. Primary does not mean its linked statements were fully read.
- **Scout / Tata and Apple — FAIL task acceptance:** Tata retains an issuer
  index and conference-call document, with unresolved labels; Apple still
  contains product-feed/homepage material. Not financial anomaly verification.
- **Trending / EV — PARTIAL, demonstrated passage improvement:** two real article
  bodies / 2,085 words. Both displayed observations concern article content
  (airport chargers and the reported EV-buying survey); both citations resolve
  to acquired records. The earlier author biography no longer becomes a finding.
  The underlying claims/survey methodology are not independently adjudicated.
- **Trending / NVIDIA — PARTIAL:** four original publisher bodies / 5,531 words,
  four separately cited UNVERIFIED observations. One fewer retained article
  than the prior five-record pass; no false claim that every source improved.
  Publisher announcements are not independent corroboration or virality proof.
- **Trending / OpenAI — FAIL acquisition in final pass:** zero acquired bodies,
  six discovery leads. Earlier runs obtained a short Reddit discussion; first-party
  article restrictions and varying provider results remain unresolved.
- **Brand / Nike — counterfeit false positive fixed; task acceptance FAIL:**
  live review found substring “clone” inside product name “Cyclone.” Two red/green
  regressions and both classifier paths now use word boundaries. No authenticity
  was granted to the storefront domain. Final native threat list no longer has
  that counterfeit signal, but three legacy “Genuine Issue” findings are generic
  storefront/product text, not useful brand intelligence.
- **Brand / Apple — FAIL specialist relevance:** two homepage records / 319 words.
  Native compatibility findings still project merchandising snippets. Shared
  role gating does not yet prevent every legacy observation from appearing in
  KEY FINDINGS. This is a remaining P1 upstream promotion bug, not a successful
  threat investigation.
- **Brand / Tata — FAIL:** zero bodies, seven discovery leads. Not evidence of
  brand safety or absence of threats.
- **All three Personal Watch cases — FAIL specialist depth:** 18/8/10-word profile
  bios only. No fabricated impersonation findings, but no actual identity-abuse
  investigation, media forensics or independently authenticated current identity.
  Passage advice intentionally skips this domain for privacy.

Seven structured citation observations resolve to SOURCE_RECORD, zero to
DISCOVERY_ONLY or UNAVAILABLE. **This covers the structured subset only**;
legacy unresolved strings and brand compatibility findings do not gain proper
citation/epistemic contracts merely because that subset has no broken joins.
No measured entailment precision/recall or calibrated confidence is claimed.

Earlier additional normal inputs (IBM, AMD, Puma, Jensen Huang) yielded
1/0/0/0 records; IBM had 1,689 words. Those runs precede the final metadata repair
and are explicitly historical controls in the JSON, not final-code held-out
acceptance. They demonstrate that broad agent generalization remains unproved.

### Browser and regression evidence

All twelve final requests returned HTTP 200, completed results and 29 progress
events. All 24 viewport states preserve expected findings/evidence/discovery
counts and finding text, no document overflow or uncaught page exceptions.
Available first evidence inspectors opened by keyboard Enter. All twelve mobile
report captures were visually inspected, plus focused real-PDF scaffold captures.
These limited checks are not a full visual/accessibility acceptance.

There were 18 console resource errors: deliberately blocked external font loads
and static-resource errors. Earlier matrices also recorded aborted local
capability refreshes; the final failed-request list contains blocked fonts.
No claim of a console-clean run or per-resource resolution.
Full screen-reader behavior, measured contrast, axe, Firefox/Safari and real
mobile hardware remain UNVERIFIED. Display-only source/PDF scaffolds are not
normal backend investigations.

| Verification actually run | Result / boundary |
| --- | --- |
| `pytest tests/ -q` final metadata repair | exit 0; **1,363 passed, 53.90s** |
| `pytest tests/unit tests/chaos tests/security -q` | exit 0; **1,155 passed, 30.70s** |
| All eight Node frontend suites | exit 0; hostile AI-status / PDF-page rendering included |
| Fatal Flake8 E9/F63/F7/F82 | exit 0; zero |
| Isolated release smoke / rollback compatibility | exit 0; OFFLINE_SMOKE_PASS / OFFLINE_PERSISTENCE_PASS; historical archive NOT_VERIFIED here |
| Frozen benchmark validator / protected-tree diff against starting commit | exit 0; unchanged |
| Final source probe | exit 0; stable fingerprint, 16 protected sampled; all-source PARTIAL |
| 69-sample display / PDF-only display | exit 0; 12 + 12 states, zero measured failures |
| Live AI diagnostic | exit 2; listing 200, generation 429; UNAVAILABLE, not PASS |
| Exact application hosted CI `3d628e1` | all five jobs SUCCESS; [run](https://github.com/Shaunakrane914/Misinformation/actions/runs/39053082338) |

Earlier `6666b08` and `19bf350` also passed five hosted jobs. CI includes full
offline/persistence/smoke, fatal lint/frontend, and fast suites on Python
3.11/3.12/3.13. It does not establish live research quality or deployment parity.

Failure history is preserved in the handoff: initially absent interfaces,
overstrict legacy-brand filtering, oversized pytest parameter IDs causing
Windows temp-path errors, no-op advice telemetry changing golden digests,
the live Cyclone false positive and Scout metadata loss. First live matrix
overlapped source edits and exited 1 for an invalidated fingerprint; subsequent
stable matrices and the final current-code matrix remain distinct. No frozen
expected findings or source bytes were regenerated to hide failures.

### Continuation priorities

1. **P1:** stop legacy BrandShield “Genuine Issue”/safe-record projections from
   manufacturing findings out of every non-threat source. Preserve background
   observations separately; absence of a detected threat does not establish safety.
2. **P1:** financial PDF/table/period/unit alignment, selection of useful bounded
   releases when an oversized combined filing is rejected, and better nested-index
   semantics. Keep the 1MB cap unless governing instructions explicitly change.
3. **P1:** acquire and investigate specific brand/identity abuse candidates;
   product catalogs and bios are not sufficient. No claims of ownership/attacker
   identity without supporting evidence.
4. **P2:** case-specific executive briefs and next actions, without rewriting
   unverified observations into authoritative narratives. Make legacy uncertainty
   and citation coverage visible rather than equating findings count with quality.
5. **Owner:** resolve provider-side generation limits securely and rerun the
   minimal AI diagnostic. Successful live advice remains UNVERIFIED until then.
6. Run a human-reviewed, new claim-support evaluation, the normal matrix/new
   controls, regressions and exact-code hosted CI after each substantive repair.

Changes are committed/pushed only on the development branch. No merge,
deployment, historical recovery or unattended future operation is claimed.
