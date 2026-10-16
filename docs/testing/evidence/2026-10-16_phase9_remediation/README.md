# Phase 9 remediation evidence — 2026-10-16

Read the [verification report](../../PHASE9_REMEDIATION_VERIFICATION_2026-10-16.md)
and [handoff](../../../handoffs/2026-10-16_PHASE9_REMEDIATION.md) before interpreting
these numbers. Software regression checks pass; Phase 9 research acceptance does
not. No production merge/deployment is represented here.

## Reference replay

- `before_{dev,regression,held_out}.json`: corrected-runner baseline, runtime
  source classification, supplied reference passages only.
- `after_*.json`: intermediate post-change run, including the observed regression
  wire-independence false positive. Preserved as failed evidence.
- `final_*.json`: after the wire predicate fix. Resolution still regresses;
  zero recorded unsupported SUPPORT is not a population guarantee.
- Dataset hashes and recorded engine HEAD/dirty status are embedded. No reference
  URLs were fetched by the runner, and no labels are human reviewed. Held-out
  aggregates were repeated after other regressions; they are not a new blind test.

## Live and rendered measurements

- [Live claim measurements](live_claim_measurements.json): before/after eleven
  claim probes plus two named live title rechecks. Captured passages were not
  injected. Includes URLs/IDs/relations and dossier-check observations, not private
  credentials or full source bodies. The original false refutation is retained.
- [Browser measurements](browser_measurements.json): twelve actual page-button
  investigations, three per agent, 24 viewport states; stable application
  fingerprint. Five records / 1,434 words, eight zero-acquisition inputs.
- [CSS saved-event replay](css_replay_measurements.json): the same twelve recorded
  event streams through native page buttons after CSS changes; 24 states, no new acquisition.
- [Observed command results](command_results.json): actual commands, exit codes,
  counts and validation limitations. Not a fabricated terminal transcript.
- [Clipping before](render_clipping_before.json) / [after](render_clipping_after.json):
  the same 22 synthetic/saved-report states, nine versus zero failures. These
  re-rendered saved reports; they did not reacquire sources or measure accuracy.
- [Hosted backend CI](ci_backend_checkpoint.json): five successful hosted jobs at
  exact SHA `8c8b6c5`. Later frontend/publication validation is recorded separately.
- [Published full checkpoint CI](ci_published_checkpoint.json): all five jobs
  successful at exact `084aae3`, including the final application/frontend fixes.

Full event streams, raw responses, temporary dossiers and logs remain in a unique
system-temp audit directory. They may be ephemeral; the maintained scripts and
committed selected measurements make new observations reproducible without
overwriting old artifacts. Counts from separate passes must not be added as if
they were unique sources or independent experiments.

## Selected actual captures

| Capture | Provenance |
|---|---|
| [Scout](screenshots/01-scout-390-report.png) | Actual final browser/backend investigation; empty acquisition with discovery disclosure |
| [Trending](screenshots/04-trending-390-report.png) | Actual investigation; zero retained records, not a fabricated trend |
| [BrandShield](screenshots/07-brandshield-390-report.png) | Actual investigation; observed store/brand text, not proof of counterfeit activity |
| [Personal Watch](screenshots/10-personal_watch-390-report.png) | Actual investigation; a profile lead, not identity/impersonation verification |
| [Supported title](screenshots/replay-0-scientific_title_true-1440.png) | Exact saved live recheck report rendered after the CSS fix; no new provider call |
| [Refuted title at 320px](screenshots/replay-0-scientific_title_false-320.png) | Exact saved live recheck report; wrapped rationale, score and citation |
| [Brand zero-source control](screenshots/fixture-brand-zero-320.png) | **Synthetic UI control**, never presented as a live investigation |

Selected captures were visually inspected. The initial 44-state basic check did
not detect internally clipped cards; a later visual review and stronger check
did. Do not claim all 44 states were manually visually accepted. Screen readers,
WCAG contrast, axe, Safari/Firefox, real mobile hardware and deployed parity were
not verified. Fonts were deliberately blocked, actual pinned Chart.js supplied;
resource errors are separate from uncaught page exceptions.
