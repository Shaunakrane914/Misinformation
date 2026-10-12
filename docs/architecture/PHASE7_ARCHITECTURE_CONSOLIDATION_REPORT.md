# Phase 7 architecture consolidation report

> Historical Phase 7 snapshot. Subsequent corrections, compatibility changes, execution evidence and remaining blockers are documented in the [2026-10-12 remediation report](ARCHITECTURE_REVIEW_REMEDIATION_2026-10-12.md) and [coding-agent handoff](../handoffs/README.md). Do not treat the older verification section as the current acceptance gate.

## Result

Phase 7 consolidated confirmed ownership overlaps without moving or deleting working integrations. The four agents and public compatibility imports remain intact.

## Execution graph

`Agent objective → QueryPlanningStage → SourcePlanningEngine → RuntimeOperationCapabilities → AgentReachService.retrieve_many → NativeRouter / ChannelQueryDispatcher → provider handler / NativeExecutor → normalizer → ResearchPipeline qualification, independence, expansion, reading, synthesis → agent presentation`

Ownership after Phase 7:

| Concern | Authority |
|---|---|
| Source and operation selection | `SourcePlanningEngine` |
| Query wording diversity | `RetrievalPlanner`, bounded to channels selected by the source planner |
| Operation eligibility, auth, policy, freshness | `RuntimeOperationCapabilities` |
| Dispatch | `NativeRouter` and `ChannelQueryDispatcher` |
| Provider I/O | provider handlers and `NativeExecutor` using the shared bounded transport |
| Evidence shape and depth | normalizers and dispatcher outcome classification |
| Relevance, independence, expansion, synthesis | `ResearchPipeline` stages |
| User-facing status | operation-health API plus the shared frontend presenter |

## Duplicates and defects found

1. Credential requirements existed in the standard handler, runtime capability service, and source planner. They now derive from `required_auth_environment()`; compatibility maps remain materialized for import stability.
2. Adaptive follow-ups consulted the legacy query planner but ignored recent operation-level failures. They now skip excluded or temporarily deferred `channel.search` operations and disclose the skip.
3. Identical normalized provider requests with different query IDs were submitted more than once. They are now deduplicated before fan-out.
4. Web, Jina, RSS, V2EX, GitHub REST, and podcast paths had inconsistent redirect and body-size behavior. ADR 0008 defines their common boundary.
5. A V2EX topic URL could resolve to topic `2` by matching the digit in `v2ex.com`. Topic IDs now come only from an all-numeric value or `/t/<id>` path.
6. `web.read` reported Jina as the requested channel. Requested `web` and actual `jina_reader` are now distinct.
7. Agent pages inferred provider health from channel-wide status or hardcoded green badges. All four now summarize required operations.
8. The server reported an obsolete hardcoded version and did not retain/cancel its RSS task. Both were corrected.

## Preserved components

- All 16 restored operations and their existing public schemas.
- Four agent entry points and deterministic integration fixture boundary.
- Source planner, legacy retrieval planner query-diversity role, and one-replan bound.
- Compatibility shims under `backend/services/agent_reach/` and Scout source shims.
- Legacy fallbacks where they provide unique behavior.
- Frozen retrieval scenarios, candidates, labels, and tracked benchmark summaries.

## Remaining debt

- Runtime operation observations are process-local and do not converge across multiple workers.
- Several non-core/limited adapters still use provider-specific clients; they remain disclosed and were not broadened into fake direct access.
- Channel-level `CapabilityRegistry` remains for compatibility and registration, while operation eligibility is authoritative in `RuntimeOperationCapabilities`.
- Compatibility shims and unused legacy strategies need owner-approved removal only after downstream caller evidence is available.

## Verification

Baseline: 624 tests passed at `e5d64f7`. Phase 7 preservation started at `6a72861`; transport hardening is `5c24498`; access/planning consolidation is `2208b82`; operation-level UI is `7caccf9`; readiness controls are `81026dd`.

