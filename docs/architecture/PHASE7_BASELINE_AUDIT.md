# Phase 7 baseline and preservation audit

## Baseline

- Branch point: `e5d64f76b94239483352f022dab2948bb837144a`
- Protected implementation branch: `feat/phase7-production-hardening`
- Worktree at branch creation: clean and synchronized with
  `origin/feat/retrieval-quality-benchmark`
- Last verified upstream workflow: GitHub Actions run `38100690873`
- Local runtime: Python 3.13.5 and Node.js 22.17.1
- Pre-change regression result: **624 passed** in 327.83 seconds
- Frozen retrieval benchmark inputs and tracked summaries: unchanged

Phase 7 begins from the approved restricted v1 scope. This report does not
authorize deployment, provider-access bypasses, or destructive legacy removal.

## Current execution graph

```text
API / four agent entry points
  -> SourcePlanningEngine (source and operation selection)
  -> RetrievalPlanner compatibility layer (bounded query diversity)
  -> ResearchPipeline / ScoutSourceEngine
  -> AgentReachService / CapabilityRegistry
  -> NativeRouter / ChannelQueryDispatcher
  -> StandardChannelHandlers / SocialChannelHandlers
  -> NativeExecutor or provider adapter
  -> NativeNormalizer / EvidenceFragment
  -> relevance, independence, ranking, adaptive expansion
  -> synthesis, dossier, replay lineage, API response, frontend
```

`backend.services.agent_reach.adapter` and
`backend.services.agent_reach.native.router` are identity-preserving compatibility
shims. The Scout modules under `backend/services/agent_reach/scout/` are also
compatibility exports for the canonical `backend/agents/scout/sources/` modules.
They are still used by tests and monkeypatch targets and are not removal-safe.

## Recovered-operation dependency map

The public API has a dedicated `/read` surface for web reads and generic
research/debug entry points for planned operations. It does not expose a generic
arbitrary provider-operation endpoint. “API route” below therefore names the
actual supported entry rather than implying a public operation RPC.

| Operation | API / entry | Registry channel | Router / dispatcher | Executor or adapter | Normalization and evidence | Agent consumers |
|---|---|---|---|---|---|---|
| `github.read` | research/debug | `GitHubChannel` | standard GitHub operation handler | GitHub REST operation | handler creates `EvidenceFragment`, full article when README exists | all shared-pipeline agents and Scout |
| `github.issues` | research/debug | `GitHubChannel` | standard GitHub operation handler | GitHub REST issues | handler, direct content | all agents |
| `github.prs` | research/debug | `GitHubChannel` | standard GitHub operation handler | GitHub REST pulls | handler, direct content | all agents; experimental |
| `github.commits` | research/debug | `GitHubChannel` | standard GitHub operation handler | GitHub REST commits | handler, direct content | all agents; experimental |
| `github.releases` | research/debug | `GitHubChannel` | standard GitHub operation handler | GitHub REST releases | handler, direct content or metadata | all agents |
| `youtube.read` | research/debug | `YouTubeChannel` | standard YouTube handler | router `yt-dlp` read | handler, video metadata | all agents |
| `youtube.transcript` | research/debug | `YouTubeChannel` | standard YouTube handler | `execute_youtube_transcript` | handler, video transcript | all agents when subtitles exist |
| `youtube.comments` | research/debug | `YouTubeChannel` | standard YouTube handler | `execute_youtube_comments` | `normalize_youtube_comments`, comments | all agents; non-authoritative context |
| `v2ex.latest` | research/debug | `V2EXChannel` | standard V2EX handler | V2EX public latest endpoint | `normalize_v2ex_topics`, direct content | all agents |
| `v2ex.search` | research/debug | `V2EXChannel` | standard V2EX handler | V2EX node endpoint | `normalize_v2ex_topics`, direct content | all agents; node lookup limitation |
| `v2ex.topic` | research/debug | `V2EXChannel` | standard V2EX handler | V2EX topic endpoint | `normalize_v2ex_topics`, direct content | all agents |
| `v2ex.replies` | research/debug | `V2EXChannel` | standard V2EX handler | V2EX replies endpoint | `normalize_v2ex_topics`, comments | all agents |
| `web.read` | `/api/agent-reach/read`, research deep read | `WebChannel` | standard web handler to reader path | safe web executor plus retained fallbacks | reader fragment, full article or snippet | all agents |
| `rss.read` | research/debug | `RssChannel` | standard RSS handler | safe RSS executor | `normalize_rss_entries`, syndicated summary | all agents |
| `xiaoyuzhou.podcast` | research/debug | authenticated-optional registry shell with public operation exception | standard Xiaoyuzhou handler | iTunes discovery plus public podcast RSS | `normalize_xiaoyuzhou_episodes`, metadata/show notes | all agents; limited |
| `xiaoyuzhou.episodes` | research/debug | same as podcast | same as podcast | same public discovery/RSS executor | same normalizer and limited depth | all agents; limited alias |

All sixteen operations flow through `ChannelQueryDispatcher`, which applies
operation telemetry, provenance defaults, outcome depth classification, Doctor
observation, and `RuntimeOperationCapabilities` observation recording.

## Confirmed architecture findings

| Finding | Severity | Phase 7 disposition |
|---|---|---|
| `web.read` overwrote its requested channel with `jina_reader` | High evidence-integrity defect | Preservation test added and lineage corrected; actual provider remains `jina_reader` |
| The 16-operation regression suite did not independently exercise `xiaoyuzhou.episodes` or assert complete provenance | High regression gap | Exact 16-operation inventory and per-route provenance assertions added |
| Raw HTTP paths implement redirects, response limits, timeouts, and rate-limit behavior inconsistently | High reliability/security risk | Consolidate the CORE/LIMITED public HTTP boundary before touching providers |
| URL validation occurs before several clients that automatically follow redirects | High SSRF risk | Require validation for every redirect and final endpoint at the adapter boundary |
| Runtime rate-limit observations use a fixed cooldown and ignore observed `Retry-After` | Medium | Parse bounded provider guidance and retain conservative defaults |
| `SourcePlanningEngine` and `RetrievalPlanner` both generate queries | Medium | Preserve compatibility; make ownership explicit and deduplicate at the pipeline boundary rather than rewriting the legacy planner |
| Capability declaration, registration, Doctor state, and runtime operation state are separate authorities | Medium | Keep declarations separate; make runtime operation state the API/UI decision authority |
| Credential names/policies are repeated in registration and standard handlers | Medium | Centralize operation access policy while preserving public operation exceptions |
| Frontend status remains primarily channel-level | Medium truthfulness risk | Add an operation-aware presentation contract without a major UI rewrite |
| Runtime health is process-local | Documented limitation | Retain for v1 single-process scope; document multi-worker consequences |

## Initial removal-candidate register

No removal is performed in Phase 7 without owner approval.

| Component | Current callers | Replacement / redundancy evidence | Coverage and rollback | Recommendation |
|---|---|---|---|---|
| `backend/services/agent_reach/adapter.py` | API, tests, legacy imports and monkeypatches | Re-exports canonical infrastructure service | identity contract tests; restore shim trivially | retain compatibility shim |
| `backend/services/agent_reach/native/router.py` | tests and legacy imports | Re-exports infrastructure router and scraper hook | architecture invariant tests | retain compatibility shim |
| `backend/services/agent_reach/scout/` | Scout agent, tests, patch targets | Re-exports canonical `backend/agents/scout/sources/` | Phase 5 compatibility and golden tests | retain; migration candidate only |
| `RetrievalPlanner` query generation | research pipeline and agent-specific code | overlaps structured planner but still supplies query diversity and adaptive follow-ups | broad regression and golden coverage | retain until a separately approved migration proves equivalent quality |
| legacy web/news scraper fallbacks | router and reader fallback paths | unique outage behavior remains | chaos and fallback tests | retain; isolate and disclose fallback use |

## Baseline acceptance

The baseline is suitable for incremental hardening. It is not yet a production
readiness decision because redirect-boundary security, provider retry semantics,
operation-aware UI truthfulness, and the final post-change regression/CI matrix
remain unverified.
