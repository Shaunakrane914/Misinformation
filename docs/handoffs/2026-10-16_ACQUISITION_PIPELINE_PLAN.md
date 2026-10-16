# Acquisition improvement planning handoff — 2026-10-16

## Scope and state

User requested a plan for better one-line-request subreddit selection and the
whole scraping pipeline. Delivered a [proposed implementation plan](../architecture/ACQUISITION_PIPELINE_IMPROVEMENT_PLAN_2026-10-16.md)
and linked it from the existing Phase 9 plan. No scraping implementation,
environment flag, provider settings or frontend code changed in this turn.

Working branch: `release/phase9-acquisition-20261015`; observed HEAD
`ff6d246bfe1e9cfd0f21d8e32135582e631636f1`. Existing uncommitted handoff-index
changes and the untracked [local Reddit probe handoff](2026-10-16_LOCAL_REDDIT_PROBE.md)
belonged to the preceding task and were preserved. The original IDE checkout
remains a different, older worktree. Do not merge or deploy by assumption.

The original checkout's ignored `.env` remains locally enabled for Reddit by
the preceding explicit operator request. This planning task neither revoked it
nor copied it into production; local diagnostic enablement is not approval
from Reddit. Public policy references are linked in the plan for implementation
review. Do not infer an unrestricted crawl or permission to defeat rate limits.

## Engineering conclusions

- First fix preservation and truthful reporting. Report builders currently drop
  canonical findings/query telemetry; new scraper depth alone cannot fix that.
- Extend existing source-planning models, bounded gateway suggestions and the
  native dispatcher rather than adding another orchestration framework.
- Entity/region/topic planning and community mapping need reviewed one-line
  cases. Existing explicit-feed success does not prove automatic relevance.
- Model discovery, acquired body and passage-supported claims separately. Keep
  archives/caches, original times, missing bodies and presentation caps explicit.
- Implement as six incremental slices with code ownership, tests and exit proof;
  no new numbered "completed phase" or unmeasured accuracy claims.
- Proposed Quick/Deep caps are development settings to validate, not guarantees.
  Generic metadata or removed content cannot meet a meaningful-body quota.

Architecture/data-pipeline skills guided reuse, interfaces and observability;
the decision-record skill guided proposed decisions, rejected alternatives and
tradeoffs. No new heavy infrastructure, daemon or paid-provider activation is
needed to start. The efficient-codebase skill kept inspection to known owners.

## Evidence and verification boundary

Inspected the Phase 9 plan, latest handoff/index, local Reddit probe handoff,
planner contracts/decision functions, social resolver, reading stage, report
adapter and relevant test inventory. Prior live results are explicitly dated;
no new live scraper run, test suite, browser run, CI run or deployment was done
for this planning-only turn. Primary HN, Stack Exchange, YouTube and Reddit
documentation was consulted for specific external contract constraints.

`git status --short` and `git diff --stat` were run before editing. After writing
the plan, `git diff --check` exited 0. A relative Markdown-link existence check
over the new plan, original Phase 9 plan, new handoff and handoff index exited 0:
63 local links checked, none missing. No files were staged, committed or pushed.
Tests and acceptance criteria in the plan are proposed work, not claimed passing
results. No application test run was warranted for these documentation changes.

## Next implementation owner

Begin Slice A: actual native payload -> report -> renderer preservation tests,
including nonempty findings and query logs, unavailable stock quotes, catalyst
field differences and V2EX name validation. Keep discovery-only candidates out
of acquired-body counts. Preserve frozen datasets and historical dossiers;
write fresh proof to new locations. Read the latest Git diff before editing;
the existing notes/config override are not permission to sweep unrelated work
into a commit or alter the other agent's worktree.
