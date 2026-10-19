# P0 Lenovo acquisition reliability: CI closeout — 2026-10-19

## Decision and publication boundary

The focused acquisition fix is verified on
`fix/p0-lenovo-acquisition-20261018` at application commit
`9a730ac1d5e6347ca4981ce9b4d3e48395d70974`.
All five jobs in the [exact-commit hosted run](https://github.com/Shaunakrane914/Misinformation/actions/runs/39136495988)
completed successfully. This closeout changes documentation only; it does not
claim CI results for its own later documentation commit.

The implementation and test corrections were committed and pushed to that fix
branch only. No merge or deployment was performed. A read-only remote check
still reports `main` at `8471ee349efd48644519d3a8fecde2e724ebf6ae`.
The earlier production attestation identified application `725f4e2`, not the P0
fix. Production parity and release authorization remain separate gates.

## Verified outcome

Read the [implementation handoff](2026-10-18_P0_ACQUISITION_RELIABILITY.md)
for code pointers, engineering decisions, commands, timings and failed-run
history; the [evidence index](../testing/evidence/2026-10-18_p0_lenovo/README.md)
contains sanitized measurements and screenshots.

- Acquisition uses non-probing capability snapshots, bounded shared workers,
  monotonic deadlines and explicit queued/started/not-submitted states.
  Completed investigations reject late worker results.
- Company identity is separate from a validated market listing. Plain Lenovo
  remains listing-ambiguous and research continues without an invented quote.
- Shared reports distinguish `ACQUISITION_FAILED` from acquired-but-insufficient
  evidence. Synthetic all-timeout controls exercised all four actual agent pages
  at 320, 390 and 1440px; warnings and empty-source reports remained visible.
- The one authorized AI-disabled live Lenovo investigation discovered 39
  candidates, completed four direct reads and retained five records: 5,485 words
  / 41.003 decimal KB. One observed issuer PDF supplied 1,564 words; the other
  four records were index pages, not independent corroboration. Two queries
  timed out and one required authorization; these failures were retained.
- Exact saved-response frontend replay showed one unverified observation, five
  acquired records and 28 discovery cards, with no observed horizontal overflow
  or uncaught page exceptions at the three tested widths. It made no second
  investigation request.

## Verification ledger

This is a summary of executed checks, not a raw terminal transcript.

| Check | Observed result |
| --- | --- |
| Full local offline regression | 1,456 passed; exit 0 |
| Local unit/chaos/security | 1,248 passed; exit 0 |
| Focused follow-up after test scheduling corrections | 71 passed; exit 0 |
| Fatal Python lint | Zero errors; exit 0 |
| Nine frontend contract scripts | Passed |
| Isolated release smoke / persistence validation | Passed; not deployed rollback proof |
| Frozen benchmark hashes / protected tracked paths | Verified unchanged |
| Hosted fatal lint / frontend contracts | Success |
| Hosted unit/chaos/security, Python 3.11, 3.12 and 3.13 | All success |
| Hosted entire offline suite / persistence / release validators | Success |
| Live AI generation or model-list requests requested by this task | Zero |

Closeout checks executed with exit 0:

```text
git status --short
git log -n 3 --oneline
gh run view 39136495988 --json headSha,status,conclusion,url,jobs
git ls-remote origin refs/heads/main refs/heads/fix/p0-lenovo-acquisition-20261018
```

The worktree was clean before this documentation update. The first two hosted
runs failed on clock-fixture and synthetic scheduling assumptions, respectively;
their details remain in the implementation handoff. No production timeout was
raised to make those tests pass.

## Limits and next-agent instructions

The old 9.7-second trace lacks stage measurements, so its exact elapsed-time
breakdown cannot be recovered or attributed entirely to diagnostics. Offline
controls reproduce diagnostic starvation, not the original production timing.
The live capture preceded final additive telemetry/test corrections; it is not
an exact-final-build or deployed-production acceptance claim. Its local channel
configuration also differed from the earlier production failure.

Python cannot forcibly terminate running provider threads; transport bounds and
global worker admission remain necessary. Useful acquisition is demonstrated
within this case, not guaranteed for every provider or company. Independent
research-accuracy acceptance, full accessibility, provider authorization,
production dossier durability and historical corruption recovery remain open.
No historical dossier was repaired or overwritten, and no frozen labels changed.
Upstream account usage was not independently audited.

Review the fix-branch diff and CI before considering a release. Do not repeat the
live investigation automatically or enable AI for regression runs. Reuse saved
responses and labeled offline failure controls for UI work. Deployment and
production parity must be explicitly handled as a subsequent release step.
