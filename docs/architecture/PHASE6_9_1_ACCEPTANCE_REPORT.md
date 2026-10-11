# Phase 6.9.1 runtime source intelligence acceptance report

## Decision

**Phase 6.9.1: PASS WITH LIMITATIONS. Phase 7 remains NOT AUTHORIZED pending
owner approval of the product scope below.**

The implementation audit began at `5475696a5275f4771dd5e44dda99c7469118bd84`.
The final permitted live acquisition run was captured from
`f7aa96ff7a3b3ae6c276e9c4b86d8872bc231da8` in
`artifacts/phase6_9_1_capability_audit/2026-10-11_00-55-42Z/`.

## A. Architecture findings and fixes

| Finding | Severity | Disposition |
|---|---|---|
| Planner equated a static handler allowlist with runtime usability | High | Added operation-level runtime assessment of handler, auth/policy, depth, observation, freshness, cache, rate limit, and task suitability |
| Doctor observations were channel-wide | High | Retained Doctor as observation authority but indexed planning state by `channel.operation` |
| Temporary failures could become sticky if consumed as permanent health | High | Added expiring success/failure/rate-limit state and recovery probes |
| Credentials were effectively startup assumptions | High | Environment eligibility is evaluated on every decision; add/remove transitions are tested |
| Cache hits could be mistaken for current provider health | High | Cache-only observations cannot overwrite a prior network observation |
| Existing executor methods were stranded behind search-only dispatch | High | Recovered 16 of the 37 previously unimplemented routes |
| `web_search.search` had no production handler | High | Registered it as a compatibility alias to the existing web-search implementation |
| Public LinkedIn guest jobs and podcast RSS were hidden behind channel-wide auth guards | Medium | Made access operation-specific; direct profile/session operations remain blocked |
| Source planner `replan()` existed but was not called by the research pipeline | High | Connected one bounded replan to no-result, missing-primary, insufficient-independence, and metadata-only gaps |
| Legacy `RetrievalPlanner` overlaps the shared planner | Medium | Responsibilities are now explicit, but the compatibility layer remains until Phase 7 |
| Frontend is channel-level while API truth is operation-level | Medium | No false-green regression found; detailed operation visibility remains a UI limitation |
| Provider cooldowns do not uniformly parse `Retry-After` | Medium | Conservative expiring defaults implemented; header-specific backoff remains future work |
| Runtime state is in-memory per process | Medium | Acceptable for current deployment; distributed propagation is documented, not fabricated |

## B. Reconciled 37-operation matrix

`Live tested` refers only to the final bounded public run. Controlled dispatcher
tests cover every restored path independently of live provider state.

| Operation | Existing implementation | Recoverability / restriction | Restored | Live tested | Classification | Disposition |
|---|---|---|---|---|---|---|
| `bilibili.hot` | No executor | New provider work; low initial-scope value | No | No | NOT_IMPLEMENTED | INTENTIONALLY_DEFERRED |
| `bilibili.rank` | No executor | New provider work | No | No | NOT_IMPLEMENTED | INTENTIONALLY_DEFERRED |
| `bilibili.read` | Search metadata only | Direct read needs a distinct verified API path | No | No | NOT_IMPLEMENTED | INTENTIONALLY_DEFERRED |
| `boss.read_jd` | Declaration/legacy CLI references | Requires approved CDP browser session | No | No | AUTH_OR_POLICY_BLOCKED | Defer until owner enables provider |
| `facebook.feed` | Indexed fallback only | Direct feed requires approved Meta access/session | No | No | AUTH_OR_POLICY_BLOCKED | Do not advertise as executable |
| `facebook.groups` | No direct handler | Login/platform restrictions | No | No | AUTH_OR_POLICY_BLOCKED | Do not advertise as executable |
| `facebook.profile` | Indexed discovery/oEmbed adjacent | Direct profile access restricted | No | No | AUTH_OR_POLICY_BLOCKED | Keep indexed discovery separate |
| `github.commits` | Public REST capability | Safe to route through bounded GitHub REST | Yes | No | IMPLEMENTED_AND_ROUTED | Experimental until live exercised |
| `github.issues` | Earlier REST audit code | Safe public REST; PR records filtered from issues | Yes | Yes | IMPLEMENTED_AND_ROUTED | Core candidate |
| `github.prs` | Public REST capability | Safe to route through bounded GitHub REST | Yes | No | IMPLEMENTED_AND_ROUTED | Experimental until live exercised |
| `github.read` | Existing CLI read | Added public REST fallback and README retrieval | Yes | Yes | IMPLEMENTED_AND_ROUTED | Core candidate |
| `github.releases` | Public REST capability | Safe to route through bounded GitHub REST | Yes | Yes | IMPLEMENTED_AND_ROUTED | Core candidate |
| `instagram.explore` | No direct handler | Session/provider restriction | No | No | AUTH_OR_POLICY_BLOCKED | Do not advertise as executable |
| `instagram.posts` | oEmbed only for explicit posts | Feed/posts contract requires approved access | No | No | AUTH_OR_POLICY_BLOCKED | Keep oEmbed separate |
| `instagram.profile` | Indexed discovery only | Direct profile restricted | No | No | AUTH_OR_POLICY_BLOCKED | Keep indexed discovery separate |
| `linkedin.company` | Indexed fallback only | Direct company access requires session/provider approval | No | No | AUTH_OR_POLICY_BLOCKED | Guest jobs remain separate |
| `linkedin.profile` | Indexed fallback only | Direct profile access requires session/provider approval | No | No | AUTH_OR_POLICY_BLOCKED | Guest jobs remain separate |
| `linkedin.read` | No general direct reader | Session/provider restriction | No | No | AUTH_OR_POLICY_BLOCKED | Defer |
| `rss.read` | Existing executor and normalizer | Safe URL validation already present | Yes | No | IMPLEMENTED_AND_ROUTED | Limited syndicated evidence |
| `twitter.feed` | No confirmed feed executor | Official X access required; mirror is status/profile only | No | No | AUTH_OR_POLICY_BLOCKED | Do not infer feed from profile metadata |
| `v2ex.latest` | Earlier public API audit | Stable public JSON endpoint | Yes | Yes | IMPLEMENTED_AND_ROUTED | Core candidate |
| `v2ex.replies` | Earlier public API audit | Stable topic-replies endpoint | Yes | Yes | IMPLEMENTED_AND_ROUTED | Core candidate |
| `v2ex.search` | Existing node lookup executor | Operation is node lookup, not global full-text search | Yes | No | IMPLEMENTED_AND_ROUTED | LIMITED with naming caveat |
| `v2ex.topic` | Public API existed in audit code | Restored with correct `id` parameter after live 404 exposed defect | Yes | Yes | IMPLEMENTED_AND_ROUTED | Core candidate |
| `web.read` | Existing safe reader/Jina path | Was routed under a separate reader alias | Yes | Yes | IMPLEMENTED_AND_ROUTED | CORE |
| `xiaohongshu.comments` | Legacy/OpenCLI references | Requires approved authenticated session | No | No | AUTH_OR_POLICY_BLOCKED | Defer |
| `xiaohongshu.feed` | Legacy/OpenCLI references | Requires approved authenticated session | No | No | AUTH_OR_POLICY_BLOCKED | Defer |
| `xiaohongshu.read` | Indexed fallback only | Direct read requires approved session | No | No | AUTH_OR_POLICY_BLOCKED | Keep indexed discovery separate |
| `xiaoyuzhou.episodes` | Existing iTunes/RSS executor/normalizer | Public podcast syndication; no transcript claim | Yes | No | IMPLEMENTED_AND_ROUTED | LIMITED alias of podcast discovery |
| `xiaoyuzhou.podcast` | Existing iTunes/RSS executor/normalizer | Public podcast syndication | Yes | Yes | IMPLEMENTED_AND_ROUTED | LIMITED |
| `xiaoyuzhou.transcribe` | Configuration/legacy references only | Requires Groq key and a bounded audio pipeline | No | No | AUTH_OR_POLICY_BLOCKED | Defer; never infer transcript from show notes |
| `xueqiu.hot_posts` | Generic visitor-client code adjacent | Application policy requires configured cookie | No | No | AUTH_OR_POLICY_BLOCKED | Defer |
| `xueqiu.hot_stocks` | Generic visitor-client code adjacent | Application policy requires configured cookie | No | No | AUTH_OR_POLICY_BLOCKED | Defer |
| `xueqiu.quotes` | Visitor API code can normalize quotes | Not separately routed; policy requires configured cookie | No | No | AUTH_OR_POLICY_BLOCKED | Recover only after owner access decision |
| `youtube.comments` | Existing yt-dlp executor/normalizer | Explicit video URL, bounded comments | Yes | Yes | IMPLEMENTED_AND_ROUTED | LIMITED community evidence |
| `youtube.read` | Existing specialized router read | Metadata only, not transcript | Yes | Yes | IMPLEMENTED_AND_ROUTED | LIMITED |
| `youtube.transcript` | Existing yt-dlp executor | Full content when subtitles exist; absence is valid | Yes | Yes | IMPLEMENTED_AND_ROUTED | CORE candidate with reliability caveat |

Summary: **16 restored**, **18 auth/policy blocked**, and **3 intentionally
deferred/not implemented**. In addition, `web_search.search` was consolidated as
an alias, `xiaoyuzhou.search` was aligned with public podcast discovery, and
LinkedIn guest jobs were separated from session-only LinkedIn operations.

## C. Runtime-aware planner evidence

The runtime evaluator distinguishes declared, implemented, eligible, observed,
fresh, depth-suitable, and temporarily unavailable states. Tests cover:

- healthy to rate-limited to stale/recoverable;
- failure followed by immediate successful recovery;
- metadata rejection when full content is required;
- never-tested operations remaining eligible but unverified;
- credentials added and removed without restart;
- cache hits preserving prior network health;
- Reddit policy blocking;
- runtime exclusions serialized into source-plan telemetry.

The research pipeline now calls the shared one-replan budget when actual evidence
has no relevant results, primary evidence, independent corroboration, or adequate
content depth. Only newly added actions execute, with a six-item/one-query-per-
channel bound. Legacy novelty expansion remains independently bounded.

## D. LLM planner evaluation

The reproducible evaluation is under
`artifacts/phase6_9_1_planner_evaluation/2026-10-11_00-55-41Z/` and covers nine
required scenarios. No model credentials were configured. Every hybrid request
failed closed to the deterministic plan with `llm_status=FALLBACK`; no mock model
output was accepted, and token/cost claims remain null.

**Decision:** deterministic planning remains the default. Hybrid value is
`BLOCKED`/unverified until a configured live model can be compared on retrieval
quality, not merely plausible plans.

## E. Updated live capability audit

The final run executed 30 representative operations. Adapter-level network
observations were preserved for 23 operations. Highlights:

- direct content: web/Jina reads, GitHub read/issues/releases, YouTube transcript
  and comments, V2EX latest/topic/replies, and an explicit mirrored X status;
- metadata/limited: YouTube search/read, Bilibili search, X profile;
- discovery/syndication: web aliases and news/RSS feeds;
- public limited integrations: LinkedIn guest jobs and podcast RSS show notes;
- blocked: Reddit direct access plus absent Xueqiu, Xiaohongshu, Instagram,
  Facebook, and Boss sessions.

The full 62-operation assessment reports 21 declared-but-unimplemented, 10
unverified executable, 11 observed direct-content, 4 direct-metadata, 4
partial/unclassified, 2 syndicated-summary, 2 search-index, 5 auth-required, and
3 policy-blocked records. These categories overlap the 30 live probes and
inventory-only rows exactly as recorded; they are not claims of permanent
provider reliability.

## F. Initial product scope recommendation

### CORE

- `web.read` / `jina_reader.read`
- GitHub `search`, `read`, `issues`, and `releases` with REST rate-limit handling
- V2EX `latest`, `topic`, and `replies`
- X explicit `status` through the disclosed public mirror

### LIMITED

- `web.search` and `web_search.search` as discovery only
- `news.search`, `rss.search`, and `rss.read` as syndicated summaries
- YouTube `search`/`read` as metadata and `transcript` only when subtitles exist
- YouTube `comments` as non-authoritative community evidence
- Bilibili search metadata
- X profile metadata and indexed keyword discovery
- LinkedIn public guest jobs
- Xiaoyuzhou podcast/search/episodes as metadata and show notes, never transcript
- V2EX node-based `search`

### EXPERIMENTAL

- GitHub `commits` and `prs` until a final live exercise is retained
- newly recovered routes after provider-schema changes or expired observations
- optional LLM source planning

### BLOCKED

- Reddit `search`, `read`, and `comments` without approved access
- direct X feed/search requiring official provider access
- Xueqiu direct operations without the configured policy-approved session
- LinkedIn profile/company/read
- Xiaohongshu, Instagram feed/profile, Facebook feed/profile/groups, Boss direct
  JD access, and Xiaoyuzhou transcription without their required access

### DEFERRED

- Bilibili hot/rank/read
- every other declaration lacking a production handler and current product need

## G. Acceptance report

| Criterion | Status | Evidence / limitation |
|---|---|---|
| 1. Which 37 operations were recoverable? | PASS | 16 recovered; each remaining operation classified above |
| 2. Existing implementations restored? | PASS | Executor-backed GitHub, YouTube, V2EX, RSS, web, and podcast paths reach production dispatch |
| 3. Planner recognizes temporary blocks/unhealthy operations? | PASS | Rate-limit/failure freshness tests and serialized runtime decisions |
| 4. Planner/provider can recover? | PASS | Expiry and immediate-success recovery tests |
| 5. Adaptive replanning connected to real workflow? | PASS | Research pipeline evidence-gap trigger with strict single-replan budget |
| 6. Hybrid LLM improves quality? | BLOCKED | No configured live model; deterministic fallback is not improvement evidence |
| 7. All four agents execute resulting plans? | PASS | Existing real-entry-point integration test remains green in 624-test matrix |
| 8. Registry/router/API/frontend consistent? | PARTIAL | Runtime/API/router truth aligned; frontend remains honest but channel-level rather than operation-level |
| 9. Operational limitations identified? | PASS | Provider access, process-local health, backoff header gaps, metadata/show-note limits documented |
| 10. Exact pre-Phase-7 scope defined? | PASS | CORE/LIMITED/EXPERIMENTAL/BLOCKED/DEFERRED proposal above; owner approval still required |

## Verification

- Final post-correction full local matrix: **624 passed** on Python 3.13.5 in
  216.85 seconds.
- Focused acquisition/runtime/recovery/planner contract suite: **110 passed**.
- Compile and changed-file fatal lint checks passed.
- Frozen retrieval benchmark inputs and tracked benchmark summaries were not
  modified.
- GitHub Actions: **PASS** for head
  `dd8deb28402e18f32d98f454ef527f6f9e791025` in run
  [38100690873](https://github.com/Shaunakrane914/Misinformation/actions/runs/38100690873):
  lint, Python 3.11/3.12/3.13 unit and chaos jobs, and provenance/performance
  benchmarks all passed.

