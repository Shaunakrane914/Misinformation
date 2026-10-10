# Pre-Phase-7 architecture and acquisition readiness report

## Decision

**Pre-Phase-7 corrective work: PASS with documented limitations. Phase 7: NOT
AUTHORIZED by this report.** The shared acquisition path is materially more
truthful and the source planner is integrated, but Phase 7 should wait for an
owner decision on whether the 37 declared-but-unimplemented operations are to be
removed from the product contract or implemented, plus an approved Reddit access
strategy if Reddit direct discussion is a product requirement.

This audit was performed from baseline commit
`3e0302e14b910d5169d599dc9238476793abcc21` on branch
`feat/retrieval-quality-benchmark`. The final bounded live record was captured
from implementation commit `4d102b2ea11cedb824b8ffa092047ff59b6675ba` under
`artifacts/pre_phase7_audit/2026-10-10_14-33-26Z/`. It contains 62
per-operation records: 20 representative probes and 42 inventory-only records.

## Architecture map

```text
HTTP/API request
  -> Scout | Trending | BrandShield | Personal Watch
  -> SourcePlanningEngine (claim/agent intent, bounded validated plan)
  -> ResearchPipeline or ScoutSourceEngine
  -> AgentReachService.retrieve_many / execute
  -> CapabilityRegistry -> NativeRouter -> ChannelQueryDispatcher
  -> SocialChannelHandlers | StandardChannelHandlers
  -> NativeExecutor / Reddit, X, web adapters
  -> EvidenceFragment + provenance + transport observation
  -> relevance gate -> source independence/ranking -> deep read
  -> synthesis/dossier/replay lineage -> API response -> frontend status
```

BrandShield, Trending, and Personal Watch share `ResearchEngine` and its staged
pipeline. Scout enters through `AgentReachService.execute` and `NativeRouter`.
Both paths now use the same source planner and acquisition runtime. The existing
LLM Gateway is optional planning assistance only; deterministic validation owns
execution authority.

## High-priority findings and disposition

| Finding | Baseline evidence | Disposition |
|---|---|---|
| Declared operations exceeded production routing | The 16-channel upstream matrix advertised 60 operations; the router implemented a smaller query-oriented surface | Fixed at the API boundary: declared and executable operations are separate. Audit: 37 `UNAVAILABLE_NOT_IMPLEMENTED`, 5 unexercised routes |
| False-green startup state | Registry initialized channels as available; Doctor hard-coded Reddit/X as healthy | Fixed: new state is `NOT_PROBED`; Doctor health is based on observed outcome depth |
| Transport success conflated with evidence success | Generic `SUCCESS` could mean snippets, metadata, or feed entries | Fixed: `DIRECT_CONTENT`, `DIRECT_METADATA`, `SYNDICATED_SUMMARY`, `SEARCH_INDEX_DISCOVERY`, `AUTH_REQUIRED`, `BLOCKED`, `EMPTY`, and `UNAVAILABLE_NOT_IMPLEMENTED` are distinct |
| Fabricated benchmark transport | Phase 6.8 runner assigned HTTP 200, inferred content type, and `FRESH_NETWORK` | Fixed: transport fields come from adapter observations; unknown remains unknown; canonical URL and requested endpoint are separate |
| Plain `Anthropic` treated as `@Anthropic` | Literal-handle logic ran before entity resolution | Fixed: only explicit `@handle` is literal; plain names resolve first and mismatched acquired identities are rejected |
| Weak four-agent test | Previous test instantiated agents and checked synthetic fields | Fixed: controlled integration test calls the real BrandShield, Trending, Personal Watch, and Scout production entry points and injects only at the shared acquisition boundary |
| Reddit RSS boilerplate counted as body | `submitted by`, `[link]`, and `[comments]` inflated usable text | Fixed before usable-character calculation |
| Cached social records retained fresh-network semantics | Some cache returns reused original fragment metadata | Fixed for X and Reddit adapter caches using copies marked `CACHE_HIT` and `network_observed_this_attempt=false` |
| LinkedIn credential name diverged by layer | Registry used `LINKEDIN_SESSION_COOKIE`; router, audits, and existing scripts used `LINKEDIN_COOKIE` | Fixed: one credential contract now reaches registration and dispatch |
| RSS SSRF check tested a tuple as a boolean | Unsafe RSS URLs could reach the fetch call | Fixed: unpack and enforce `(safe, reason)`; regression test covers cloud metadata URL |
| Walled-garden fallback could be mislabeled | Search snippets could appear as platform content | Fixed: host allowlist, `WEB_SEARCH_INDEX`, `INDEX_SNIPPET`, and fallback disclosure are required |
| Static frontend readiness labels | Trending rendered providers as “Ready”; other agents treated coarse availability as green | Fixed: unobserved is “Not tested”; limited/degraded/auth states are not green |

## Empirical capability summary

The 2026-10-10 bounded live run performed permitted public operations only. Ten
representative operations preserved adapter-level network observations. Results
are observations for that run, not permanent provider guarantees.

| Channel.operation | Observed result | Depth / health | Access and limitation |
|---|---|---|---|
| `web.search` | 3 Bing index results, HTTP 200 observed | Search-index / degraded | Discovery only; snippets are not source bodies |
| `news.search` | 3 Google News RSS entries, HTTP 200 | Syndicated summaries / limited | Feed excerpts, not publisher articles |
| `rss.search` | 3 Google News RSS entries, HTTP 200 | Syndicated summaries / limited | Feed excerpts only |
| `jina_reader.read` | Nvidia page content, 3,999 normalized chars, HTTP 200 | Direct content / healthy | Public page read; endpoint and canonical URL recorded separately |
| `github.search` | 3 repositories through REST fallback, HTTP 200 | Partial/unclassified / degraded | `gh` unavailable; REST fallback disclosed |
| `youtube.search` | 3 video records | Direct metadata / limited | External tool observed network use; HTTP status unavailable |
| `v2ex.hot` | 3 public API topics, HTTP 200 | Partial/unclassified / degraded | Public API; query is a local filter over hot topics |
| `bilibili.search` | 3 videos, HTTP 200 | Direct metadata / limited | Metadata, not video body/transcript |
| `twitter.profile` | 1 FxTwitter profile, HTTP 200 | Direct metadata / limited | Third-party mirror; profile is not a tweet timeline |
| `twitter.status` | 1 explicit status body, HTTP 200 | Direct content / healthy | Third-party mirror; explicit public status URL |
| `reddit.search`, `reddit.comments` | Not probed | Blocked | No approved Reddit Data API access was configured |
| Seven credential-gated probes | No evidence | Auth required / blocked | LinkedIn, Xueqiu, Xiaohongshu, Instagram, Facebook, Boss, Xiaoyuzhou credentials absent |
| `web_search.search` | No handler, no evidence | Empty / unsupported | Declared upstream but not registered as a production channel |

The complete per-platform/per-operation table, including backend, endpoint,
transport, content depth, item count, usable characters, canonical URLs,
fallback, failure, latency, cache state, and health, is the machine-readable
`operation_results.jsonl` beside the run summary. Inventory totals were:

- 2 direct-content observations
- 3 direct-metadata observations
- 2 syndicated-summary observations
- 1 search-index observation
- 2 partial/unclassified observations
- 7 authentication-required probes
- 2 policy-blocked probes
- 1 empty route
- 37 declared but not implemented operations
- 5 executable routes not exercised by the bounded live run

## Source planner behavior

The deterministic plan changes with the claim. “Nvidia is discontinuing the RTX
5090” prioritizes official product material, specialist hardware reporting,
hardware discussion, and technical video metadata. “Nvidia manipulated its
quarterly revenue” prioritizes SEC/issuer filings, official disclosures,
independent financial reporting, and clearly non-authoritative investor
discussion. Tata Sons financial claims use SEBI context. Agent-specific actions
add trend signals, brand-risk searches, or public identity monitoring without
changing capability truth.

Plans contain stable action IDs, stage, concrete operation, query, expected
depth, rationale, authority flag, limitations, exclusions, and budgets. The
default limits are 10 actions, 3 queries per channel, one optional LLM call, one
non-recursive replan, and a 2.5-second planner timeout. Unsupported operations,
unsafe URLs, unverified subreddits, and auth-only channels are rejected.

## Provider and compliance constraints

- Reddit’s current Data API documentation requires OAuth, approval, and rate
  limit compliance. Reddit announced on 2026-10-08 that new public API access
  requests stop on 2026-10-31 and existing public API access is phased out in
  2027. Direct probes were therefore skipped without approved access:
  [Data API Wiki](https://support.reddithelp.com/hc/en-us/articles/16160319875092-Reddit-Data-API-Wiki),
  [developer access](https://support.reddithelp.com/hc/en-us/articles/14945211791892-Developer-Platform-Accessing-Reddit-Data),
  [2026-10-08 changelog](https://support.reddithelp.com/hc/en-us/articles/54353370049684-Changelog-October-8-2026).
- X’s official search APIs require an approved developer account/app and
  credentials; recent and archive search are distinct paid capabilities:
  [X API overview](https://docs.x.com/x-api/getting-started/about-x-api),
  [post search](https://docs.x.com/x-api/posts/search/introduction). This run used
  FxTwitter only for a public profile and one explicit public status and labels it
  as a mirror.
- YouTube’s official Data API requires a project, API key/OAuth as appropriate,
  and quota accounting: [YouTube Data API](https://developers.google.com/youtube/v3/getting-started).
- GitHub documents 60 unauthenticated REST requests per hour and 5,000 per hour
  for primary authenticated users; clients must handle rate limits and avoid
  excessive polling: [rate limits](https://docs.github.com/en/rest/using-the-rest-api/rate-limits-for-the-rest-api),
  [best practices](https://docs.github.com/en/rest/using-the-rest-api/best-practices-for-using-the-rest-api?apiVersion=2026-03-10).

## Acceptance gates

| Gate | Status | Evidence / remaining limitation |
|---|---|---|
| Architecture traced through all four agents | PASS | Production paths documented and exercised with boundary fixtures |
| Complete declared-versus-executable inventory | PASS | 62-operation artifact; declarations no longer equal implementation |
| False-success semantics removed | PASS | Outcome depth and observation-based health replace generic green |
| Real transport provenance | PASS | Populated only from adapter boundary; unknown stays unknown |
| Anthropic identity regression | PASS | Plain entity resolves; explicit handle remains literal; mismatch rejected |
| RSS body-quality correction | PASS | Boilerplate stripped before usable text count |
| Shared source planner | PASS | Integrated across all four real entry paths with deterministic validation |
| Bounded fallback/replanning | PASS | One replan, stable dedupe, action/query limits, deterministic LLM fallback |
| Live public acquisition smoke test | PARTIAL | 10 observed network operations; Reddit blocked and auth providers unavailable |
| Every declared operation live-tested | UNVERIFIED | 37 not implemented and 5 not exercised; neither is reported as healthy |
| Direct Reddit comments | BLOCKED | Approved access absent; zero comments claimed |
| X status acquisition | PASS | One explicit status body observed; search/timeline coverage remains unverified |
| Four-agent deterministic execution | PASS | Real agent methods, acquisition-boundary fixture |
| Full local CI-equivalent suite | PASS | 598 unit, chaos, security, integration, and benchmark tests passed on Python 3.13.5 in 400.26s |
| GitHub Actions matrix | PASS | [Run 38060120013](https://github.com/Shaunakrane914/Misinformation/actions/runs/38060120013) passed lint, Python 3.11/3.12/3.13 unit-security-chaos jobs, and provenance/performance benchmarks for commit `3d4bce72eaef82f60b814259b288b3168b7d472f` |

## Final answers

1. Aegis can currently retrieve public web-page bodies, an explicit mirrored X
   status, public V2EX topic content, web/search discovery, news/RSS summaries,
   repository search results, and video/profile metadata. These depths are now
   labeled separately.
2. Reddit direct discussion is blocked in this audit. The credential-gated
   platforms cannot currently provide evidence in this environment. Thirty-seven
   declared operations lack a production execution path.
3. Reddit/X bootstrap health, static frontend “Ready” badges, registered
   capabilities, generic `SUCCESS`, indexed fallbacks, and hardcoded benchmark
   HTTP fields could previously imply more than was proven.
4. The audit fixed those false signals, wrong identity ordering, benchmark
   fabrication, RSS boilerplate, cache provenance, RSS SSRF enforcement, fallback
   host validation, and the weak four-agent test.
5. The planner interprets claim intent, selects staged source categories, applies
   agent priorities, then deterministically validates capability, identity, URL,
   auth, and budgets. Optional LLM output is only a candidate proposal.
6. Yes. Hardware and financial claims about Nvidia generate materially different
   source plans; Tata claims use Indian regulatory context.
7. Yes, through actual production methods with a controlled acquisition-boundary
   fixture. This is deterministic integration evidence, distinct from live
   provider testing.
8. Yes for populated transport fields. Missing observations remain null/unknown;
   normalized byte counts are not network byte counts.
9. Reddit policy/approval, X official search credentials and pricing, YouTube API
   credentials/quota, GitHub rate limits, and all absent platform sessions remain
   external constraints.
10. Phase 7 should not begin until product scope resolves the declared-operation
    gap and decides whether Reddit direct discussion is required. The architecture
    is ready for that decision; the unsupported capabilities are not ready to be
    advertised as implemented.
