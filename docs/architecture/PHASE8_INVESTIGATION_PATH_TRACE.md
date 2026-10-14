# Phase 8 production investigation path trace

Captured on 2026-10-12 before Phase 8 implementation. This is a code-path
inventory, not proof that every external provider is available.

## Executed path

| Step | Production owner | Principal hand-off |
|---|---|---|
| Claim request | `backend/api/claims.py` | `POST /api/claims/verify` validates and normalizes the user claim. |
| Claim decomposition | `ClaimIngestionAgent` | Normalized text, claim identity and atomic claims. |
| Research entry | `ResearchAgent` / `ResearchEngine` | A typed `ResearchRequest` enters the application pipeline. |
| Query and source planning | `QueryPlanningStage`, `RetrievalPlanner`, `SourcePlanningEngine` | Capability-aware `QueryPlan` with bounded channel actions. |
| Broad acquisition | `BroadDiscoveryStage`, canonical `agent_reach_service` | `retrieve_many()` executes planned channel queries. |
| Runtime selection | `RuntimeOperationCapabilities` | Operation eligibility, auth, depth and recent health decision. |
| Provider dispatch | `NativeRouter` -> `ChannelQueryDispatcher` | Standard/social handler chosen for a normalized operation. |
| Network boundary | `NativeExecutor`, bounded HTTP transport or allowlisted tool | Redirect-safe, size-limited public request or bounded `yt-dlp`/`gh` process. |
| Normalization | Native normalizer -> `EvidenceFragment` | Provider payload becomes the shared acquisition record. |
| Qualification | relevance gate and source-quality engine | Candidate accepted/rejected with quality annotations. |
| Independence and ranking | source-independence engine and candidate ranker | Syndication families and ranked evidence. |
| Deep reading | primary escalation and deep-reading stages | Bounded direct reads and passage extraction. |
| Analysis | contradiction, evidence graph and grounded synthesis stages | Findings, contradictions, integrity and lineage graphs. |
| Persistence | corpus assembly and dossier registration | Research corpus and replay/dossier lineage. |
| API presentation | claims API and four domain-agent routers | Backward-compatible and unified report shapes. |
| Frontend | static agent workspaces plus unified report renderer | Claim, verdict, evidence, health and provenance views. |

## Ownership findings

- The authoritative transport boundary is the infrastructure acquisition
  router, even though compatibility imports remain under
  `backend.services.agent_reach`.
- The research pipeline owns cross-domain evidence qualification and synthesis.
  Scout, Trending, BrandShield and Personal Watch own domain-specific planning
  and presentation, but their primary paths all enter the shared research and
  acquisition layers.
- Operation health is global, in-memory process state. It is intentionally
  ephemeral, but audit runners must isolate probes so a single edge-case target
  does not defer every subsequent target for the operation.

## Remaining architecture risks

1. The synchronous `/api/claims/verify` work is invoked from an `async` route.
   Its research call can perform synchronous provider work and should be moved
   to a worker boundary during the intelligence/API phase.
2. The claims API and several agents reconstruct or reshape evidence after the
   shared pipeline. These compatibility projections can discard provider fields
   and should not become a second source of truth.
3. Some agent fallback paths perform direct news or radar retrieval when the
   research pipeline returns no evidence. They preserve truthful limitations,
   but do not receive every shared ranking and quality annotation.
4. Provider payload richness is compressed into `EvidenceFragment`; Stage 8B
   must account for every lost or optional field before changing UI contracts.
5. `RuntimeOperationCapabilities`, the canonical acquisition service and the
   research engine are singletons. Their shared state is useful for runtime
   health, but dependency injection would improve test isolation and multi-
   worker observability.

## Decisions carried into Phase 8

- Preserve the modular-monolith boundary and compatibility shims.
- Measure provider truth at the adapter boundary; never infer HTTP success from
  a normalized fragment.
- Keep discovery, syndicated summaries, metadata and direct content distinct.
- Do not redesign the frontend until extraction and intelligence contracts are
  measured and stable.
