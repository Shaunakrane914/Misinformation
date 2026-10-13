# Phase 8B content decoding and important-field audit — 2026-10-13

This is an implementation checkpoint, **not** completion of Phase 8 or the
frontend redesign. Read [AGENTS.md](../../AGENTS.md), the
[prior Phase 8B handoff](2026-10-12_PHASE8B_FIELD_DETAIL_AND_UI_CHECKPOINT.md),
and inspect the actual branch/status before changing code.

## Scope and safe branch

- Owner request: continue the whole Phase 8 mandate, including the frontend;
  return a final completion report only when the work is actually accepted.
- This checkpoint started from `7fcf97a49e896a733b825eaa14bddeb4866fd267`
  on `feat/phase8b-extraction`, in the ignored isolated worktree
  `.scratch/phase8b-worktree`. Another agent was confirmed to be committing on
  the original Phase 8 branch. Do **not** merge/reset either branch implicitly.
- No frozen benchmark input, historical dossier, research tree, deployment,
  credential or original-worktree change was made. Three new spot-check
  directories are append-only, not replacements for older evidence.

## What changed and why

1. [The bounded HTTP transport](../../backend/infrastructure/acquisition/network/http.py)
   now provides explicit gzip/deflate entity decoding under both a wire-byte
   and expanded-byte limit. It rejects unsupported, malformed, concatenated or
   undeclared compressed entities. The original wire body remains intact for
   raw byte counts and SHA-256 provenance. This responds to an observed
   provider sending gzip despite `Accept-Encoding: identity`.
2. [The native web reader](../../backend/services/agent_reach/native/executor.py)
   uses the decoder before HTML/text extraction, rejects binary controls and
   non-text MIME types, and records decoded length separately from raw wire
   length. Its transport record remains paired with the actual selected
   primary/fallback body. Other HTTP-backed parsers and the typed web/Jina
   adapters use the same bounded decoder. The typed web adapter no longer
   invents `Web Publisher` as author or labels a character-capped page as a
   `FULL_ARTICLE`.
3. [The audit runner](../../scripts/audits/run_phase8_live_acquisition_audit.py)
   records names of *populated* nested provider/page fields without storing
   values. [The summarizer](../../scripts/audits/summarize_phase8_extraction.py)
   measures a declared minimum important-field set for each of the 16
   protected operations, distinguishing populated, empty and unobserved.
   These are small normalized samples, **not** raw-provider completeness.
4. The [schema matrix](../architecture/PHASE8B_MAXIMUM_EXTRACTION_SCHEMA_MATRIX.md)
   and [spot-check index](../../artifacts/phase8_extraction_spotchecks/README.md)
   explicitly correct the earlier false web-read success. The old 17:37Z
   common-page excerpt had 243 replacement/control characters in its first
   400 characters; the 02:49Z pre-fix re-probe reproduced the defect. Both
   historical records remain available as negative evidence, not valid page
   text proof.

## Actual local verification

| Check | Observed result |
|---|---|
| Focused HTTP/acquisition/summary regressions | 34 passed before the cross-adapter expansion; 81 passed after the expansion, both exit 0 |
| Final full `pytest tests/ -q -o addopts='--tb=short -ra'` | 1,012 passed in 66.04s, exit 0 |
| Final fast `pytest tests/unit tests/chaos tests/security -q -o addopts='--tb=short -ra'` | 816 passed in 28.74s, exit 0 |
| Fatal flake8 command from `AGENTS.md` | exit 0, 0 findings |
| Node `tests/frontend/test_*.js` | three scripts passed, exit 0; simulated DOM/fetch only |
| Frozen benchmark verifier | exit 0, hashes verified |
| Offline release smoke | exit 0, `OFFLINE_SMOKE_PASS`; test mocks and no live acquisition |
| Rollback validator in isolated worktree | exit 0, `OFFLINE_PERSISTENCE_PASS`; historical archive `NOT_VERIFIED` because ignored protected dossiers are absent in this worktree |
| Live 16-operation guarded common-case probe | 16/16 classified usable at [02:53Z](../../artifacts/phase8_extraction_spotchecks/2026-10-13_02-53-55Z/), on dirty pre-commit code |
| Live web common/high-content follow-up | 2/2 readable bounded excerpts, observed title/headings, zero replacement/control chars at [02:55Z](../../artifacts/phase8_extraction_spotchecks/2026-10-13_02-55-36Z/); filtered run is not a 16-operation gate |
| Important-field summary | [v6 machine output](../../artifacts/phase8_extraction_spotchecks/2026-10-13_02-55-36Z/richness_summary_v6.json); latest matching scenario wins, no provider completeness claim |
| Browser visual/keyboard/narrow-screen audit | NOT VERIFIED: no enabled browser surface was available in the UI inventory |
| Hosted CI on these changes | NOT VERIFIED at this checkpoint; require exact committed SHA and hosted run before acceptance |

The live artifacts' `run_metadata.json` records the dirty checkout and code
location. No full raw response body or private credential is retained. The
current tests use controlled fixtures; only the explicitly labeled live
probe exercised real providers. Keep old and new runs distinct.

## Gate and next-owner decisions

- **8A PASS** remains the earlier 16-operation connection gate, but its old
  common web content must not be used as valid text evidence.
- **8B PARTIAL.** Current common/high-content web pages decode properly;
  important-field population is now measurable. Provider-optional fields,
  difficult cases, follow-up requests, pagination and marginal cost remain
  incompletely characterized. A 16/16 classifier count is not a completeness
  percentage.
- **8C–8F not accepted.** Shared intelligence, agent-specific evaluation,
  source expansion, complete frontend workflows, visual accessibility and
  adversarial end-to-end quality audits remain. Shared-renderer hardening from
  the prior checkpoint is not the full Stage 8E redesign.
- Deployment and merge to `main` remain blocked. The 55 malformed historical
  dossiers in the original checkout are protected and unresolved; an empty
  isolated archive does not validate historical rollback.

Reproduce with the five commands in [AGENTS.md](../../AGENTS.md), the Node and
frozen commands in the [testing runbook](2026-10-12_ARCHITECTURE_REMEDIATION_TESTING.md),
and the bounded live probe runner with `--max-scenarios 1` or
`--operations web.read --max-scenarios 2`. Use a **new** output directory for
each run; never overwrite older artifacts. New web evidence requires an
observed readable excerpt and provenance, not merely HTTP 200 or a classifier
label. This record contains engineering conclusions, not a fabricated raw
transcript or private reasoning trace.

Commit/push state: **pending at document creation**. Check `git log`, branch
and hosted CI for the actual final state; do not infer it from this line.

## Checkpoint outcome and later web-detail work

The decoding/field-audit checkpoint was committed and pushed as
`a9a59585c6764d6e97c0f243639ce50eed44d6c4`. Hosted
[run 38340023007](https://github.com/Shaunakrane914/Misinformation/actions/runs/38340023007)
completed successfully for that exact SHA: fatal lint/frontend contracts,
fast unit/chaos/security on Python 3.11/3.12/3.13, and the full offline
suite with release/persistence validators. This validates **that checkpoint**,
not later uncommitted edits.

Subsequently, bounded HTML article/main observations were added in
[page_extraction.py](../../backend/infrastructure/acquisition/adapters/web/page_extraction.py):
links (unverified, not followed), table cells, blockquotes, figcaptions,
possible correction notices and selected publisher-declared JSON-LD fields.
Two focused web live probes at
[03:08Z](../../artifacts/phase8_extraction_spotchecks/2026-10-13_03-08-05Z/)
observed links on both pages and a JSON-LD declaration on one; absent optional
fields remain empty. The [v8 summary](../../artifacts/phase8_extraction_spotchecks/2026-10-13_03-08-05Z/richness_summary_v8.json)
records important-field population for these fields. One initial focused
test run failed because a fixture's `<article>` was incorrectly expected to
be a body fallback; after correcting the assertion, the focused 24-test run
passed. The final guarded re-probe at
[03:32Z](../../artifacts/phase8_extraction_spotchecks/2026-10-13_03-32-27Z/)
and [v9 summary](../../artifacts/phase8_extraction_spotchecks/2026-10-13_03-32-27Z/richness_summary_v9.json)
supersede the 03:08Z field-count view after eliminating synthetic fallback
titles and absent-canonical flags. Both sampled pages still had readable text
and observed links; only one had selected JSON-LD fields.

For these **later web-detail edits**, a subsequent full offline run reported
1,016 passed in 76.35s and the fast unit/chaos/security run reported 820
passed in 34.80s, both exit 0. Fatal flake8 found 0, all three Node frontend
scripts passed, frozen hashes verified, offline release smoke passed and
isolated rollback exited 0 with historical archive `NOT_VERIFIED`. Hosted CI
for these later edits is **not yet verified** at this handoff update. Do not
treat the earlier `a9a5958` hosted run as covering them.

## Web-detail CI and subsequent GitHub integrity work

The web-detail checkpoint was committed and pushed as
`620beecff25c7561769db926d8f7ac12447d3bfa`; hosted
[run 38342294739](https://github.com/Shaunakrane914/Misinformation/actions/runs/38342294739)
completed successfully for that exact SHA, all five jobs. It does not cover
the subsequent GitHub edits below.

The [GitHub route](../../backend/infrastructure/acquisition/routing/standard_handlers.py)
now distinguishes observed repository owner/last update from README
author/publication, does not invent missing issue/PR/commit/release attribution,
and labels issue/PR bodies and release notes `PARTIAL_CONTENT`, not
`FULL_ARTICLE`. Release asset metadata retains a provider-supplied digest when
available, but no asset bytes are independently verified. The
[executor](../../backend/services/agent_reach/native/executor.py) requests a
bounded ten-entry issue page for small limits because GitHub's issues API can
include PRs. It still returns at most the requested number of actual issues,
and exposes the count filtered as PRs and whether a next page exists.

The [03:53Z live probe](../../artifacts/phase8_extraction_spotchecks/2026-10-13_03-53-35Z/)
observed HTTP 200 with three provider entries, all filtered PRs, yielding zero
issues. The old audit classifier labeled that `NOT_FOUND` incorrectly. The
[audit runner](../../scripts/audits/run_phase8_live_acquisition_audit.py)
now distinguishes `EMPTY_RESULT` from a missing target; a
[03:55Z re-probe](../../artifacts/phase8_extraction_spotchecks/2026-10-13_03-55-58Z/)
retrieved three actual issue bodies after bounded overfetch. The
[v10 summary](../../artifacts/phase8_extraction_spotchecks/2026-10-13_03-55-58Z/richness_summary_v10.json)
selects the latest matching scenario across retained runs. The 03:53Z/03:55Z
pair observed 61,088/112,197 response bytes and 2,072/2,745 ms; timing
variation prevents treating that pair as a controlled cost estimate.

Focused GitHub/route/audit tests: 64 passed, exit 0. After the final GitHub
edits, the full offline suite passed **1,022** tests in 72.70s and the fast
unit/chaos/security suite passed **826** in 32.35s, both exit 0. Fatal flake8
found 0; all three Node frontend scripts, frozen-hash verification and offline
smoke passed. The isolated rollback validator exited 0 while reporting the
historical archive `NOT_VERIFIED`. Hosted CI for these latest GitHub changes
is **not yet verified** at this record update. The provider field boundary
and official documentation links are in the
[schema matrix](../architecture/PHASE8B_MAXIMUM_EXTRACTION_SCHEMA_MATRIX.md).
