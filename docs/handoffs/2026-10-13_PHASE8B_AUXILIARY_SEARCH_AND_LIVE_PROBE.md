# Phase 8B auxiliary search-index and live adapter checkpoint — 2026-10-13

## Scope and code decisions

The user asked to continue the Phase 8 mandate and to leave engineering
reasoning for later agents. Work remained isolated on
`feat/phase8b-extraction` because another agent was editing the original
Phase 8 worktree. The starting commit was
`d04ffa25cee89f5a989ae16f1275346e9d46ea6b`; its exact
[hosted CI run 38372249008](https://github.com/Shaunakrane914/Misinformation/actions/runs/38372249008)
passed all five jobs. The code and first live sample were committed and pushed
as `21ce6aa2b75d2ab28663731123998494118bd0e3` on the isolated branch.
Its exact [hosted CI run 38374012939](https://github.com/Shaunakrane914/Misinformation/actions/runs/38374012939)
completed successfully in all five jobs, including the full offline suite,
unit/chaos/security on three Python versions, fatal lint, frontend contracts,
frozen-input integrity, smoke and isolated persistence checks.
No merge to `main`, deployment, credential change or original-worktree Git
operation was performed. The current handoff and clean-commit live sample are
append-only follow-up documentation; check their final commit/push state via
`git status --short --branch` and `git log -1`.

The [search-index adapter](../../backend/services/agent_reach/native/adapters/search.py)
previously turned an empty candidate into a successful record titled “Search
Discovery Record.” It now fails an empty title/snippet handoff without a
fragment. It marks the handoff as `network_observed_this_attempt: false` in
the document and normalized fragment: it carries a prior index observation,
not a fresh fetch of the target. This is deliberately narrower than claiming
live target content. The [regressions](../../tests/unit/test_phase8_normalization_truth.py)
cover both the empty and snippet-only paths. The fixed public-target
[auxiliary probe](../../scripts/audits/run_phase8_auxiliary_adapter_probe.py)
records only response lengths, field presence and metadata key names; a
[redaction test](../../tests/unit/test_phase8_auxiliary_adapter_probe.py)
guards against persisting response/evidence values. Its command and purpose
are indexed in the [script catalog](../development/SCRIPT_INDEX.md).

## Observed validation

All commands below ran from the isolated worktree. These are result summaries,
not reconstructed raw transcripts. The first live probe was on a dirty
checkout; its retained record is explicitly labeled as such. The
[second retained sample](../../artifacts/phase8_auxiliary_adapter_probes/2026-10-13_09-07-26Z/summary.json)
ran on clean commit `21ce6aa2b75d2ab28663731123998494118bd0e3`.
GitHub, web and YouTube each returned `SUCCESS` with one normalized fragment
on one fixed public target. GitHub author/publication were absent, web depth
was `SNIPPET`, and YouTube depth was `VIDEO_METADATA`. This is not a
provider-completeness, difficult-case, source-truth or 16-operation proof.

| Command | Observed result |
|---|---|
| `pytest tests/ -q -o addopts='--tb=short -ra'` | Exit 0; 1040 passed. |
| `pytest tests/unit tests/chaos tests/security -q -o addopts='--tb=short -ra'` | Exit 0; 844 passed. |
| `pytest tests/unit/test_phase8_auxiliary_adapter_probe.py tests/unit/test_phase8_normalization_truth.py -q -o addopts='--tb=short -ra'` | Exit 0; 13 passed. |
| `flake8 backend tests scripts --count --select=E9,F63,F7,F82 --show-source --statistics` | Exit 0; zero selected fatal errors. |
| All five `tests/frontend/test_*.js` scripts via Node | Exit 0; all passed (simulated DOM, not a browser visual audit). |
| `python scripts/validation/verify_frozen_benchmarks.py` | Exit 0; frozen content hashes verified. |
| `python scripts/validate_release_candidate_smoke.py` | Exit 0; `OFFLINE_SMOKE_PASS`, with disabled acquisition and test mocks. |
| `python scripts/validate_rollback_compatibility.py` | Exit 0; isolated `OFFLINE_PERSISTENCE_PASS`; historical archive and deployed rollback were `NOT_VERIFIED` in this worktree. |
| `python -m scripts.audits.run_phase8_auxiliary_adapter_probe` | Exit 0 twice; 3/3 fixed public targets returned one fragment in each bounded run. Only the second was on a clean commit. |
| `git diff --cached --check` and protected-input diff | Exit 0; no whitespace or tracked frozen-data, dossier or research changes. The new auxiliary summary is an intentional separate append-only artifact. |

## Gate boundary and next work

Stage 8A's separate protected-operation evidence remains as documented in the
[Phase 8B matrix](../architecture/PHASE8B_MAXIMUM_EXTRACTION_SCHEMA_MATRIX.md).
This checkpoint does not convert Stage 8B from **PARTIAL** to **PASS**:
pagination, difficult cases, comments and transcript context, and raw-provider
schema coverage still need measured work. Stage 8C's four-agent research
usefulness and evidence-truth evaluations, Stage 8D source expansion, Stage
8E real-browser responsive/accessibility verification, and Stage 8F final
release audit are not accepted by this checkpoint. The frontend contracts
pass in Node, but full frontend completion must not be inferred from them.
Historical dossiers remain protected; this isolated checkout cannot establish
readability or recovery of the outer worktree's malformed archive. No public
deployment is authorized.

Next agent: read the [Phase 8B schema matrix](../architecture/PHASE8B_MAXIMUM_EXTRACTION_SCHEMA_MATRIX.md),
confirm exact branch/CI state, then choose bounded extraction or agent-quality
work against measured baselines. Do not treat the search-index carrier as a
live visit to its target, promote metadata into article/video evidence, or
overwrite frozen or historical outputs to make a gate pass.
