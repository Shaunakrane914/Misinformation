# Phase 8B normalization truth — 2026-10-13

This is a Phase 8B implementation checkpoint, not acceptance of Phase 8 or its
frontend redesign. Read [AGENTS.md](../../AGENTS.md), the
[prior handoff](2026-10-13_PHASE8B_CONTENT_DECODING_AND_FIELD_AUDIT.md), and
inspect branch/status/diff before resuming.

## Owner scope and branch

The owner asked for the *whole* Phase 8 mandate, including the four-agent
frontend, with a completion report only after all work is accepted. Another
coding agent was confirmed on the original Phase 8 branch. This work therefore
stays on isolated branch `feat/phase8b-extraction` in
`.scratch/phase8b-worktree`, beginning at
`3b3dc23d082f50d4f3654c5afa4b91064fada3bd`. That preceding checkpoint
was pushed and its exact SHA passed all five jobs in
[hosted run 38344378801](https://github.com/Shaunakrane914/Misinformation/actions/runs/38344378801).
That run does **not** cover the changes described here.

## Implementation and rationale

- [Native normalization](../../backend/services/agent_reach/native/normalizer.py)
  no longer substitutes repository descriptions/star counts/README authors,
  video channels/views, V2EX reply counts/dates, feed-entry authors, comment
  authors/likes/video URLs or podcast identities/URLs when the provider did
  not supply them. The repository owner and update timestamp remain distinct
  metadata, not document author/publication. Long V2EX topic text is
  `PARTIAL_CONTENT`, not `FULL_ARTICLE` based on length alone. A title-only
  RSS entry or episode without notes is metadata, not summary/content.
- [YouTube routing](../../backend/infrastructure/acquisition/routing/router.py)
  now requires observed video identity and title/description for a successful
  `youtube.read`. An inaccessible/empty yt-dlp result cannot fall through to
  generic HTML and be misread as a video. The
  [standard handlers](../../backend/infrastructure/acquisition/routing/standard_handlers.py)
  leave absent video/transcript title and author blank.
- [Runtime outcome classification](../../backend/infrastructure/acquisition/routing/channel_dispatcher.py)
  and the [live audit classifier](../../scripts/audits/run_phase8_live_acquisition_audit.py)
  use actual feed content depth, not `rss_feed` mode alone, to avoid upgrading
  a title-only entry to `SYNDICATED_SUMMARY`.
- [Normalization regression fixtures](../../tests/unit/test_phase8_normalization_truth.py)
  and [operation-route tests](../../tests/unit/test_recovered_operation_routes.py)
  cover these missing-field and no-fallback contracts. One early focused run
  failed because an existing test expected the old V2EX body format; that
  expectation was corrected to the observed-content contract before the
  recorded passing runs below. No provider data or frozen labels were changed.

## Verification observed for this uncommitted checkpoint

| Check | Actual result |
|---|---|
| Focused normalization, routes, audit and native tests | 59 passed, exit 0; later 47-test subset passed, exit 0 |
| Full `pytest tests/ -q -o addopts='--tb=short -ra'` | 1,029 passed in 62.51s, exit 0 |
| Fast `pytest tests/unit tests/chaos tests/security -q -o addopts='--tb=short -ra'` | 833 passed in 28.71s, exit 0 |
| Fatal flake8 from `AGENTS.md` | exit 0, 0 findings |
| Three Node frontend contract scripts | exit 0, all three passed; simulated DOM/fetch, not visual browser proof |
| Frozen benchmark hash verifier | exit 0, content hashes verified |
| Offline release smoke | exit 0, `OFFLINE_SMOKE_PASS`; mocks/disabled live acquisition |
| Isolated rollback validator | exit 0, `OFFLINE_PERSISTENCE_PASS`; historical archive `NOT_VERIFIED` because the 55 protected malformed dossier files are absent from this isolated worktree |
| [Guarded live re-probe](../../artifacts/phase8_extraction_spotchecks/2026-10-13_04-08-03Z/) | 10/10 **selected common-case** operations live-classified; 10/16 protected operations were selected, so the filtered run's Phase 8A gate is `PARTIAL` by design |
| [Important-field summary v11](../../artifacts/phase8_extraction_spotchecks/2026-10-13_04-08-03Z/richness_summary_v11.json) | 16-operation latest-scenario rollup; normalized samples only, not provider schema completeness |
| Hosted CI on *these* edits | NOT VERIFIED until a new commit/push and exact-SHA run finish |
| Browser visual, narrow-screen and keyboard walkthrough | NOT VERIFIED: no browser surface was available in the enabled computer-use inventory |

The live run metadata explicitly records a dirty worktree and the preceding
commit. Raw response bodies and credentials were not retained. No frozen
benchmark input, historical dossier, research tree, original worktree,
production credential or deployment was changed.

## Gate and continuation

**8A PASS** rests on the earlier complete 16-operation live proof, with its
documented content-quality correction. **8B PARTIAL:** the known-field matrix
and sampled richness are useful, but difficult targets, pagination/follow-up
cost, optional/restricted field completeness and several missing extraction
paths remain. **8C–8F NOT ACCEPTED:** intelligence and held-out research
quality, valuable new source integration, complete four-agent frontend and
visual accessibility, adversarial end-to-end runs and final system integrity
are not done. Shared-renderer contracts are not a frontend redesign.

Do not merge to `main` or deploy. The original checkout's 55 malformed
historical dossiers remain protected. A passing isolated rollback reader is
not proof of historical archive recovery or deployed rollback. Before the
next handoff, inspect the real worktree and hosted CI; do not infer completion
from this document's snapshot.

Commit/push state for **this** checkpoint: pending at document creation.
