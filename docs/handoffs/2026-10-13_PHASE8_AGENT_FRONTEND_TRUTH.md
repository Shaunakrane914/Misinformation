# Phase 8 agent frontend truth checkpoint — 2026-10-13

This is another independent Stage 8E integrity checkpoint, **not** a complete
frontend redesign or final Phase 8 acceptance. Work continued in the isolated
`feat/phase8b-extraction` worktree, starting at commit
`97b39e24f17e40b0a3c92fd541ccb383a993c746`. That exact backend commit
passed [hosted CI run 38367854394](https://github.com/Shaunakrane914/Misinformation/actions/runs/38367854394)
in all five jobs. The new frontend changes below require their own exact-SHA
CI verification after commit.

## Observed defect and decision

The old [research page](../../frontend/research-agent.html) produced a
browser-model dossier and synthetic reading lists with no backend acquisition.
The [agent directory](../../frontend/agents.html) advertised
`POST /api/research/query`, which does not exist. The page is now a factual
claim entry gateway to the real `/api/claims/verify` workflow, explicitly
disclosing that standalone open-ended research is unavailable. The former
page can be recovered from Git history; no research artifact was deleted.
[Frontend documentation](../../frontend/README.md), the
[architecture overview](../ARCHITECTURE.md) and the historical
[feature status matrix](../FEATURE_STATUS.md) reflect that boundary.

The four specialized pages now avoid several unearned conclusions:

- [Scout](../../frontend/scout-agent.html) no longer turns missing price/
  currency/market-state data into a green nominal condition or a made-up
  provider. Source role, first news item and catalyst type alone no longer
  make a record `KNOWN_FACT` or `SUPPORTED` in its provenance drawer.
- [Trending](../../frontend/trending-agent.html) treats missing velocity and
  risk as unmeasured/unassessed, describes origin as earliest *sampled*
  source, and does not equate a backend `VERIFIED` label with demonstrated
  independent corroboration. Sparse trend records no longer crash on absent
  category, origin, platform or timestamp.
- [BrandShield](../../frontend/brandshield-agent.html) no longer treats an
  empty response as no suspicious activity or an absent review-screening
  result as a completed clean screen. It preserves missing seller/platform/
  date/risk fields and labels source groups as unverified.
- [Personal Watch](../../frontend/personal-watch-agent.html) counts only
  explicit change events, leaves missing risk/date/platform values unknown,
  and no longer calls every returned source a verified URL.

All four pages now use the [shared display-link guard](../../frontend/safe-source-url.js)
for dynamic source links. It rejects non-HTTP(S) and credential-bearing URLs;
output is HTML-escaped. It does **not** authenticate domains, establish
source-to-claim entailment or replace backend SSRF controls.

## Validation and limitations

- [Agent UI truth contracts](../../tests/frontend/test_agent_ui_truth.js)
  execute the actual inline page controllers against sparse and adversarial
  simulated DOM data; [claim UI contracts](../../tests/frontend/test_claim_ui_truth.js)
  cover the research-page transfer. Five Node frontend test scripts passed,
  exit 0. These are not real-browser screenshots, responsive layout checks,
  or keyboard/screen-reader acceptance.
- Full Python offline suite: 1033 passed, exit 0. Fast unit/chaos/security:
  837 passed, exit 0. Fatal Python lint: zero, exit 0. Frozen benchmark
  content hashes verified, exit 0. Offline release smoke and isolated
  rollback scripts each exited 0. Rollback's historical archive read-only and
  deployed previous-version checks remained `NOT_VERIFIED` in this worktree.
- `git diff --check` passed. No frozen benchmark, historical dossier,
  credentials, production deployment or `main` branch was altered.

## Remaining acceptance work

**8E remains PARTIAL.** The current agent layouts still need a coherent
design/interaction pass, keyboard and narrow-screen browser checks, longer
and conflicting backend-response cases, verified citations and timestamps,
and complete source-coverage/error/auth-required presentation. A computer-use
inventory exposed no browser or app surface during this turn, so no visual
browser audit or before/after screenshot is claimed. Stages 8B/8C/8D/8F
also remain incomplete under the Phase 8 mandate. Do not label this work as
production-ready merely because local and hosted regression gates are green.

Commit/push and hosted CI for *this* checkpoint were pending when this record
was authored; verify the actual SHA/run rather than inheriting the prior
backend CI result. This is an engineering handoff, not a raw chat transcript.

## Follow-up after first push

The first frontend commit was `9882a827e42c368def22fe4dee5b50fb8777bf59`
and [hosted CI run 38370934400](https://github.com/Shaunakrane914/Misinformation/actions/runs/38370934400)
passed all five jobs. A subsequent template audit found additional unescaped
BrandShield status/evidence IDs and a default-`SUPPORTED` Scout badge. The
follow-up code and adversarial simulated-DOM assertions are separate from
that passing CI run. Verify their final commit and hosted CI independently.
