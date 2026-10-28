# Sixteen-prompt website yield evidence — October 28, 2026

Read the [evaluation](../../FOUR_AGENT_16_PROMPT_EVALUATION.md),
[desktop report](../../DESKTOP_FRONTEND_CONTENT_SUFFICIENCY.md),
[source-gap plan](../../source_gap_recommendations.md) and
[handoff](../../../handoffs/2026-10-28_SIXTEEN_PROMPT_WEBSITE_YIELD.md).

- [Exact prompts](prompts.json), [private capture locations/hashes](capture-manifest.json),
  [application lineage](implementation-state.json) and initial checkout snapshots.
- [Per-URL JSON](website_word_yield.json) / [CSV](website_word_yield.csv):
  original live observations and separately labeled corrected offline projections.
  SOURCE, REJECTED_SEARCH_LEAD and TRANSPORT are different record types.
- [Per-case/website totals](website_totals.csv), [agent/website totals](agent_website_totals.csv),
  [rankings](website_rankings.json), [case/agent summary](agent_word_yield_summary.json).
- [Conditional gaps and agent review](evidence-gap.json): soft visual targets do
  not imply task fulfilment; independent human/factual validation is not claimed.
- [Transport admissions](transport/): metadata only, no raw headers/credentials.
  Admissions are not provider receipts, paid quotas or complete external SDK usage.
- [T2 source-pool metadata recovery](T2-recovered-pool-metadata.json): actual
  bodies were captured; original native/frontend response was not saved. Per-URL
  original read durations/backends remain unknown; no zero substitutions.
- [Identical-input replay](replay-comparison.json), [AI accounting](ai-accounting.json),
  [final gates](final-gates.json), [earlier gates](earlier-gates.json).
- [Browser states](browser-summary.json), [section CSV](frontend_sections.csv),
  [layout comparison](layout-comparison.json), [screenshots](screenshots/README.md).

There are 16 once-only live investigations, 15 saved native responses (including
one explicit acquisition failure), and one recovered pool with missing original
native output. Final browser inputs are 11 original responses, four offline
native-capture replays and one recovered-pool replay, at four widths. Never count
the four viewport copies or offline projections as additional acquisitions.

Bodies stay in the private original temp capture tree; this directory publishes
permitted metadata/counts/hashes and qualified UI excerpts rather than whole
publisher bodies. Unknown permission/source-family observations are not approvals.
Temp files may expire. No commit, push, deployment or remote CI occurred.
