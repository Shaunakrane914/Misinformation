# ADR 0006: Capability-aware shared source planning

## Status

Accepted for pre-Phase-7 implementation on 2026-10-10.

## Context

The four research agents previously generated broad, largely static channel
queries. The provider capability catalogue also mixed upstream aspirations with
operations that the application can actually route. This created unnecessary
fan-out and allowed a declared capability, an HTTP response, metadata, a feed
summary, and direct evidence to look too similar.

The same entity needs different evidence for different claims. An Nvidia product
availability claim needs first-party product material and specialist hardware
reporting; an Nvidia revenue-integrity claim needs filings, investor relations,
and independent financial reporting. A model can help interpret ambiguous intent,
but it must not authorize a network operation or declare that a provider works.

## Decision

Add one shared `SourcePlanningEngine` between research intent and the existing
acquisition boundary.

- Deterministic logic classifies common intent, creates a staged plan, assigns
  stable action IDs, enforces channel/operation allowlists, checks explicit URLs,
  validates subreddit candidates, limits actions and queries, and permits at most
  one non-recursive replan.
- Optional suggestions reuse the existing LLM Gateway and are disabled by
  default. Suggestions are schema-validated and then subjected to the same
  deterministic policy checks. Timeout, invalid JSON, or an unavailable model
  falls back to the deterministic plan. Mock output is not accepted.
- Explicit safe URLs bypass the LLM and retain their concrete operation, such as
  `twitter.status` or `reddit.comments`.
- Scout uses the planner at the shared acquisition service entry point.
  BrandShield, Trending, and Personal Watch use it through the shared research
  pipeline. Agent identity affects priority and rationale, not capability truth.
- Retrieval outcomes remain the authority on what was actually acquired. Plans
  express expected evidence and limitations; they never assert success.

## Alternatives considered

1. Four agent-specific planners: rejected because it duplicates policy and lets
   capability truth diverge.
2. A fully autonomous research loop: rejected because it adds cost and recursive
   failure modes without evidence that one bounded replan is insufficient.
3. Extend only the legacy `RetrievalPlanner`: rejected because it combines query
   generation with domain defaults and has no structured operation, exclusion,
   budget, or validation contract.
4. LLM-only planning: rejected because model output cannot establish provider
   availability, identity, policy, or network facts.

## Consequences

The application now has auditable source selection and materially less irrelevant
fan-out. Identical source actions are deduplicable across agents. The architecture
still has two planning layers during compatibility migration, and several
platform operations remain declarations only. Runtime health is observation-based,
so an unprobed route remains `NOT_PROBED` rather than green.

The planner may recommend Reddit discussion with explicit limitations, but the
2026-10-10 live audit did not perform Reddit direct-content probes without
approved Data API access. Provider policy remains a runtime constraint, not a
planner override.
