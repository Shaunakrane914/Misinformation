# Phase 8 frontend truth checkpoint — 2026-10-13

This is a frontend *integrity* checkpoint, not the complete four-agent Stage
8E redesign. The owner asked to finish the frontend and the whole Phase 8
mandate before a completion report. Continue in the isolated
`feat/phase8b-extraction` worktree because another agent is using the original
Phase 8 branch. Inspect actual status/diff first; preserve concurrent work.
The starting commit for this checkpoint was
`60a76a55f66de201c5a1e52803c18025b0b5bb08`; its exact SHA passed
[hosted CI run 38345383376](https://github.com/Shaunakrane914/Misinformation/actions/runs/38345383376)
in all five jobs. That CI result does **not** cover the frontend changes here.

## Verified defect and decision

The old [Investigator page](../../frontend/investigator-agent.html) called a
client-side language model with no retrieved source bundle and, on failure,
returned an attractive fabricated dossier claiming absent filings, formal
denials, timed amplification, source clusters and successful registry checks.
This was unacceptable misinformation UX. The page is now a focused gateway to
the existing [claim verification workspace](../../frontend/submit.html), using
one-time `sessionStorage` transfer instead of putting the claim in a new URL.
It no longer performs a separate client-model investigation or displays a
sample dossier as a live result. The previous page remains recoverable in Git
history; no historical research artifact was removed.

The claim workspace formerly substituted model-generated verdicts/evidence
when the backend failed, showed timer-driven fake research stages, inferred
evidence strength from a confidence number, invented default reasons/source
roles/groups/retrieval methods, put unknown-stance evidence in the refuting
column, and allowed unsafe source schemes in evidence links. The page now
returns `INSUFFICIENT_EVIDENCE` with empty evidence on backend failure, shows
only an actual waiting state, preserves unknown values, keeps unclassified
evidence inspectable, and permits only credential-free HTTP(S) source links.
It also withholds a decisive backend verdict in the visible claim workspace
when no attached item has both an inspectable source URL and readable passage.
This is a frontend guard, not proof that the cited passage supports the claim.
The [shared report renderer](../../frontend/unified-report-renderer.js) no
longer asserts that a heuristic source-group count proves independent
publishers or that absent contradiction/change records prove none exist. It
also handles malformed telemetry/lineage and null report envelopes safely.

The [frontend runbook](../../frontend/README.md) was updated so later agents
do not look for a nonexistent `operation-health.html` page.

## Tests and limits

- [Claim UI truth test](../../tests/frontend/test_claim_ui_truth.js) executes
  the real inline claim controller with a simulated DOM, checks backend-offline
  abstention, unsupported decisive verdicts, unknown verdict/stance, URL
  rejection and the investigator
  handoff. [Renderer test](../../tests/frontend/test_unified_report_renderer.js)
  covers missing contradiction/change data, heuristic source groups, malformed
  telemetry, invalid links and null responses.
- All four Node frontend test scripts passed locally after these changes.
  These are simulated DOM/fetch contracts, **not** visual, keyboard-only or
  narrow-screen browser observations. The enabled computer-use inventory had
  no browser/app surface; no screenshot or browser acceptance is claimed.
- The first full-suite run found one obsolete test assertion requiring the
  retired client-model fallback. After changing that test to require explicit
  abstention, focused product-integrity tests passed (11/11), the full suite
  passed (1029/1029), and the fast unit/chaos/security suite passed (833/833).
  Fatal lint reported zero issues. Frozen benchmark content hashes verified;
  release-candidate smoke and isolated rollback scripts exited 0. Rollback
  reported the actual historical archive and deployed previous version as
  `NOT_VERIFIED`. These checks are offline; hosted CI on the new SHA must be
  checked separately.

## Open work and product gate

**8E remains PARTIAL.** The four specialized pages still need realistic
backend-response fixtures and end-to-end workflow checks, responsive/keyboard
browser audits, accessible status/loading/failure treatment, and a coherent
agent-specific design pass. Backend `/api/claims/verify` still warrants a
separate evidence-integrity audit: its no-evidence fallback includes a
pre-filled medium confidence string and its response labels some sources and
independence counts heuristically. Frontend abstention does not repair that
server contract. Stage 8B extraction and 8C/8D/8F are likewise not accepted.
The 55 protected historical malformed dossiers remain unresolved in the
original checkout; the isolated worktree cannot certify their recovery.

No merge to `main`, public deployment, credential change, frozen benchmark
edit or historical dossier edit was authorized or performed. Commit/push for
*this* checkpoint: pending at document creation; inspect Git and hosted CI for
the eventual state rather than treating this line as a permanent status.
