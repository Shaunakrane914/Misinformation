# Acquisition pipeline improvement plan — 2026-10-16

Status: **PROPOSED implementation backlog**, not delivered functionality or
release acceptance. This makes the existing [Phase 9 plan](PHASE9_EVIDENCE_DEPTH_AND_STRATEGIC_WORKBENCH_PLAN.md)
concrete using the latest diagnostics. No architectural rewrite is proposed.

Implementation update, 2026-10-16: [Slice A is locally implemented and tested](../handoffs/2026-10-16_REPORT_PRESERVATION_IMPLEMENTATION.md).
The remaining slices below are proposed work; no deployment or whole-plan
acceptance is established by that checkpoint.

## 1. Outcome and observed baseline

Turn an ordinary one-line request into a bounded, explainable investigation:
select appropriate sources, acquire meaningful text when available, retain
provenance and uncertainty, and show the same evidence on all four frontends.
Optimize relevant, nonduplicate evidence per request/second, not raw KB or the
number of registered providers. URL-only discovery is a useful intermediate
outcome, but is not successful body extraction or verified claim support.

Observed evidence, not assumed universal provider behavior:

- The October 16 production quick pass exercised 41 operations across 24 channel
  entries, including aliases. The protected set is 16 operations, not 16 sites.
  It was a public-example smoke sample, not a common-query relevance benchmark.
- GitHub reported 57,909 captured characters across five operations, but the
  extraction API exposed only 20.625 KB of selected passages. Words/bytes for
  returned passages must not be advertised as the full acquired document.
- V2EX worked through the local dispatcher, while the production extraction API
  rejected its name because the platform validator excludes digits.
- Stack Overflow returned titles with empty bodies even in a deep follow-up.
  The loss location remains unresolved; inspect upstream fields and downstream
  transformations before selecting a fix.
- HN quick samples were metadata-only; a bounded deep read added two comments,
  1.053 KB / 184 whitespace-delimited words. This is not an external-article read.
- The [local Reddit probe](../handoffs/2026-10-16_LOCAL_REDDIT_PROBE.md) returned
  15 records / 1,124 raw-text words. One feed used RSS; two RSS requests received
  429 and the existing dispatcher used Arctic Shift. This proves a local path,
  not relevance to a one-line claim, archive freshness or production approval.
- The subreddit resolver routes exact inputs Tata Motors / Infosys to generic
  global-equity communities, while Tata Sons gets Indian-market communities.
- Saved four-agent responses reproduce findings lost by report adapters and
  nonzero query records rendered as zero coverage. Scout also maps unavailable
  quotes to zero, drops positive `catalyst` entries when looking only for
  `factor`, and emits timeline fields different from the shared adapter.

The October 16 broad/source probes remain temporary diagnostics, not a durable
benchmark. Preserve dated checkpoint proof and record a new baseline before
tuning. Do not replace historical measurements with newer success-only runs.

## 2. Proposed decisions and boundaries

These decisions are proposed, not an accepted provider/configuration change.

| Decision | Rationale and tradeoff |
|---|---|
| Extend the modular monolith, `SourcePlanningEngine`, native dispatcher and existing research stages | Avoid competing planners or a second scraper stack; existing interfaces need compatibility tests |
| Use deterministic entity/permission validation with bounded optional LLM suggestions through the current gateway | Handles varied language without letting model output authorize a host, credential or arbitrary crawl; fallback must still work without an LLM |
| Keep discovered observations separate from acquired bodies and passage-supported findings | Preserves useful snippets without promoting them to verified evidence; requires explicit UI states |
| Use one versioned acquisition/result contract for all agents | Prevents another four-way field mismatch; migrations must retain old imports and replay compatibility |
| Make access mode, transport, cache and original-source freshness explicit | Local enablement and archive availability cannot be presented as provider approval or direct live access |
| Stay bounded; deepen selected sources, not every website | Reduces noise and rate limits, but cannot promise exhaustive coverage |

Rejected for this workstream: an unconstrained LLM browser agent, fixed fan-out
to every provider, a universal minimum-word success threshold, and a new
Airflow/Kafka/vector-database/microservice deployment. Revisit infrastructure
only after measured concurrency or durability failures justify it.

```text
One-line request
  -> entity + intent + time/region constraints
  -> capability-aware source actions / candidate communities
  -> bounded discovery -> candidate relevance + origin deduplication
  -> selected body reads / context expansion
  -> normalized observations + exact passages + quality checks
  -> claim support / contradiction / uncertainty
  -> canonical report -> four agent views
```

Every step emits an outcome and reason. Failure at a later step must not erase
earlier discovery or silently produce a clean/no-risk conclusion.

## 3. Understanding a one-line request

Extend existing planning contracts rather than introducing another orchestrator.
The following are proposed fields, not an implemented schema:

| Field | Required behavior |
|---|---|
| Original request and request ID | Preserve user wording and correlation; do not replace the question with a presumed true assertion |
| Entities | Canonical identity, aliases, ticker/domain when validated, candidate alternatives and provenance of each mapping |
| Intent / propositions | Verification question versus monitoring; break multiple claims into independently testable questions |
| Region / sector / language | Use explicit user constraints first, then validated issuer/entity metadata; uncertain values remain unknown |
| Time window | Resolve relative language against request time/timezone; distinguish event, publication, retrieval and archive time |
| Evidence needs | Official/primary, independent reporting, community context, contradiction search and required content depth |
| Uncertainty | Ambiguity, missing identifiers and unresolved time/region constraints; ask only when alternatives materially change the investigation |

Use exact URLs/handles and curated aliases first. Extend the planner's existing
bounded LLM suggestion call for structured entity/intent proposals when needed;
validate its output against executable operations, safe URLs, access policy and
budgets. Preserve no-LLM deterministic behavior and explicit degraded parsing.
Do not create one LLM call per community, post or adapter.

Add negative cases for Apple the company versus fruit, Jaguar cars versus the
animal, ticker/name variants, subsidiaries versus parents, multiple entities,
negated claims and prompt injection. Avoid substring sector matching such as
incidental `ai` inside unrelated words. A model suggestion is not identity proof.

## 4. Reddit and other community selection

For the illustrative request "Is Tata Motors falling because of a safety recall?":

1. Resolve company identity, automotive topic, financial question, relevant
   geography and time window. Price movement and recall causation remain
   separate propositions, not assumed facts.
2. Generate candidates from versioned brand, region, sector and topic mappings.
   Indian-market and automotive communities are examples to validate, not a
   guaranteed list of relevant/accessible subreddits.
3. Where access permits, discover additional community/post candidates through
   supported search. Validate actual host, subreddit and post identity; a search
   result on tata.com or Wikipedia fails a Reddit-scoped requirement. Do not
   count a generic Reddit homepage as a relevant post discovery.
4. Rank candidates using entity specificity, geography, topical match, observed
   recent yield, source accessibility and redundancy. Keep rationale and rejected
   alternatives; scores are ranking heuristics, not confidence percentages.
5. In Quick mode, initially inspect at most three communities and a small bounded
   set of posts each. Follow candidate permalinks/context only when relevant.
   Never infer relevant posts merely from community popularity or membership.
6. Require body/title entity alignment plus topic/proposition alignment. Exclude
   removal/deletion markers, navigation, empty link posts and unrelated ticker
   collisions from meaningful-body counts. Keep rejection reasons for audit.
7. Follow only bounded parent/child context with identity checks, permitted
   access and a remaining budget. Stop on provider cooldown, exhausted budget
   or low marginal relevant yield; permit one bounded replan on a documented gap.

Keep a versioned community registry with source of mapping, candidate rationale,
last validation, language/region/topic, observed yield and expiry. It is a prior,
not a truth label. Do not convert temporary EMPTY into permanent exclusion or
automatically learn hardcoded mappings from unreviewed model output.

Separate local diagnostic enablement from configured production access. The
current original-checkout `.env` remains locally enabled by explicit operator
request; this plan does not change it or enable Render. Make RSS, archive and
approved API routes distinguishable, including original post time and archive
observation age when known. No IP rotation, CAPTCHA evasion or rate-limit bypass.

## 5. Source-specific depth work

All channels share contracts but keep source-specific extraction semantics.

| Source group | Next implementation target | Honest success boundary |
|---|---|---|
| Web/search | Preserve search constraints, validate result hosts, read selected original pages and extract main text/sections/tables | URL/snippet success is distinct from relevant body acquisition; preserve redirects/SSRF and decompression caps |
| RSS/news | Preserve feed item identity/date; acquire selected linked articles through the shared reader | Feed summary stays a summary; missing/blocked article bodies remain explicit |
| Reddit | Better entity/community registry, relevant post selection, bounded context, source-mode provenance and cooldowns | RSS is not full-thread coverage; archives are not guaranteed fresh direct Reddit |
| X | Resolve candidate handles, prefer concrete status URLs, preserve sampled text and observable context | Profile bio is metadata, not an investigation of recent posts; public mirror access is not authenticated identity or platform-wide search |
| GitHub | Query-specific issue/PR/commit/release selection, relevant changed-file/comment samples, incremental pagination | README or release text is not whole-repository analysis; retain repository and branch/commit identity |
| YouTube/Bilibili | Separate metadata, available captions, sampled comments and timestamped passages; diagnose current failures per operation | Metadata does not establish transcript/audio/video semantics; restricted captions remain unavailable |
| V2EX | Repair public API platform validation; preserve node/topic/reply semantics and Unicode | Local dispatcher success does not count as deployed API success; node lookup is not unrestricted search |
| Xiaoyuzhou | Preserve show notes, episode identity, dated links and explicitly available text | Episode/audio metadata is not a transcript |
| Hacker News | Distinguish link-story metadata, self text, sampled comments and separately acquired external article | Parent-checked comments and external article are distinct observations |
| Stack Overflow | Trace missing body at provider -> adapter -> fragment -> API boundary; test body-inclusive filter and clean text | Title-only records are not content-read success; answers are a separate bounded operation, not implied |
| SEC/issuer sources | Correct issuer/filing identity and original documents; then period/unit/amendment-aligned facts | Filing indexes and mismatched fiscal periods cannot support financial conclusions |
| NVD/arXiv/FactCheck | Fix transport-observation consistency, acquire appropriate advisory/abstract/review context and original references | Abstracts are not full papers; ratings remain attributed; configured credentials/contact requirements remain explicit |
| Optional authenticated sources | Keep Xueqiu, Xiaohongshu, Instagram, Facebook, Boss and other configured operations in the coverage denominator | Credentials missing is not zero mentions; aliases are not independent sources |

Do not add providers until an unresolved, reviewed case demonstrates a gap.
First fix the existing adapters and actual consumers. Keep all 16 protected
operations and compatibility shims registered throughout the work.

## 6. Preservation and report correctness: first implementation priority

Extend the existing evidence models additively with stable links between query,
candidate, acquisition attempt, captured document and passage. Preserve:

- Original source URL, actual transport endpoint/mode, redirects, cache state,
  relevant status/denial reason, retrieval time and known publication/event time.
- Captured-text hash, exact offsets, language, truncation/caps, and whether a
  body is absent, inaccessible, removed, malformed, irrelevant or metadata-only.
- Independent-origin grouping and alias/syndication deduplication. A report's
  "other reporting" bucket is not proof of independent corroboration.
- Policy-permitted bounded text/structured facts with access-controlled storage
  references; redact PII where appropriate. No indefinite raw-body collection or
  mutation of protected historical dossiers as a prerequisite.

Keep discovery observations in the canonical report even when no deep read
succeeds, with explicit `DISCOVERY_ONLY` use and unresolved body status. Do not
fix empty `evidence` by blindly relabeling all ranked candidates as acquired
documents. Every asserted finding must resolve to its actual captured support;
snippet-only findings need appropriate uncertainty and cannot imply full reads.

Repair all four report adapters against real native payloads: canonical findings,
source lists, grouped factors, actual query records, timeline fields, nullable
market data and quality metadata. Do not manufacture a summary to fill space;
an observed-facts brief may be assembled only from correctly attributed records.
Missing prices/risk assessment must render unavailable/unassessed, not zero/low.

Separate captured totals from returned passages: the eight-passage inspection
cap is a presentation boundary. Expose bounded, authorized pagination/inspection
of retained captured text rather than silently discarding or calling it a full
document. Keep untrusted HTML/text escaped and source-follow-up requests explicit.

## 7. Budgets, reliability and measurements

Introduce one monotonic request deadline propagated into all network attempts,
worker admission, retries, planning and synthesis. Reserve time for body reads
and report assembly so discovery cannot consume the entire investigation.
Increasing the browser timeout alone does not change the current 20–25 second
research defaults or fix deep-read starvation.

Initial **proposed development caps**, to validate before rollout, not current
settings or performance promises:

| Budget | Quick | Deep |
|---|---:|---:|
| Total research deadline | 45s | 120s |
| Source actions | 8 | 16 |
| Candidate records retained for ranking | 20 | 40 |
| Selected body reads | 4 | 10 |
| Initial Reddit communities when relevant and enabled | 3 | 5 |
| Replans | 1 | 1 |

Allocate an initial 20% discovery / 60% acquisition-context / 20% assembly budget
as a development configuration, then adjust against measured latency and useful
yield. Enforce explicit request/page/response/decompressed-byte/text/token caps;
network attempts remain bounded to at most the existing five-second limit and
the remaining stage deadline. Budget the entire request, not five seconds per
unbounded nested fallback. Scheduling overhead and active worker cancellation
must be measured; timeout display is not proof the provider call stopped.

Use low per-host concurrency, bounded global concurrency, request coalescing and
source-specific caches/backoff. A 429 stops further work for that provider until
allowed; an alternate permitted archive observation has separate provenance and
must not be described as a successful retry against the original host. Honor
provider Retry-After/backoff; if it exceeds the request budget, return partial
coverage instead of sleeping indefinitely. Retry at most once for eligible
transient failures within the original budget; never retry permission denials.

Measure per operation and investigation:

- Response bytes versus decoded bytes versus captured UTF-8 text bytes, cleaned
  text bytes, API-returned passage bytes and rendered accessible passage bytes.
- Raw whitespace-token counts versus language-aware segmentation when supported;
  flag CJK/unknown-language limitations. Do not call removal markers useful words.
- Records discovered, body-eligible, attempted, acquired, relevant, deduplicated
  and passage-supported; report denominators and rejection/failure counts.
- Unique relevant words/passages per request and second, metadata-only rate,
  content-preservation loss, unknown dates, archive/cache age and origin reuse.
- Latency distributions, rate limits, admission/cancellation behavior and provider
  health age. Direct-network observation is not original-record freshness.

`body_missing` is an extraction failure only when a body is expected for that
operation; a legitimate profile/link-story metadata response remains metadata
success. Use capability/operation outcomes as the authoritative health source;
remove contradictory legacy-derived available counts without breaking clients.

## 8. Four-agent frontend contract

One canonical report must drive summary, findings, explorer and diagnostics.
Do not mount mutually inconsistent legacy and unified reports indefinitely.
Migrate with compatibility/replay tests, keeping richer captured content usable.

The shared view shows: interpreted request and selected sources; evidence found
versus read versus relevant; primary/other/community provenance; exact passage
links; disagreements; missing sources; time/depth/cache/archive limits; and next
verification steps. Source choices need a human-readable "why selected" label.
Actual progress counts must remain distinct from evidence quality or completeness.

Agent-specific views use the same observations:

- Scout: issuer/event/financial-period alignment, sourced catalysts and competing
  explanations; no causal price narrative from a community mention.
- Trending: sampled narrative clusters, observation windows and origin reuse;
  velocity only from comparable repeated measurements.
- BrandShield: evidence-linked allegations and review priority; similarity is
  not proven impersonation, counterfeiting or coordination.
- Personal Watch: identity candidates and quote context with PII minimization;
  text patterns cannot certify deepfake detection or unauthorized exposure.

Progressive disclosure, responsive layout, keyboard/focus semantics, escaped
text and safe links remain required. Test real populated, snippet-only, partial,
blocked, stale, removed and failed results—not only synthetic loading screens.

## 9. Delivery sequence, tests and acceptance

These are implementation slices, not new claims that Phase 9 is complete.

| Slice / priority | Main owners | Exit evidence |
|---|---|---|
| A / P0: preservation and truth | Report builder, unified schema, agent API adapters, Scout quote fallback, extraction request validator, shared renderer | Saved nonempty native findings/queries/passages survive all four actual API-to-render paths; V2EX accepted; missing quotes stay null |
| B / P1: request understanding and selection | Existing source planner and social resolver | Reviewed one-line cases produce auditable entity/region/topic plans; ambiguity handled; Tata Motors/Infosys no silent generic-only routing; scoped-search host mismatches rejected |
| C / P1: vertical source depth | Web/RSS and Reddit/X handlers, community adapters, deep reader | Relevant public cases retain bodies/context end-to-end; title-only, removed and archive cases remain truthful; diagnose Stack Overflow before claiming a fix |
| D / P1: budgets and reliability | Research budget, stages, network layer and runtime capabilities | Deadline and rate-limit chaos tests; measurable read opportunity; one health source; no duplicate investigation or retry storm |
| E / P2: remaining operations and rich views | Existing platform adapters and four frontend consumers | All 16 protected routes plus optional-source states checked through deployed-shaped APIs; no metadata promoted to transcript/filing content |
| F / P2: evaluation and closeout | Existing audit runners, contract tests and handoffs | Reproducible before/after and bounded repeated live samples; exact-commit CI, browser proof and explicit remaining limitations |

Deliver A first; then B+C as a complete Scout/community vertical slice, sharing
contracts immediately with the other three agents. Source improvements should
reach the actual frontend in each slice rather than waiting for a final UI phase.
Use a single integration owner or isolated worktrees; no concurrent commits
sweeping another agent's unreviewed changes. No delegation is mandated here.

### Evaluation contract

Create new versioned development cases for one-line parsing, community selection,
relevance and field preservation; include unrelated, multilingual, ambiguous,
stale, removed, inaccessible and adversarial cases. Human reviewers should label
acceptable source choices, entity identity and passage relevance. LLM-created
cases/labels must be disclosed and cannot serve as independent accuracy proof.

Use separate locked evaluation cases and replay snapshots. Define numeric
selection/relevance and latency improvement thresholds on development data before
running evaluation, rather than choosing thresholds after seeing results. Keep
all failures/blocked sources in reports. No minimum KB/word quota may force a
false success. Recall stays NOT MEASURED without an annotated denominator.

Non-negotiable automated gates: every displayed citation resolves to the correct
captured observation; every retained native finding maps to a report finding or
an explicit rejection reason; no silent loss across API/UI boundaries; zero
known wrong-host acceptance in scoped-search cases; no fabricated quotes/dates/
prices/source counts; preserved policy and SSRF controls; unchanged frozen data.
These are intended test assertions, not claims about population accuracy.

Start with [source-planner tests](../../tests/unit/test_source_planning_engine.py),
[social-resolution tests](../../tests/unit/test_phase6_8_social_resolution.py),
[extraction API tests](../../tests/unit/test_phase9_extraction_api.py),
[community tests](../../tests/unit/test_phase9_community_sources.py),
[schema tests](../../tests/unit/test_unified_report_schema.py),
[extraction-quality tests](../../tests/unit/test_phase9_extraction_quality.py),
pipeline golden/replay tests, and the shared Node renderer tests. Add actual
native-payload/route-to-DOM regressions; old passing mocks did not catch the loss.

For each implementation slice, run targeted tests first. Before release, run
the full/fast/lint/smoke/rollback commands in [AGENTS.md](../../AGENTS.md), frontend
tests, frozen-data/output checks and exact-head hosted CI. Historical dossier
corruption, missing browser validation and untested live providers remain explicit
limitations, not skipped PASS outcomes. Use new output directories only.

Live monitoring is opt-in, low-frequency and bounded. Extend the current cycle
runner for repeatable scheduled samples only after access/rate budgets and an
owner are established. Do not install an indefinite scraper, self-modifying
optimizer or paid provider through this planning task.

## 10. External contract checks and continuation

Primary references checked on 2026-10-16; these establish constraints, not uptime:

- [Stack Exchange filters](https://api.stackexchange.com/docs/filters): `withbody`
  includes body fields. A missing body in our live path requires diagnosis, not
  an assumption that Stack Overflow has no content.
- [Stack Exchange throttles](https://api.stackexchange.com/docs/throttle): respect
  returned backoff and avoid identical requests more than once per minute.
- [Official HN API](https://github.com/HackerNews/API): distinguish story URLs,
  item text, child IDs and deleted/dead states when sampling context.
- [YouTube caption download](https://developers.google.com/youtube/v3/docs/captions/download):
  this official method requires authorization and video-edit permission; buying
  a generic API key does not guarantee arbitrary-video transcript access.
- [Reddit access guidance](https://support.reddithelp.com/hc/en-us/articles/14945211791892-Developer-Platform-Accessing-Reddit-Data):
  approval/access requirements depend on the use case. The project's boolean
  is not a provider authorization credential. Do not treat unsupported hardcoded
  sunset dates in source comments as verified platform policy.

No production enablement, paid services, credential creation, deployment, data
repair or benchmark-label changes are authorized by this document. Preserve the
existing local flag state and protected datasets/dossiers/research/artifacts.
The implementation owner should begin with Slice A and produce a dated handoff
with source/test pointers, exact commands, observed results and unresolved risks.

Planning verification and Git state are recorded in the [planning handoff](../handoffs/2026-10-16_ACQUISITION_PIPELINE_PLAN.md).
