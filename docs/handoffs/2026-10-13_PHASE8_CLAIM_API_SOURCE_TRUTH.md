# Phase 8 claim API source-truth checkpoint — 2026-10-13

This is a focused integrity checkpoint within Phase 8, **not** completion of
the full acquisition, frontend, deployment, or visual-browser acceptance
mandate. Work was done in the isolated `feat/phase8b-extraction` worktree while
another agent used the original branch. Starting commit:
`d16bc191aa1d16157742ab4de18cef3f636e270a`; the prior frontend commit
passed [hosted CI run 38366572171](https://github.com/Shaunakrane914/Misinformation/actions/runs/38366572171)
in all five jobs. This CI run does not cover the claim API changes here.

## Scope and decisions

- [Claim API](../../backend/api/claims.py) no longer turns failed research
  into medium-confidence evidence, maps `UNTRUE` to `TRUE`, labels model-only
  sentences as documents/wires, infers primary-source status from publisher
  names, invents executed queries from evidence counts, or produces a debunk
  package when no source-linked passage is returned. Absent inspectable
  evidence now yields `INSUFFICIENT_EVIDENCE`, null confidence and no action
  package. The response distinguishes heuristic non-echo nodes from verified
  independent groups. A URL and passage are an inspectability gate, **not**
  proof that the passage supports the verdict. Claims with only the current
  LLM string-list synthesis may now abstain; source-linked structured evidence
  must be supplied to recover decisive behavior safely.
- Synchronous claim/research/DB handlers use FastAPI's worker pool via regular
  `def` endpoints rather than blocking an `async def` event-loop handler.
- [Research agent](../../backend/agents/research_agent.py) JSON parse fallback
  returns zero evidence confidence rather than ambiguous 0.5.
  [Investigator agent](../../backend/agents/investigator_agent.py) empty/invalid
  response abstains with null confidence, does not claim monitored registries
  had no records, and avoids attaching a stale model-response provenance to an
  uncalled model.
- The shared lineage engine's empty-graph metric remains legacy behavior to
  preserve frozen Phase 4 replay-golden snapshots. The claim API scopes the
  truthful zero correction to its response and replay graph. Do not silently
  regenerate or overwrite those goldens; changing the shared contract needs a
  versioned migration and separate review.

Regression entry points:
[source-truth API tests](../../tests/unit/test_claim_source_truth.py),
[agent extraction tests](../../tests/unit/test_research_and_investigator_api.py),
[claim pipeline integration](../../tests/integration/test_claim_pipeline.py),
and [Phase 4 replay goldens](../../tests/unit/test_research_pipeline_golden.py).

## Observed validation

- Initial full and fast runs failed three Phase 4 replay-golden cases after a
  global empty-lineage metric change. That global change was reverted. The
  focused golden/source-truth rerun then passed 15/15 without changing the
  historical fixture.
- Final current-diff focused claim/agent/integration run: 26 passed.
- Final current-diff fast unit/chaos/security: 837 passed, exit 0.
- Final current-diff full offline suite: 1033 passed, exit 0.
- Fatal Python lint (`E9,F63,F7,F82`): zero, exit 0. Four Node frontend
  contract scripts passed, exit 0. Frozen benchmark content hashes verified,
  exit 0. Offline release-candidate smoke and isolated rollback scripts each
  exited 0. Rollback still reported historical archive read-only and deployed
  previous version as `NOT_VERIFIED` in this isolated checkout.
- `git diff --check` passed. None of these tests prove live provider behavior,
  visual/keyboard/mobile browser quality, production credentials, or deployed
  rollback. The 55 protected malformed historical dossiers remain unresolved
  in the original checkout.

## Continuation and gate

**Phase 8 remains PARTIAL.** The claim pipeline still needs citation-to-claim
entailment checks, actual source-role/independence derivation from acquisition
metadata, a versioned lineage metric correction, and richer structured
source-linked research output. The four specialized frontend workflows need
realistic response tests and visual/keyboard/mobile browser audit; no browser
surface was available in the enabled computer-use inventory. Complete 8B
extraction, 8C intelligence, 8D production scenarios, and 8F final audit
against their own acceptance criteria before claiming the project is done.

No frozen benchmark or historical dossier was edited. No merge to `main`,
deployment, or credential change was authorized or performed. This record is
a dated handoff, not a raw chat transcript. Commit/push and hosted CI for this
checkpoint must be verified by exact SHA after it is created; do not infer them
from the preceding frontend CI run.
