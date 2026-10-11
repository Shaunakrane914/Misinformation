# ADR 0007: Expiring runtime operation capability state

## Status

Accepted for Phase 6.9.1 on 2026-10-11.

## Context

The upstream declaration catalogue, production dispatcher, channel Doctor, and
Source Planning Engine previously answered different questions. A declared
operation could have no handler, an implemented handler could lack credentials,
and a channel-level success could conceal that another operation was blocked or
metadata-only. Static capability checks therefore spent research budget on
operations that could not satisfy the task.

## Decision

`RuntimeOperationCapabilities` is the operation-level capability view. It
composes, rather than replaces, existing authorities:

- `CAPABILITY_MATRIX` owns upstream declarations.
- `EXECUTABLE_CAPABILITIES` owns the tested production dispatch contract.
- environment and policy checks are evaluated for every planning decision.
- the acquisition dispatcher and Doctor remain the source of observed outcomes.
- operation observations record content class, transport observation, cache
  state, HTTP status when known, timestamp, and temporary failure state.

Healthy observations expire after 15 minutes, ordinary failures after 90
seconds, and rate limits after 180 seconds by default. An expired failure becomes
eligible for a bounded recovery probe; it does not permanently disable the
provider. A later success immediately supersedes a failure. A cache-only result
does not overwrite a prior network-health observation.

The Source Planning Engine evaluates required evidence depth as well as access.
It prefers recently verified operations, permits bounded unknown/stale probes,
deprioritizes cache-only evidence, and excludes unsupported, auth-missing,
policy-blocked, depth-insufficient, or temporarily failed actions. Every decision
is serialized in `source_plan.runtime_decisions`.

Reddit direct operations remain policy-blocked unless
`REDDIT_APPROVED_ACCESS=true` is explicitly configured. This flag records an
owner/operator access decision; it is not a credential bypass.

## Recovered dispatch contract

Phase 6.9.1 connected existing executor or public-API implementations for GitHub
repository/issue/PR/release/commit reads, YouTube read/transcript/comments, V2EX
latest/search/topic/replies, RSS reads, web reads, and public podcast discovery.
`web_search.search` is a compatibility alias of the canonical web search path,
not a second network client.

## Consequences

- Capability API responses expose operation-level truth alongside channel-level
  summaries.
- Credentials added or removed during a process are recognized without restart.
- The existing legacy `RetrievalPlanner` remains temporarily responsible for
  query diversity and later novelty rounds. `SourcePlanningEngine` owns source,
  operation, policy, depth, and one bounded evidence-gap replan.
- Runtime observations are process-local. Cross-process/Redis propagation is a
  documented limitation, not required for the current single-process scope.
- Default cooldowns are conservative because provider `Retry-After` parsing is
  not yet uniform across every adapter.

