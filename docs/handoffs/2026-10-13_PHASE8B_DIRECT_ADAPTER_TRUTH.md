# Phase 8B auxiliary direct-adapter truth — 2026-10-13

This checkpoint addresses a separate AgentReach acquisition path after the
recovered-operation work. It does **not** close the Stage 8B field-completeness
or pagination gate. Work was performed in the isolated
`feat/phase8b-extraction` worktree because another coding agent used the
original Phase 8 branch. Starting commit:
`da3b3b14bf7f9e0dd580609633f7fd722210cec3`, which passed
[hosted CI run 38371455913](https://github.com/Shaunakrane914/Misinformation/actions/runs/38371455913)
in all five jobs. That run precedes the direct-adapter changes below.

## Why this change

The [direct GitHub adapter](../../backend/services/agent_reach/native/adapters/github.py)
could fabricate zero stars, a `Code` language, a `github` author, publication
from a pushed timestamp, and a maximal semantic score when fields were absent.
The [YouTube adapter](../../backend/services/agent_reach/native/adapters/youtube.py)
fabricated a video title/channel and score. The
[web reader](../../backend/services/agent_reach/native/adapters/web.py)
promoted search-discovery dates to page publication. The
[search-index adapter](../../backend/services/agent_reach/native/adapters/search.py)
fabricated an index author, publication, score and snippet depth even for
title-only results. These are independent paths from the newer recovered
operation normalizer and could mislead downstream evidence weighting.

The adapters now leave missing normalized fields blank, retain observed
provider/discovery metadata separately, and return metadata depth for a
title-only search result. A candidate title in YouTube output is explicitly
tagged as discovery-origin when used. No absent value is filled to make a
record look richer. The changes are covered by
[normalization truth regressions](../../tests/unit/test_phase8_normalization_truth.py)
and the [acquisition policy tests](../../tests/unit/test_acquisition_policy_integrity.py).

## Measured checks and limits

- Focused adapter and acquisition-policy tests: 38 passed, exit 0.
- Final current-diff full offline suite: 1037 passed, exit 0. Fast
  unit/chaos/security: 841 passed, exit 0. Fatal Python lint: zero, exit 0.
  Five Node frontend contract scripts passed, exit 0. Frozen benchmark
  content hashes verified, exit 0. Offline release smoke and isolated
  rollback each exited 0; rollback's historical archive read-only and
  deployed previous-version checks remained `NOT_VERIFIED` here.
- These are fixture-driven normalization checks. They do not prove live
  GitHub/YouTube/web availability or the completeness of those providers'
  optional fields. See the [Phase 8B schema matrix](../architecture/PHASE8B_MAXIMUM_EXTRACTION_SCHEMA_MATRIX.md)
  and earlier guarded live probes for the separate observed traffic boundary.

No frozen benchmark dataset, historical dossier, credential or research
artifact was edited. No merge to `main` or public deployment was performed.
Commit/push and hosted CI for this checkpoint must be verified by exact SHA
after creation. This is a dated engineering handoff, not a raw transcript.
