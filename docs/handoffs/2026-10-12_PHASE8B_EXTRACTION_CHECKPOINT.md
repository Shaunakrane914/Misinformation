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
  documents each run. An important verification mistake was discovered after
  the first checkpoint: invoking the script by file path loaded the
  editable-installed **outer** checkout's backend in the nested worktree.
  Those early live records are retained as invalid isolated-branch proof. The
  runner now forces and checks its own repository import path; only the
  17:21Z guarded runs validate this branch. The
  [summarizer](../../scripts/audits/summarize_phase8_extraction.py)
  creates a new JSON path and refuses to overwrite historical evidence.
  Its latest 16-operation result distinguishes unobserved fields from empty
  fields. It is normalized-sample measurement, **not** raw-provider theoretical
  field coverage.
- Web read now extracts observed HTML title, explicitly declared author/date,
  headings and the publisher's unverified canonical claim. Missing dates stay
  blank; the actual native HTTP backend is no longer labeled `jina-reader`.
  Challenge-page metadata is discarded if the bounded fallback reader supplies
  content. Generic web reads always remain `PARTIAL_CONTENT` because length
  cannot prove complete article extraction. Two guarded live pages returned
  bounded partial content with no observed author or publication date.
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
| Focused web/acquisition tests after page metadata fix | 38 passed |
| Guarded live Stage 8B spot-check | GitHub/RSS/YouTube 6/6 usable across two scenarios each; web 2/2 partial content, source path asserted in run metadata |
| Initial hosted CI at `ca57e70` | [run 38283341137](https://github.com/Shaunakrane914/Misinformation/actions/runs/38283341137) **failed**: all Python jobs hit `ModuleNotFoundError: backend` in the new subprocess summary test; lint/frontend passed. The runner's own-checkout import bootstrap was added afterward and requires a new hosted run. |
| Corrected hosted CI at `7ad5932dd8a8c3e3c36e7b573287056e004ee6de` | [run 38284188252](https://github.com/Shaunakrane914/Misinformation/actions/runs/38284188252) **passed**: fatal Python lint/frontend contracts; fast unit/chaos/security on Python 3.11, 3.12 and 3.13; entire offline suite, persistence/release validators and tracked-output integrity. |
| First full suite, before nested-worktree isolation fix | 990 passed, 1 failed (`database.supabase is None` assertion) |
| First fast suite, same environment issue | 794 passed, 1 failed |
| Failing isolation test after fix | 1 passed |
| Intermediate full/fast suites before web correction | 991 / 795 passed, exit 0 |
| Final `pytest tests/ -q -o addopts='--tb=short -ra'` | **994 passed**, exit 0, 50.81s |
| Final `pytest tests/unit tests/chaos tests/security -q -o addopts='--tb=short -ra'` | **798 passed**, exit 0, 24.49s |
| Fatal flake8 command from `AGENTS.md` | exit 0, 0 findings |
| `python scripts/validate_release_candidate_smoke.py` | exit 0, `OFFLINE_SMOKE_PASS` |
| `python scripts/validation/verify_frozen_benchmarks.py` | exit 0, content hashes verified |
| `python scripts/validate_rollback_compatibility.py` | exit 0, `OFFLINE_PERSISTENCE_PASS` **only in the isolated worktree**; historical archive read-only check was `NOT_VERIFIED` because ignored historical dossiers are absent there |
| Git diff check | no whitespace errors |

The original checkout's protected historical archive remains known to have
55 malformed JSON files and legacy-unsealed records. The isolated worktree's
rollback result does **not** supersede that limitation. No dossier or frozen
benchmark was changed. The corrected Phase 8B code/evidence checkpoint was
committed and pushed, and its exact hosted CI run passed. This handoff update
is documentation-only; its own final CI status is reported in the final
handoff response. No merge or deployment was performed.

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
