# Trending current-evidence completion — 2026-10-20

This is the offline Trending subtask of the final four-agent completion request,
not a fresh live acceptance report. Worktree `.scratch/phase9-remediation-20261016`,
branch `fix/p0-lenovo-acquisition-20261018`, base
`39a514b68388450bbc5e6061aba97bda2077fc7f` plus preserved inherited changes.
No Git write, deployment, credential change, live provider or model request was
performed by this subtask. The coordinating agent owns fresh bounded checks,
browser replay and whole-suite closeout.

## Observed first loss and decisions

Saved native `04-trending.json` from the expanded-harvesting temporary run shows
that subject-relevant Bing RSS items included publication dates from 2023 and
March–September 2026. The literal `when:2d` hint did not make those dates current.
The feed handler returned immediately on any subject-relevant results, suppressing
the existing Google fallback despite the stale evidence. Undated Google wrappers
were separately available and were already provisionally readable. Do not revert
to rejecting missing-date candidates before reading or relax the 48-hour gate.

- [Harvesting query planning](../../backend/services/research/harvesting.py)
  uses concise task angles, not the agent's entire internal instruction. Trending
  queries include absolute `after`/`before` and `when:2d` discovery hints for all
  existing core channels. These hints are not proof of publication timing.
- [Feed routing](../../backend/infrastructure/acquisition/routing/standard_handlers.py)
  continues the existing bounded fallback when a Trending harvest's first feed
  contains only provably stale/future items. Those observed leads remain available
  behind fresh/undated fallback leads; an undated candidate still gets a read
  opportunity. No new search provider, retries or access bypass was added.
- [Captured context](../../backend/services/research/body_context.py) clears a
  Trending article's feed-only publication field when no captured publisher
  declaration exists, retaining the feed date separately. Fetch time, updates and
  sitemap `lastmod` cannot establish freshness. Runtime, passage analysis and
  offline requalification set `temporal_required` before this reconciliation.
- [Clustering](../../backend/agents/trending/clustering.py) distinguishes events
  using observed headline overlap rather than lumping all generic category matches
  or incidental body/navigation words together. Wire/title IDs are deterministic.
  Groups remain heuristic; independent-source counts are unknown, not verified.
- [Trending projection](../../backend/agents/trending/agent.py) exports bounded
  `recent_developments` with canonical IDs, URLs, publication declarations and
  source-reported passages. Neither a completed empty investigation nor an exception
  can silently start a second unbudgeted headline sweep. Pipeline exceptions retain
  sanitized explicit acquisition failure diagnostics. Unknown evidence is not proof
  of absence.
- [Extraction](../../backend/agents/trending/extraction.py),
  [assessment](../../backend/agents/trending/assessment.py) and
  [temporal analytics](../../backend/agents/trending/temporal.py) no longer turn
  article count into high momentum, source grouping into independence, or ordinary
  reporting into LOW misinformation risk. Snapshot comparisons are explicitly
  sampled acquisition counts, not popularity, reach, diffusion or amplification.

## Verification actually run

Final focused command:

```text
python -m pytest tests/unit/test_trending_current_evidence.py tests/unit/test_expanded_harvesting.py tests/unit/test_trending_2.py tests/unit/test_raw_pool_requalification.py tests/unit/test_shared_acquisition_fabric.py tests/unit/test_phase5_agent_golden_master.py tests/integration/test_trending_2_workflow.py tests/integration/test_functional_agents_matrix.py -q
```

**124 passed / 8.47s, exit 0.** Ten new focused controls cover genuine saved
old-feed metadata plus explicitly synthetic positive controls, missing dates,
captured original dates, event separation, no fake momentum and no second sweep.
No saved snippets or replay are represented as fresh live acquisition.

Earlier attempts exposed four obsolete golden epistemic labels, followed by three
API tests mocking the removed post-research fallback and one numeric-independence
expectation. Historical golden JSON was not regenerated. The parity test permits
only the explicit UNASSESSED label delta for its four unadjudicated cases, while
preserving all original counts, titles, sentiments and citation cardinalities.
API integration fixtures now mock the actual qualified-research boundary, not
search headlines pretending to be acquired articles.

Scoped fatal flake8: exit 0, zero findings. `git diff --check`: exit 0, existing
line-ending warnings only. Full regression/browser/live proof belongs to the
coordinating closeout and is not claimed here. The actual fresh Trending result
must still establish captured publication timing and useful source content.

## Bounded live result and subsequent offline correction

The coordinator's single authorized Trending check completed in 22.17s with three
candidate URLs, three successful raw reads, one structurally extracted article
(1,472 words) and zero qualified recent articles. All three reads returned HTTP
200; no deadline was exhausted. Native admissions were 57. The Yahoo article's
captured original publication was September 25; Mint's July 16 capture was not
structurally classified as an article; Moneycontrol had no captured publication
declaration. Keeping these out of current evidence was correct.

The first source-loss boundary, however, was earlier: 54 provider observations,
34 response-received observations and 264 result decisions included 190
`SUBJECT_MISMATCH` and 64 `INVALID_URL` rejections. Existing stale-only fallback
did run; a final-strength four-token topic match then rejected publisher headlines
that omitted modifiers before an article could be read. The compatibility news
scraper also emitted observed `url` fields, while RSS normalization read only
`link`, losing those locators entirely.

Two narrow corrections followed that live check:

- [Discovery topic overlap](../../backend/infrastructure/acquisition/adapters/web/search_matching.py)
  permits a provisional read lead when a general/topic/concept target has at
  least three meaningful tokens, at least two distinct whole-token matches and
  at least 50% coverage. Only harvest discovery calls can use this path. Named
  person/company classes, publisher headline-resolution and final captured-body
  entity/date qualification are unchanged. This is recall for reading, not a
  relaxed evidence gate or claim-support score.
- [RSS normalization](../../backend/services/agent_reach/native/normalizer.py)
  preserves the already observed `link` or `url` key. Missing URLs remain missing;
  metadata remains metadata, not a fabricated body.

Network-blocked replay of the saved decisions admits 30 additional provisional
observations across nine unique observed locators. Their publication dates were
not retained in those decision records, and their bodies were not read. This is
not proof of fresh evidence or a post-fix live success. The existing live request
permission was consumed; an additional check needs its own small authorization.

Post-correction focused validation: **175 passed / 5.00s, exit 0**, running the new
Trending controls, expanded harvesting, native bounded HTTP, acquisition channel
contracts, search-resolution iteration and autonomous-discovery funnel suites.
The 13 focused Trending controls include the genuine saved rejected headline as
an explicitly unacquired/undated lead, strict final-gate rejection and the legacy
URL-key regression. No additional live network or AI call was made by this agent.
