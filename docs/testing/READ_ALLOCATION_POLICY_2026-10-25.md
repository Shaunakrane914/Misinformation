# Read allocation policy and pre-implementation decisions — 2026-10-25

Completed repair cycle: [actual live results, offline follow-ups and remaining gaps](READ_ALLOCATION_RESULTS_2026-10-26.md).

User approved the plan following the failed live demonstration. Branch
`release/specialist-task-20261024`, HEAD `7ad13a5` plus preserved local implementation.
This policy and the failed-run ledger were written before implementation changes.

[All 24 observed candidate decisions](evidence/2026-10-25_read_allocation/failed-run-decisions.md) ·
[Machine-readable observed decisions](evidence/2026-10-25_read_allocation/failed-run-decisions.json).

## Measured cause

The nine actual read slots were one unresolved Google wrapper followed by eight reads at a single
publisher: home, comments feed, publisher search, five undated-at-selection article leads. Those five
bodies subsequently proved stale. The ECS candidate was discovered with a real headline but never read.

Read-time scoring favored the exact adjacent phrase in the older article headlines (+3 title) over
the reordered topic words in the ECS headline (+2 title). Body dates were unknown before those reads.
Indexes/homepages also counted as zero-yield publisher observations, imposing history/streak penalties
before the first actual article. Even then all five exact-phrase articles beat the untested reordered
headline, exhausting the publisher cap. The comments feed consumed a discovery slot despite a main
publisher feed being observed. The strict final date gate correctly rejected stale bodies; it did not
cause the useful candidate to be skipped.

## Implementation contract

Retain the opt-in pipeline, existing providers, security/access controls, 24-read and 120-admission
global ceilings and the existing per-host read cap. No fabricated URLs, publication times or bodies.

1. Track host discovery and article attempts separately. At cap eight, reserve a starting allocation
   of two discovery opportunities, four article opportunities and two adaptive opportunities. Scale
   conservatively for lower profiles. Unused reservations can be released only with an explicit reason.
2. Distinguish publisher main feeds/search/sitemaps from comment feeds. Article tasks defer comment
   feeds; the registered community/comment operations remain untouched. Main feeds can establish
   routing date observations, but final freshness still requires captured-body evidence.
3. After two stale/undated/unusable actual article reads, use a remaining discovery opportunity to
   inspect an observed main feed/search path or diversify. Do not count homes/indexes as failed articles.
4. Rank complete topic-token coverage independently of adjacency; exact phrase is a weak tiebreaker,
   not grounds for excluding reordered relevant headlines. Observed publication hints outrank unknown
   dates. GDELT first-seen timestamps never become publication hints.
5. Keep personal statement, quotation and identity-threat objectives distinct in planning/selection.
   Prefer observed statements/interviews/transcripts for statement objectives; commentary remains
   inspectable, with actual attribution and role qualification unchanged.
6. Record allocation decisions, phase counters, deferrals and date/subject reasons. Do not silently
   convert reserved-but-unstarted work into successful provider attempts.

## Verification gates

First replay the failed query responses and known genuine captures at their original timestamps.
Explicitly label any supplemental previously acquired body; unknown outcomes remain unknown.
Test main-feed preference, reordered topic titles, two stale reads, blocked feeds/articles, no feeds,
late feed date aliases, total/per-host caps and final stale/missing-date rejection. The ECS URL must
receive a read opportunity in the saved scenario without changing its title or source bytes.

Then run impacted/full/fast Python, fatal lint, frontend contracts, isolated smoke/persistence and
frozen checks. Proposed final live batch: battery recycling and semiconductor manufacturing;
Mary Barra and Tim Cook, once each, 240s/24 reads/120 native admissions per case. Use ordinary query
inputs. No whole-investigation retry, paid reader, source sweep, push or deployment. AI suggestions
may use the existing strict shared budget; measure actual reservations, never reset the ledger to
obtain permission. Compare the saved source-to-frontend outputs and disclose failures rather than
claiming that additional raw text establishes acceptance.

Near-term acceptance requires relevant real bodies reaching useful attributed passages. Current-date
coverage, independent accuracy and 2×/20× growth remain separate gates. A topic with no established
fresh evidence must abstain honestly; a calibrated positive control must actually read its relevant
candidate. Test counts and HTTP 200 are not substitutes for these outcomes.
