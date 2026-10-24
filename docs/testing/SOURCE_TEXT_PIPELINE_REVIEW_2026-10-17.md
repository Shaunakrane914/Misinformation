# Source capture, readable text and frontend review — 2026-10-17

Latest [source-to-report repair and six bounded live observations](REPORT_COMPLETION_AND_FOUR_AGENT_CHECK_2026-10-20.md)
correct Adobe's heading/title loss and preserve the substantive captured paragraph.
1,555 full / 1,347 fast tests and 12 offline browser states pass. **Not fully
fixed:** Dyson/Mary Barra only reach background publisher hubs, not article
evidence; Trending freshness-query effect remains unverified live. Zero AI,
no commit/push/merge/deployment. Earlier statements below remain dated history.

Latest [Adobe post-fix live verification](ADOBE_POSTFIX_LIVE_CHECK_2026-10-20.md):
query-driven acquisition now demonstrated in one case (842-word article), but
heading-only synthesis keeps research acceptance open. No AI, push or deployment.

## Continuation checkpoint — 2026-10-20

See [autonomous-discovery repair](AUTONOMOUS_DISCOVERY_REPAIR_2026-10-20.md)
and [handoff](../handoffs/2026-10-20_AUTONOMOUS_DISCOVERY_REPAIR.md) for the latest
implementation and actual 1,532 full / 1,324 fast tests. Two authorized fresh
Adobe/Dyson cases still did not establish useful autonomous article acquisition.
Current saved-byte processing removes an index false finding; resolver scheduling
and asset rejection are offline verified, not freshly live proven. Zero AI calls;
uncommitted/unpushed, no merge/deployment. The original report below is dated history.

## Decision

**Extraction improvements verified in bounded samples; overall research acceptance remains FAIL / PARTIAL.**
The repeatable probe now covers **all 52 executable operations**, not just the
16 protected operations. No website is silently removed because it failed.
All protected operations returned samples in the complete passes. This is not
proof of full-site coverage, source accuracy, independent corroboration or uptime.

Direct source reads improved, but the new twelve-input normal agent run still
returned no acquired records for eight inputs. It returned five records / 355
whitespace words / 2.070 KB in total. Do not call this a completed evidence-rich
four-agent product or claim that more scraper code has solved research quality.

[Handoff](../handoffs/2026-10-17_SOURCE_TEXT_PIPELINE.md) ·
[machine evidence and browser captures](evidence/2026-10-17_source_text_pipeline/README.md).

## Implemented path and boundaries

`bounded acquisition → native source records → readable extraction + raw provenance → research qualification → shared frontend inspection`

- Web HTML previously flattened navigation, body and footer before truncation.
  The reader now selects a semantic article/main container, excludes structural
  chrome and preserves paragraphs, headings, negation, table-row context and
  correction asides. Multiple articles in a main container are retained rather
  than selecting an arbitrary card. Body fallback stays explicit.
- The cleaned content is used by the existing reader/research path. Separate
  `raw_capture` retains up to 100,000 characters of page text, its cap flag and
  the original extracted-text hash. This is **text, not a saved HTML archive**.
  Transport hashes still identify the bounded wire body. Captured passage
  offsets address the readable content, not DOM nodes or the raw HTTP body.
- All native source records use the existing inspection contract. New additive
  metrics report retained raw/readable UTF-8 bytes and whitespace-delimited
  words. Source-specific observations use a bounded scalar allowlist, not an
  arbitrary metadata dump. Unknown authors/dates, metadata-only records,
  summaries, truncation and unknown completeness remain visible.
- Deep research reads retain up to 12,000 body characters instead of 4,000,
  without increasing the transport deadline or byte cap. An explicit source URL
  now honors the existing `max_read_chars` budget instead of ignoring it.
- Stack Overflow deep mode acquires at most two vote-ranked answers for each
  of at most two questions. Answers retain their own IDs, parent IDs, authors,
  dates, license and acquisition transport. They do not replace the question.
  Wrong-parent answers are rejected; backoff, quota and follow-up failures do
  not erase the original question. This follows the official
  [answer endpoint](https://api.stackexchange.com/docs/answers-on-questions) and
  [throttling contract](https://api.stackexchange.com/docs/throttle).
- Reddit `comments` now requires an explicit thread/ID and returns only comment
  records, never a submission or unrelated search results. Removed/deleted body
  markers remain metadata observations with no fabricated body. Actual comments
  are `COMMENT`, not `FULL_ARTICLE` merely because they are long. The comment
  fetch uses the shared bounded, redirect-validating HTTP transport and checks
  the returned parent ID. No approval flag, cookie or server secret was edited.
- NVD/arXiv now retain observed endpoints, HTTP statuses and wire hashes and
  explicitly record real default-transport observations. Injected test fetchers
  are not labeled live. Earlier false network flags remain in baseline evidence.
- All four pages display the same raw/readable metrics and source observations
  through the shared renderer. Evidence grid tracks now shrink within their
  container rather than clipping long content behind `overflow:hidden`.

The cleaning layer is deterministic extraction, **not model rewriting of
evidence**. It does not manufacture summaries, resolve claims, upgrade profile
bios to identity proof, certify publishers, infer engagement or infer transcripts
from audio URLs. API bodies and retained evidence can still be irrelevant.

## Measurement method

Fresh output trees only; no tracked evaluations or historical dossiers were
overwritten. The source cycles used the actual production dispatcher, bounded
public examples and `--deep --limit 2`. A detailed baseline covered 52 operations;
two post-change rounds covered those 52 plus two supplemental web pages, 60
seconds apart. A separate 52-operation pass used the existing server environment.
Each run recorded its dirty HEAD and source fingerprint and reported unchanged
source during the run. They are distinct observations, not independent trials
or a deduplicated corpus. Follow-up records can exceed the top-level limit.

KB = UTF-8 bytes / 1,000. Words = whitespace-delimited units, which substantially
underrepresent linguistic word counts in Chinese/CJK text. Counts exclude JSON
envelopes. Raw text means retained native text; before structural HTML selection,
raw and readable counts are identical by design. More words are not precision,
recall, relevance or evidence strength. Sampling fixtures are not human labels.

### Demonstrated depth changes

| Fixed operation / input | Before | After, repeated round 2 | Interpretation |
|---|---|---|---|
| `web.read`, Python about | 680 words / 4.616 KB | 333 words / 2.258 KB | Structural boilerplate removed, not a loss of 347 verified facts |
| `stackexchange.read`, question 231767 | 1 record, 131 words / 1.009 KB | 3 records, 2,319 words / 13.740 KB | Question plus two actual answers, not full thread coverage |
| `stackexchange.search`, python generator | 2 records, 386 words / 2.614 KB | 6 records, 3,548 words / 21.277 KB | Bounded answers added; different records are not independent corroboration |
| Supplemental Apple Q1 2024 release | No matching fresh baseline in this cycle | 753 readable words / 5.149 KB from 1,049 raw words / 7.093 KB | Issuer release text, not its linked financial-statement PDF |
| Supplemental PEP 8 | No matching fresh baseline in this cycle | 1,893 readable words / 12.056 KB | Capped readable capture; not the complete document |

The initial 28-operation metrics-only pass is not a word-count baseline. The
52-operation detailed baseline was collected after adding measurement code but
before structural extraction/answer changes. Later research-window and Reddit
fixes have separately named rechecks; do not relabel every earlier observation
as a run of the final application bytes.

### Complete configured operation inventory

This table is the recorded **52-operation configured pass**, before the final
Reddit semantic correction. `D` counts records explicitly marked discovery-only;
`N` means a network observation in that operation, not that every field was
authenticated. False means no fresh transport was reported, not necessarily no
retained data. Defaults, mirrors, caches and metadata are not interchangeable.

| Operation | Status | Records | Words | KB | D | N |
|---|---|---:|---:|---:|---:|---|
| github.read | SUCCESS | 1 | 4749 | 42.167 | 0 | true |
| github.issues | SUCCESS | 2 | 710 | 5.843 | 0 | true |
| github.prs | SUCCESS | 2 | 97 | 1.146 | 0 | true |
| github.commits | SUCCESS | 2 | 302 | 2.897 | 0 | true |
| github.releases | SUCCESS | 2 | 124 | 2.651 | 0 | true |
| youtube.read | SUCCESS | 1 | 379 | 2.546 | 1 | true |
| youtube.transcript | SUCCESS | 1 | 675 | 4.263 | 0 | true |
| youtube.comments | SUCCESS | 2 | 10 | 0.038 | 0 | true |
| v2ex.latest | SUCCESS | 2 | 79 | 1.978 | 0 | true |
| v2ex.search | SUCCESS | 2 | 95 | 2.065 | 0 | true |
| v2ex.topic | SUCCESS | 1 | 165 | 3.622 | 0 | true |
| v2ex.replies | SUCCESS | 2 | 19 | 0.314 | 0 | true |
| web.read | SUCCESS | 1 | 333 | 2.258 | 0 | true |
| rss.read | SUCCESS | 2 | 374 | 2.523 | 1 | true |
| xiaoyuzhou.podcast | SUCCESS | 1 | 17 | 0.443 | 1 | true |
| xiaoyuzhou.episodes | SUCCESS | 2 | 116 | 4.052 | 0 | true |
| reddit.read | SUCCESS | 2 | 211 | 1.273 | 1 | true |
| reddit.comments | SUCCESS | 2 | 211 | 1.273 | 1 | false |
| twitter.status | SUCCESS | 1 | 5 | 0.024 | 0 | true |
| twitter.profile | SUCCESS | 1 | 16 | 0.133 | 1 | true |
| hackernews.read | SUCCESS | 3 | 184 | 1.053 | 1 | true |
| hackernews.search | SUCCESS | 6 | 484 | 2.888 | 2 | true |
| stackexchange.read | SUCCESS | 3 | 2319 | 13.740 | 0 | true |
| stackexchange.search | SUCCESS | 6 | 3548 | 21.277 | 0 | true |
| sec_edgar.read | CONFIG_REQUIRED | 0 | 0 | 0.000 | 0 | false |
| nist_cve.read | SUCCESS | 1 | 103 | 0.713 | 0 | true |
| arxiv.read | SUCCESS | 1 | 166 | 1.136 | 0 | true |
| fact_check.search | AUTH_REQUIRED | 0 | 0 | 0.000 | 0 | false |
| arxiv.search | SUCCESS | 2 | 514 | 3.730 | 0 | true |
| bilibili.search | SUCCESS | 2 | 35 | 1.431 | 2 | true |
| boss.search_jobs | AUTH_REQUIRED | 0 | 0 | 0.000 | 0 | false |
| facebook.oembed | SUCCESS | 1 | 10 | 0.270 | 1 | false |
| facebook.search | AUTH_REQUIRED | 0 | 0 | 0.000 | 0 | false |
| github.search | SUCCESS | 2 | 23 | 0.284 | 2 | true |
| instagram.oembed | DEGRADED | 0 | 0 | 0.000 | 0 | false |
| instagram.search | AUTH_REQUIRED | 0 | 0 | 0.000 | 0 | false |
| jina_reader.read | SUCCESS | 1 | 333 | 2.258 | 0 | true |
| linkedin.jobs | SUCCESS | 2 | 30 | 0.559 | 2 | true |
| news.search | SUCCESS | 2 | 62 | 0.360 | 2 | true |
| nist_cve.search | SUCCESS | 2 | 104 | 0.675 | 0 | true |
| reddit.search | SUCCESS | 2 | 215 | 1.098 | 0 | true |
| rss.search | SUCCESS | 2 | 32 | 0.214 | 2 | true |
| sec_edgar.search | CONFIG_REQUIRED | 0 | 0 | 0.000 | 0 | false |
| twitter.read | SUCCESS | 1 | 5 | 0.024 | 0 | false |
| twitter.search | SUCCESS | 1 | 16 | 0.133 | 1 | false |
| v2ex.hot | SUCCESS | 2 | 14 | 1.076 | 0 | true |
| web.search | SUCCESS | 2 | 60 | 0.419 | 2 | true |
| web_search.search | SUCCESS | 2 | 59 | 0.410 | 2 | true |
| xiaohongshu.search | AUTH_REQUIRED | 0 | 0 | 0.000 | 0 | false |
| xiaoyuzhou.search | DEGRADED | 0 | 0 | 0.000 | 0 | false |
| xueqiu.search | AUTH_REQUIRED | 0 | 0 | 0.000 | 0 | false |
| youtube.search | SUCCESS | 2 | 72 | 0.455 | 2 | true |

The last eight-operation recheck used the final Reddit correction. `reddit.read`
retained two records / 210 words / 1.264 KB (one removed-comment metadata record
has no body). `reddit.comments` retained two comment observations / **four actual
body words / 0.021 KB**: one was `[removed]` metadata, the other an actual short
question. It did **not** return the 210-word submission as comment text. X status
returned five words / 0.024 KB and its separate profile remained metadata. All
eight rechecked operations reported fresh network observations. This filtered
recheck does not by itself pass a sixteen-operation gate.

### Access context is part of the result

The standalone baseline/two-round default process did not load server `.env`:
Reddit was correctly policy-blocked. The normal application calls `load_dotenv`
at settings initialization and found the previously operator-enabled local
`REDDIT_APPROVED_ACCESS` flag. The configured pass explicitly read that same
existing flag using an allowlist, without printing credentials or changing files.
This explains the different Reddit results; it is **not** new independent proof
of Reddit authorization, a changed default policy or a production setting.
SEC contact and FactCheck credentials remain unavailable. Other credential-gated
sources retain their explicit exclusions. Do not flip flags to improve metrics.

## Frontend and normal agent results

The source display harness rendered **66 actual retained native samples** in the
shared renderer on all four pages at 320/390/1440px. It retained at most two
samples per operation/target, not every follow-up record. The report scaffold is
test-only, not a native agent report or newly invented evidence. Exact inspection
objects were used. Keyboard opening, card/metric counts and unsafe-link checks
were automated. A first 12-state pass falsely looked clean because its overflow
test missed overflowing children hidden by a section. Visual inspection caught
the clipping. The stronger card-boundary check then found **8 failing states**;
the same twelve states had **0 after the grid fix**. Original failed captures
and measurements remain available. This is not WCAG certification.

Separately, twelve real Chromium buttons submitted three inputs per agent to
the real local SSE/backend/acquisition pipeline. All completed HTTP 200 with a
result and 29 progress events each. No uncaught page exceptions, missing findings
or document overflow were detected at 390/1440px. Google Fonts were intentionally
blocked, actual pinned Chart.js bytes served locally. No progress/result stubs.
This run predates the final Reddit comment correction and evidence-grid CSS;
those have focused live rechecks and exact display replay, not an invented
second full twelve-input acquisition run.

| Agent | Input | Records | Words | KB | Discovery cards |
|---|---|---:|---:|---:|---:|
| Scout | TATAMOTORS.NS | 0 | 0 | 0.000 | 20 |
| Scout | INFY.NS | 0 | 0 | 0.000 | 13 |
| Scout | AAPL | 0 | 0 | 0.000 | 3 |
| Trending | OpenAI | 0 | 0 | 0.000 | 0 |
| Trending | NVIDIA | 0 | 0 | 0.000 | 0 |
| Trending | electric vehicles | 0 | 0 | 0.000 | 0 |
| BrandShield | Nike | 0 | 0 | 0.000 | 5 |
| BrandShield | Apple | 2 | 319 | 1.837 | 0 |
| BrandShield | Tata Motors | 0 | 0 | 0.000 | 0 |
| Personal Watch | Sam Altman | 1 | 18 | 0.101 | 0 |
| Personal Watch | Tim Cook | 1 | 8 | 0.059 | 12 |
| Personal Watch | Satya Nadella | 1 | 10 | 0.073 | 0 |

Personal records are short profile observations, not successful impersonation
investigations. Apple records are not independent corroboration. These are
time-varying observations, not controlled before/after recall measurements.
Credential presence does not establish successful live LLM inference.

## Remaining work and acceptance

1. **P1 — Entity research is still sparse.** Diagnose the actual search/selection
   reasons for Scout/Trending first. Do not relax relevance or replace empty
   research with homepage navigation, generic guidance or fabricated narratives.
2. **P1 — Financial evidence depth.** Follow a bounded issuer-linked financial
   statement/PDF and bind metric/period/unit before evaluating net-income claims.
   This work does not add PDF parsing or financial-statement crawling.
3. **P1 — Legacy social transport debt.** Reddit comment reads now use the shared
   bounded transport, but other legacy Reddit post/search/RSS and X mirror paths
   still contain direct `urlopen` implementations. They require a separate
   compatibility-tested migration; this report does not certify every scraper's
   redirect/response-size/cooldown behavior as hardened.
4. **P2 — Source-specific remaining depth.** YouTube captions are not audio
   forensics; podcast show notes are not transcripts; GitHub sampled files are
   not complete diffs; V2EX node lookup is not full-text search; arXiv abstracts
   are not full papers; SEC metadata is not acquired XBRL. Profile, feed and
   discovery observations must remain separate from substantive evidence.
5. **P2 — Continued quality review.** Repeated sampling is implemented, but no
   unattended optimizer/daemon is installed and code does not self-modify. Human
   passage review and an independently annotated relevance denominator are still
   needed before precision/recall or “perfect information” claims.

Protected benchmarks, research/artifacts and historical dossiers remain intact.
Manual screen-reader use, measured contrast, axe, other browsers/real devices,
new independently reviewed accuracy, provider authorization, production parity,
and deployment acceptance are not established by these checks. The implementation
checkpoint's five hosted jobs subsequently passed; see the
[exact publication/CI closeout](../handoffs/2026-10-17_SOURCE_TEXT_PIPELINE_CLOSEOUT.md).
CI does not remove the live research-quality failures.

## Later continuation — 2026-10-19

The [production-failure repair report](PRODUCTION_RESEARCH_FAILURE_REPAIR_2026-10-19.md)
and [handoff](../handoffs/2026-10-19_PRODUCTION_RESEARCH_FAILURE_REPAIR.md) supersede
implementation status for the focused acquisition/contradiction/risk projection
defects, not this historical source-quality evidence. Local 1,498 full / 1,290
fast tests and 12 saved-SSE frontend states pass. No new provider/AI requests,
commit, push or deployment; upstream specialist retrieval and independent
research-quality acceptance remain unverified.
