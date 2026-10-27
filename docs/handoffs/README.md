# Coding-agent handoffs

## News wrapper unwrapping, temporal guard & 4-agent verification — 2026-10-27

- [News wrapper unwrapping & 4-agent verification](2026-10-27_NEWS_WRAPPER_UNWRAPPING_AND_FOUR_AGENT_VERIFICATION.md):
  resolved opaque Google News redirect wrapper tokens via direct publisher prioritization (Bing News RSS)
  and normalizer unquoting, implemented two-layer temporal guard labeling (NEW vs OLD) for Trending so
  pages are never empty, protected golden master hash invariances (12/12 passed), and validated all 4 agents
  across live smoke and fast offline regression suites (867/867 passed).

## Expanded scraper fleet — scraping repair & discovery wiring — 2026-10-26

- [Fleet scraping repair](2026-10-26_EXPANDED_FLEET_SCRAPING_REPAIR.md):
  diagnosed the fleet live; fixed dead news feeds (Reuters/PIB) with verified direct
  publisher RSS, broadened Substack, registered hackernews/arxiv, and wired
  `expanded_sources` discovery into the planner so the fleet actually fires in
  investigations. Real bodies scraped end-to-end (BBC/Guardian/Wikipedia/Yahoo/arXiv).
  SEC/FactCheck/Reddit remain credential-gated; Bluesky search now 403s. Uncommitted.

## Expansion Git checkpoint ? 2026-10-25

- [Push and security closeout](2026-10-25_EXPANSION_PUSH.md):
  code9a437bb pushed to the release development branch; full/fast2,356/2,148.
  Hosted CI pending at handoff preparation; no merge or deployment.

## Useful evidence expansion ? 2026-10-25

- [Implementation and measured continuation](2026-10-25_USEFUL_EVIDENCE_EXPANSION.md):
  application changes remain in the release worktree. Fresh source-citation
  acquisition and separate Personal routing repair verified; full/fast2,348/2,140.
  **20? NOT demonstrated; no push or deployment.**

## Four-case expansion live retest — 2026-10-24

- [Live retest and offline follow-up](2026-10-24_EXPANSION_LIVE_RETEST.md):
  exactly four approved cases, zero AI reservations; published words
  6,484/774/0/0. Trending plural-selection defect repaired from saved bytes,
  one source qualifies offline; no extra live request. Full/fast2,300/2,092,
  ten Node suites and12 browser replay states passed. **20× not demonstrated.**

## Expansion safety and release integration repair — 2026-10-24

- [Repair handoff](2026-10-24_EXPANSION_SAFETY_AND_RELEASE_INTEGRATION.md):
  bounded transport, adapter access/depth controls, actual release integration
  and honest output measurement. Offline validation and saved-report browser
  replay are separated from fresh live proof. **20× remains unverified; no deploy.**

Start here when resuming work. These are dated engineering records, not promises that the current checkout has been validated. Read [AGENTS.md](../../AGENTS.md) first, then inspect the live worktree before editing.

## Historical: Phase 10 10x Deep Reading & Expanded Fleet Extraction — 2026-10-24

- [Phase 10 handoff](2026-10-24_PHASE10_10X_DEEP_READING_AND_EXPANDED_FLEET.md): historical expansion implementation and test snapshot. Its aggregate word-count benchmark mixed scopes and does not validate useful evidence per agent; use the repair record above for current acceptance.

## Preceding: Phase 9 20x Async Acquisition & Expanded Scraper Fleet — 2026-10-24

- [Phase 9 handoff](2026-10-24_PHASE9_20X_ASYNC_ACQUISITION_HANDOFF.md): historical async/adapter expansion and test snapshot. The synthetic scheduler comparison does not establish 20× HTTP throughput or evidence yield.

## Preceding: Phase 8A real acquisition proof — 2026-10-12

- [Phase 8A handoff](2026-10-12_PHASE8A_REAL_ACQUISITION_HANDOFF.md): production-path trace, live acquisition repairs, evidence, validation and safe Stage 8B continuation.
- [Phase 8A real acquisition report](../architecture/PHASE8A_REAL_ACQUISITION_VERIFICATION.md): honest live depth for all 16 protected operations and negative evidence.
- [Phase 8 production path trace](../architecture/PHASE8_INVESTIGATION_PATH_TRACE.md): claim-to-frontend ownership and remaining architecture risks.

The Phase 7.4 section below remains the preceding security and data-integrity checkpoint.

## Latest: Phase 7.4 verification — 2026-10-12

- [Phase 7.4 closeout handoff](2026-10-12_PHASE7_4_CLOSEOUT.md): pushed commits, hosted CI evidence, local archive limitation and safe continuation.
- [Phase 7.4 machine context](2026-10-12_PHASE7_4_CONTEXT.json): commit SHAs, run ID, validation counts and unresolved boundaries.
- [Phase 7.4 verification report](../architecture/PHASE7_4_REMEDIATION_VERIFICATION.md): local security closeout, Git/CI evidence boundary and release decision.
- [Historical dossier recovery inventory](2026-10-12_HISTORICAL_DOSSIER_RECOVERY_INVENTORY.json): read-only paths, SHA-256 hashes, parser diagnostics and candidate results for all 55 malformed records; no dossier content.

The remediation implementation context remains:

1. [State and safe continuation](2026-10-12_ARCHITECTURE_REMEDIATION_HANDOFF.md): where the previous agent stopped, ownership boundaries, implementation entry points, and prioritized follow-up.
2. [Decision rationale and code map](2026-10-12_ARCHITECTURE_REMEDIATION_DECISIONS.md): why the changes were made, tradeoffs, and regression tests that protect them.
3. [Testing and reproduction runbook](2026-10-12_ARCHITECTURE_REMEDIATION_TESTING.md): exact offline commands, isolated logging, expected failures, and honest acceptance criteria.
4. [Execution work log](2026-10-12_ARCHITECTURE_REMEDIATION_WORK_LOG.md): reconstructed checkpoints and observed command-result excerpts; not a verbatim chat export.
5. [Machine-readable context](2026-10-12_ARCHITECTURE_REMEDIATION_CONTEXT.json): portable paths, base commit, scope, evidence links and continuation constraints.

The [remediation report](../architecture/ARCHITECTURE_REVIEW_REMEDIATION_2026-10-12.md) summarizes the preceding implementation. [Rollback verification](../operations/ROLLBACK_VERIFICATION.md) explains the 55 protected malformed historical JSON files that remain unresolved.

## Record maintenance

- Preserve older handoffs; add a new dated record when work continues and update this index's latest pointer.
- Record observed results separately from planned checks. Include failures and incomplete verification.
- Link to maintained code and tests rather than copying implementations into documentation and creating another source of truth.
- Do not store API keys, bearer tokens, private datasets, full dossier contents, or private reasoning traces here. Record concise technical rationale and evidence instead.
- A dirty worktree is shared work to preserve, not permission for cleanup, restoration, staging, commits or pushes.
