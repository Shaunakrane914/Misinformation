# Phase 8B extraction checkpoint — 2026-10-12

This is a dated engineering handoff, not approval to merge or deploy. Read
[AGENTS.md](../../AGENTS.md), inspect the live branch/worktree and the
[schema matrix](../architecture/PHASE8B_MAXIMUM_EXTRACTION_SCHEMA_MATRIX.md)
before resuming.

## Scope, branch and concurrency

- User mandate: continue Phase 8 sequentially after the Phase 8A live gate,
  maximize legitimate extraction, measure richness and leave reproducible
  evidence for later coding agents.
- Phase 8A commit `0731171cd10045239a30115179436c45a92a31b7` was pushed;
  [hosted CI run 38240609031](https://github.com/Shaunakrane914/Misinformation/actions/runs/38240609031)
  passed for that exact SHA. This does **not** validate Phase 8B changes.
- Another coding agent was confirmed to be committing to
  `feat/phase8-real-acquisition-proof` concurrently. Its commits included the
  initial GitHub/RSS/YouTube extraction edits in `b478906` along with unrelated
  documentation/script changes. No existing commit was reset or rewritten.
- This work was isolated in an ignored Git worktree at
  `.scratch/phase8b-worktree` on `feat/phase8b-extraction`, based on
  `f0a41b7`. The source checkout and its protected files were not cleaned.
  Integrate the branches deliberately after concurrent work stops.

## Implemented and observed

- GitHub `read` now decodes README content from the bounded official Contents
  API response instead of requiring a second raw-host fetch. Path, SHA,
  source URL and transport are retained. A README is classified as
  `PARTIAL_CONTENT`, not full repository evidence. Live samples returned
  partial README content for two public repositories.
- RSS now retains feed/entry identity, GUID, observed dates, author/publisher,
  categories, enclosures, longer summary and bounded content blocks. Full
  *feed-entry* content is distinguished from summary, but neither is promoted
  to the linked article. One live feed had a content block; another was
  summary-only.
- YouTube read now carries observed metadata fields (ID, channel, date,
  duration, available counters/tags/categories/status), still labeled video
  metadata. One live target populated all listed field names. Unknown dates in
  YouTube search/comments and Xiaoyuzhou normalization are no longer set to
  `Recent`; comment epochs become UTC only when actually supplied.
- The probe runner now records bounded normalized field-presence names and
  author without retaining new response bodies. The
  [spot-check artifact index](../../artifacts/phase8_extraction_spotchecks/README.md)
  documents each run. The
  [summarizer](../../scripts/audits/summarize_phase8_extraction.py)
  creates a new JSON path and refuses to overwrite historical evidence.
  Its 16-operation results are normalized-sample metrics, **not** raw-provider
  theoretical field coverage.
- A nested-worktree test-isolation bug was found: dotenv discovered the outer
  checkout's `.env`, leading to a Supabase client during offline tests. The
  test setup now sanitizes keys from the same discoverable file before app
  imports. No credentials were printed or used by the probe runner.

## Commands actually run

| Command / check | Observed result |
|---|---|
| Focused acquisition tests after extraction edits | 35 passed |
| Focused acquisition/audit tests after date fix | 41 passed |
| Extraction summarizer overwrite contract | 1 passed |
| First full suite, before nested-worktree isolation fix | 990 passed, 1 failed (`database.supabase is None` assertion) |
| First fast suite, same environment issue | 794 passed, 1 failed |
| Failing isolation test after fix | 1 passed |
| Final `pytest tests/ -q -o addopts='--tb=short -ra'` | **991 passed**, exit 0, 28.97s |
| Final `pytest tests/unit tests/chaos tests/security -q -o addopts='--tb=short -ra'` | **795 passed**, exit 0, 13.13s |
| Fatal flake8 command from `AGENTS.md` | exit 0, 0 findings |
| `python scripts/validate_release_candidate_smoke.py` | exit 0, `OFFLINE_SMOKE_PASS` |
| `python scripts/validation/verify_frozen_benchmarks.py` | exit 0, content hashes verified |
| `python scripts/validate_rollback_compatibility.py` | exit 0, `OFFLINE_PERSISTENCE_PASS` **only in the isolated worktree**; historical archive read-only check was `NOT_VERIFIED` because ignored historical dossiers are absent there |
| Git diff check | no whitespace errors |

The original checkout's protected historical archive remains known to have
55 malformed JSON files and legacy-unsealed records. The isolated worktree's
rollback result does **not** supersede that limitation. No dossier or frozen
benchmark was changed. No Phase 8B hosted CI run or deployment was observed
as of this handoff draft; update this paragraph after any push/check.

## Decision and next engineering work

**Phase 8B gate: PARTIAL.** All 16 operations have time-bound live acquisition
and normalized richness records, but source-response field presence is not
audited for most operations; pagination, complete chronology, web article
structure, transcript segments and important-field success need more work.
Do not advance the main intelligence redesign on assumed complete contracts.
The next agent should:

1. Resolve concurrent branch ownership, then review the actual branch diff
   against `f0a41b7` before integration.
2. Extend bounded redacted raw-field-presence probes for all 16 operations and
   classify candidate fields as implemented, optional, restricted or
   unavailable with evidence. Keep complete response bodies out of artifacts.
3. Add pagination/continuation and important-field fixtures where permitted,
   then rerun live spot-checks and the full offline gates.
4. Reconcile historical-dossier rollback using the original checkout or a
   read-only mounted archive; never copy, overwrite or silently repair the
   protected dossier files merely to obtain a green isolated-worktree result.
5. Push and verify hosted CI for the exact Phase 8B commit before calling this
   checkpoint remotely verified. No merge to `main` or deployment is authorized.
