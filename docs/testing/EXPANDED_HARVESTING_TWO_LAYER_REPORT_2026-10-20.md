# Expanded harvesting and two-layer evidence pipeline — 2026-10-20

Later continuation: [four-agent intelligence and browser report](FOUR_AGENT_COMPLETION_2026-10-20.md).
The measurements below remain the original expanded-harvesting checkpoint.

## Decision

**The zero-article acquisition failure is no longer universal.** A normal Samsung
query autonomously acquired **seven article bodies / 6,544 retained article words**
from six publisher hosts in 26.85s. A separate Sundar Pichai query acquired **five
article bodies / 4,161 words** in 46.83s. Neither was supplied article URLs; both
post-fix investigations used **zero AI calls**.

**Engineering implementation and offline regression: PASS within the scope below.
All-four-agent research-quality acceptance: PARTIAL. Deployment remains blocked.**
This is not independent financial, identity, threat or virality verification.
BrandShield's original live response failed after acquisition; Trending acquired
old reporting, not fresh trend evidence. Later status, attribution, promotion and
API-scope budget corrections have offline proof, not another live rerun.

Worktree: `.scratch/phase9-remediation-20261016`; branch
`fix/p0-lenovo-acquisition-20261018`; base HEAD
`39a514b68388450bbc5e6061aba97bda2077fc7f`, plus preserved inherited dirty work.
No commit, push, merge, deployment, credential or access-flag change.

[Selected measured proof](evidence/2026-10-20_expanded_harvest/measurements.json) ·
[evidence scope](evidence/2026-10-20_expanded_harvest/README.md) ·
[next-agent handoff](../handoffs/2026-10-20_EXPANDED_HARVESTING.md).

## Implemented flow and capacity

```text
normal query + capability-validated specialist actions
  -> diverse bounded search waves
  -> observed publisher URLs / feeds / sitemaps / archive links
  -> bounded article reads + raw acquisition pool
  -> strict body/entity/objective/date/passage qualification
  -> qualified-only specialist inputs + existing shared report
```

The acquisition-first path is the runtime default (`STANDARD`), not merely an
audit script. All four API request models also accept `research_profile`.
Explicitly constructed legacy `ResearchBudget()` instances retain the old path
unless a profile is selected; this preserves existing integration/golden contracts.

| Profile | Candidate ceiling | Generated queries | Read attempts | Total ceiling | Logical operation ceiling | Native HTTP admissions |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| QUICK | 24 | 6 | 6 | 60s | 24 | 40 |
| STANDARD | 60 | 12 | 14 | 150s | 48 | 80 |
| DEEP | 100 | 18 | 24 | 240s | 80 | 120 |

These are maxima, not promised results. Caller/server overrides may lower them.
The separately approved post-fix checks used **180s / 16 reads / 80 native HTTP
admissions** each. Socket calls remain bounded; modes do not disable SSRF, access,
cooldown, size or provider limits. DEEP reads at most four sources concurrently,
one per publisher host, with up to eight host reads and short bounded spacing.
Opaque Google wrappers have a three-attempt ceiling. Discovery/index reads have
separate caps, and candidate capacity is reserved for observed continuation links.

Native HTTP admissions include native retries and redirects and are shared across
copied worker contexts. Admission is not proof a remote server received a request;
the counter is not complete network/billing accounting. Per-host native admission
cap is 24. Logical service-operation counts are separately labeled. Late workers
cannot append to the closed investigation or open more admitted native requests.

Six task angles are diversified across existing web/news/RSS categories. The
existing Bing news RSS surface can yield observed publisher URLs before the Google
feed fallback. Existing capability-approved auxiliary channels may consume up to
two existing query slots; this does not dispatch every operation for every query.
Reddit/X are not forced into all research, and no approval flag was enabled.
The protected sixteen operation routes remain registered and contract-tested.

## Code and rationale

| Component | Implementation |
| --- | --- |
| [Profiles](../../backend/services/research/research_profiles.py), [budget](../../backend/services/research/research_budget.py) | Immutable QUICK/STANDARD/DEEP bounds; default runtime profile and backward-compatible explicit legacy serialization |
| [HarvestingEngine](../../backend/services/research/harvesting.py) | Multi-query waves, task-aware ranking, candidate/read/host quotas, reserved continuation capacity, explicit failure/unsubmitted records, optional validated advisory query |
| [Harvest orchestration](../../backend/application/research/harvest_pipeline.py), [pipeline dispatch](../../backend/application/research/pipeline.py) | Populate raw pool before strict filtering, retain rejection reasons, send only usable qualified bodies to specialists, export structural metrics rather than legacy article guesses |
| [RawAcquisitionPool](../../backend/services/research/raw_pool.py), [corpus model](../../backend/services/research/research_models.py) | Stable IDs/aliases, exact text hashes, revisions/duplicates, query IDs, observed dates, transport/errors, raw text and separate qualification decisions; optional owned-temp persistence |
| [Bing URL resolver](../../backend/services/agent_reach/native/source_discovery.py) | Decode only known Bing redirect envelopes into actually observed target URLs; ordinary percent-encoded URIs remain unchanged |
| [DeepReader](../../backend/services/research/deep_reader.py) | Injected budgeted service, bounded concurrency, validated redirect endpoint attribution, canonical IDs retained through reads, no snippet-to-body promotion |
| [Page extraction](../../backend/infrastructure/acquisition/adapters/web/page_extraction.py), [XML discovery](../../backend/infrastructure/acquisition/adapters/web/discovery_document.py), [publisher links](../../backend/services/research/publisher_links.py) | Semantic/CMS/articleBody extraction; RSS/Atom/news sitemap/index/archive discovery with observed URLs and date provenance; no guessed article slugs, XML DTD/entities or lastmod-as-publication |
| [Native executor](../../backend/services/agent_reach/native/executor.py), [reader adapter](../../backend/infrastructure/acquisition/adapters/web/jina.py) | Propagate body structure/hash/method/word metadata; challenge/denial does not trigger alternate-route retrieval; ordinary CDN mentions are not challenge pages |
| [HTTP budget](../../backend/infrastructure/acquisition/network/budget.py), [HTTP transport](../../backend/infrastructure/acquisition/network/http.py), [shared service](../../backend/infrastructure/acquisition/service.py) | Shared thread-safe request admissions, copied worker context, redirect/retry accounting and closed-budget protection |
| [Content roles](../../backend/services/research/content_roles.py), [passages](../../backend/services/research/passage_extractor.py), [attribution](../../backend/services/research/passage_records.py) | Strict rejected-body guard, promotional giveaway versus abuse context, exact acquired-article quotation attribution independent of discovery query names; no identity authentication |
| [BrandShield dossier](../../backend/agents/brandshield/dossier.py), [assessment](../../backend/agents/brandshield/assessment.py), [Scout assessment](../../backend/agents/scout/assessment.py) | Structured/legacy claim compatibility; promotional reports are not attackers; crypto solicitation remains investigable; bare “profit” no longer means positive performance |
| [Agent API](../../backend/api/agents.py), [SSE](../../backend/api/research_stream.py), [progress client](../../frontend/agent-research-client.js), [report builder](../../backend/services/report_builder.py), [renderer](../../frontend/unified-report-renderer.js) | Request-local modes; one shared advisory identity across multiple passes in one scan; actual harvest counts, variable stage totals, honest statuses and inspectable discovery leads; minimal UI change |
| [Terminal runner](../../scripts/audits/run_terminal_agent_quality.py), [raw replay CLI](../../scripts/audits/requalify_raw_pool.py), [measurement CLI](../../scripts/audits/summarize_raw_harvest.py) | Isolated live acquisition, explicit bounds/AI opt-in, offline raw qualification and read-only measurements without repeated network requests |

### Raw pool is not another findings list

Ten types are explicit: `DISCOVERY_LEAD`, `SOURCE_INDEX`, `PUBLISHER_HOMEPAGE`,
`FEED_ENTRY`, `ARTICLE_BODY`, `OFFICIAL_DOCUMENT`, `STRUCTURED_PUBLIC_DATA`,
`COMMUNITY_POST`, `BACKGROUND_REFERENCE`, `BLOCKED_OR_FAILED`.

Unknown captured pages remain non-article; snippets have no readable body. Article
classification requires observed extraction structure, not length alone. An
official-document label does not independently authenticate ownership or content.
The current harvester retains at most 12,000 readable characters per page, with
truncation disclosure; “article body” does not promise the complete remote article.

Default pool limits: 300 records, 20MB serialized data, 1MB per source, bounded
histories; harvester captures have an additional 400,000-character cap in DEEP.
Original body/hash/context survives qualification. Persistence is opt-in, atomic
and restricted to newly owned system-temp trees. Cleanup validates ownership and
touches only files that pool created. Imported pools never gain cleanup ownership.
No automatic deletion of historical evidence or research/artifact trees occurs.

## Five-case before/after: first authorized DEEP batch

The preceding [overhaul](P0_AUTONOMOUS_RESEARCH_OVERHAUL_2026-10-20.md) acquired zero
new qualified articles. The table reports new live acquisition, not retrospective
rewriting of that baseline. Raw-body counts are structural extraction observations,
not independent truth or current specialist relevance.

| Agent / query | Before useful current article bodies | New bodies / retained article words | Saved qualified / useful passage words | Outcome |
| --- | ---: | ---: | ---: | --- |
| Scout / Samsung | 0 | 2 / 1,274 | 1 / 60 | Real Rediff/CNBC text, but colliding IDs make the saved citations unacceptable; corrected afterward |
| Scout / Unilever | 0 | 3 / 4,121 | 2 / 92 | Actual corporate articles, one duplicate capture; one publisher group, not independent corroboration |
| BrandShield / Adidas | 0 | 5 captured page texts / 2,950 words in isolated dossier, not verified article-body metadata or returned API output | Not accepted | Article-shaped Hypebeast product/lifestyle URLs; API failed `claim_text` during packaging; promotion was not threat proof |
| Trending / grid-scale energy storage | 0 | 1 / 843 | 0 / 0 | Acquired article was dated 2023; strict 48-hour abstention remains correct |
| Personal Watch / Sundar Pichai | 0 | 1 / 783 | 0 / 0 | Substantive article, but quotation blocked by legacy query-class boundary; later fixed offline |

For Adidas, five captured texts/hashes and URLs are recoverable from the **new
isolated dossier's** candidate snapshots and lineage. They are not a successful
returned response or independently verified extraction metadata. The selected JSON
leaves missing returned-pool measurements null rather than inventing them.

| Query | Seconds | Unique candidate URLs | Reader attempts | Successful raw captures | Native HTTP admissions |
| --- | ---: | ---: | ---: | ---: | ---: |
| Samsung | 56.69 | 40 | 24 | 16 | 83 |
| Unilever | 61.62 | 34 | 21 | 15 | 81 |
| Adidas | 39.30 | Not retained in returned response | Not retained | Not retained | Not retained |
| grid-scale energy storage | 68.69 | 20 | 11 | 7 | 80 |
| Sundar Pichai | 110.63 | 44 | 13 | 8 | 87 |

These fixed inputs are calibration cases, not held-out independent accuracy
evaluation. All five requests ran once; no automatic audit retries. Both batches
kept stable application fingerprints within their own runs, recorded in proof.

## Failures exposed and repaired

1. **First batch citation collision:** legacy `EvidenceFragment.__post_init__`
   stripped meaningful query strings, so different Bing news click URLs shared
   one evidence ID. The raw-pool alias then joined several sources to the first
   article's qualification. The harvesting boundary now assigns full-canonical-URL
   identities before any finding, preserves ambiguous upstream IDs as non-citation
   metadata, and safely decodes known observed Bing envelopes. Old captures and
   bad citations are unchanged, not retroactively declared correct.
2. **Raw-to-specialist leakage:** legacy classifiers inspected every downloaded
   page, even rejected pages. The specialist boundary now receives qualified-only
   source items. All raw text remains in the pool; structural metrics replace the
   old `SUBSTANTIVE_CANDIDATE` article-count shortcut.
3. **BrandShield projection:** `dossier.py` assumed every claim had `claim_text`.
   It now supports documented structured text shapes with preserved evidence IDs,
   and skips absent prose rather than fabricating it. Product giveaways without
   incident context cannot become a risk merely via the giveaway keyword; actual
   crypto/credential solicitation remains investigable.
4. **Misleading empty-result status:** filtering all articles out made the older
   assembly helper infer that no body was read. Final status now uses raw capture
   observations: successful acquisition with insufficient qualification differs
   from failed retrieval. The post-fix Pichai saved SSE predates this correction.
5. **Personal statement boundary:** a genuine acquired article explicitly quoted
   the full subject, but `harvest_impersonation` was not an old statement query
   class. A narrow actual-article/full-speaker/quotation path now retains an
   attributed source assertion. Snippets, profiles, other speakers, fabricated,
   negated, misattributed and debunked quotations remain excluded.

The last two corrections, final promotion policy and API-wide advisory identity
were verified offline after the two extra checks; no later live result is claimed.

## Separately authorized post-fix live checks

| Input | Seconds | URLs / attempts / raw captures | Article bodies / article words | Qualified / useful passage words | Article publisher hosts |
| --- | ---: | ---: | ---: | ---: | ---: |
| Samsung | 26.85 | 29 / 16 / 11 | **7 / 6,544** | **7 / 787** | 6 |
| Sundar Pichai | 46.83 | 39 / 16 / 12 | **5 / 4,161** | 0 / 0 in saved live result; **1 / 76** after offline attribution repair | 5 |

Samsung used 68 native HTTP admissions; Pichai 79, each below 80. Both used no AI.
Samsung's six structured findings have six citation references, each uniquely
resolving to a qualified article record, with no source-ID collision. This proves
join validity, **not** citation entailment or independent financial correctness.
Pichai's five articles prove acquisition, not five identity-threat investigations.

The full Pichai saved pool was requalified offline without new requests: one
explicit quotation survives as `REPORTED_QUOTATION` / `UNVERIFIED`, with exact
passage offsets. The original live response remains unchanged. A repository
regression retains only a 17-word partial excerpt plus original body hash/count;
full article captures stay in temporary storage.

### Real article examples from the post-fix Samsung query

All are automatically discovered and natively read HTTP-200 publisher pages,
`ARTICLE_BODY`, `PARTIAL_CONTENT`, method `DOM_SEMANTIC_TEXT`. Dates below are
publisher declarations, not independently authenticated timestamps.

| Publisher / source | Observed publication | Retained body words |
| --- | --- | ---: |
| [Korea Times](https://www.koreatimes.co.kr/business/companies/20261008/samsung-electronics-1st-korean-firm-to-top-80-bil-in-quarterly-operating-profit) | 2026-10-07T22:55:03Z | 765 |
| [Business Standard](https://www.business-standard.com/companies/news/samsung-sees-record-80-bn-quarterly-profit-as-ai-chip-demand-surges-126100801254_1.html) | 2026-10-08T19:13:07+05:30 | 856 |
| [Ad-hoc News](https://www.ad-hoc-news.de/boerse/news/corporate-news/samsung-electro-mechanics-stock-faces-chip-selloff-before-earnings/70359108) | 2026-10-19T09:11:41+02:00 | 563 |

Different hosts may reuse the same wire or corporate account. Samsung affiliates,
financial periods, forecast versus reported figures and currencies still need
proposition-level review. None of these source assertions is endorsed as investment
advice or independently verified truth by this engineering check.

## AI usage

One non-generation capability lookup confirmed the exact configured
`gemini-3.5-flash-lite` model before the five-case run. **Two actual generation
attempts**, one each for Adidas and Pichai, returned 200: 389+84=473 and
396+83=479 provider-reported tokens, **952 total / 167 output**. Neither output
exceeded 160 tokens. No retry, key/model fallback or extra quota probe occurred.
The unused third-call allowance was not spent. Monetary cost was not measured.

Adidas advice returned no extra retained candidates; a causal retrieval gain from
Pichai advice was not established. The improvement is not credited to AI. Both
post-fix checks and all ordinary tests/requalification used zero live generation.
API-level investigation scope now prevents multi-pass scans reopening the
one-call allowance. Existing SQLite reservation/cooldown policy remains intact.

## Validation actually run

| Check | Result |
| --- | --- |
| `python -m pytest tests/ -q` | **1,695 passed / 34.91s**, exit 0 |
| `python -m pytest tests/unit tests/chaos tests/security -q` | **1,487 passed / 26.76s**, exit 0 |
| Fatal flake8 E9/F63/F7/F82 | Zero findings, exit 0 |
| Nine frontend Node scripts | All exit 0; static/DOM contracts, not rendered acceptance |
| Frozen verifier / protected-path diff | Hashes match; protected data unchanged |
| New report/runbook/handoff links and selected JSON | Relative targets resolve; JSON parses; scoped scan found no full-body fields or credential-shaped values |
| Release smoke | OFFLINE_SMOKE_PASS, exit 0 |
| Rollback validator | OFFLINE_PERSISTENCE_PASS, exit 0; historical archive/deployed rollback NOT_VERIFIED |
| Five-case live runner | Exit 1 due to BrandShield error; stable code, not a passing batch |
| Two-case post-fix runner | Exit 0 transport; stable code; research limitations above remain |
| Raw-pool replay | Exit 0 with zero network/model calls; old ambiguous aliases require explicit opt-in disambiguation |

115 additional offline controls cover the new harvesting/pool/extraction,
projection, attribution and requalification boundaries. They are supporting
evidence, not live source recall or independent accuracy labels.

Smoke and persistence were rerun against the final application into fresh
`smoke-verified.json` and `rollback-verified.json` in the run's temporary directory.
Both exited 0; historical archive and deployed rollback remain NOT_VERIFIED.
A separate read-only closeout review cross-checked selected measurements and
corrected Adidas wording to avoid claiming unverified article-body metadata.

An earlier full/fast run had 18 failures: incompatible null profile serialization,
old default/size/challenge expectations, trace assumptions and an overbroad
promotional guard. Those failures were resolved with scoped code/test corrections;
no golden manifest or frozen benchmark was regenerated. A mistyped new test path
collected no tests, then the correct path passed. An initial strict import correctly
rejected the first batch's ambiguous aliases; explicit offline disambiguation now
retains original raw records while excluding ambiguous aliases from joins. It does
not repair old citations/verdicts. All intermediate failed outputs remain in temp.

## Remaining acceptance gates and release status

- **Trending:** old provider results despite freshness hints; no fresh 48-hour
  article set or measured narrative velocity demonstrated. Keep abstention.
- **BrandShield:** product/lifestyle capture is not threat discovery. The packaging
  crash and promotion leak have offline regressions, but no post-fix live Adidas
  response or representative confirmed-threat/negative-case matrix was authorized.
- **Personal Watch:** five real bodies acquired; one attributed statement retained
  offline. False-quote/impersonation accuracy and identity/media forensics are not
  established, nor is that offline correction a new live result.
- **Scout:** seven bodies and unique citation joins demonstrate acquisition. Lead
  passage usefulness, affiliate disambiguation, financial direction and claim
  entailment still need independent review. A minor metric-token boundary edge
  remains in the conservative heuristic polarity parser.
- **Release:** no final rendered browser/accessibility matrix, hosted CI, production
  parity, independent held-out accuracy, deployed rollback or historical corrupt
  dossier recovery was performed. The earlier 55-file issue is not silently fixed.

All seven authorized investigations and both actual advisory calls are accounted
for. No more live retries, source sweeps, AI calls or deployment are authorized by
this closeout. Future live work needs a new small case/request envelope.

Full redacted source/events/logs, new isolated dossiers, optional owned-temp raw
snapshots and gate logs remain under the new system-temp run basename
`aegis-expanded-harvest-976b78ac9bad4aa1a362ab1cd9d3339c` or explicitly referenced
owned raw-pool snapshots. Temp storage can expire. Durable proof contains selected
metadata/hashes, not republished full articles. Historical reports remain dated
snapshots. This document records engineering decisions/results, not private
reasoning or an invented verbatim execution transcript.
