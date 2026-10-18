# Research-quality completion — implementation handoff, 2026-10-18

**PARTIAL: code/calibration checkpoint, not research-quality or release acceptance.**

## Scope and ownership

User requested focused research accuracy, starting with BrandShield and Personal
Watch; terminal output first, then frontend, normal testing with no AI generation.
User chose an independent reviewer packet, then requested a 10–14 day bounded
v1 sequence and roughly 10–15 cases per agent. The packet now has 48 unfilled
slots (12 per agent). No invented independent answers or passing accuracy score.

Work in `.scratch/phase9-remediation-20261016`, branch
`feat/continuous-source-intelligence-20261017`, base
`314bf17697f1424bf9aa0d60704b42d87bf8e244`. Preserve all pre-existing Netlify,
model/configuration and frontend changes. This agent did not stage, commit,
push, merge or deploy. Files unexpectedly became staged and BrandShield's
target-context filter changed during validation; the user said no other agent
should be writing. The existing index was not reset or altered. Some final
working-tree edits are newer than its staged snapshot: do not commit that
snapshot blindly. Read the complete current diff, including untracked files.

## Implementation map and rationale

- [BrandShield assessment](../../backend/agents/brandshield/assessment.py):
  passage-context filtering, encyclopedia/warning/metadata exclusions, explicit
  suspicious-offer retention, reporting-versus-actor distinction. Broader legacy
  threat taxonomy remains compatible; fixed heuristic scores are not calibrated.
- [Content roles](../../backend/services/research/content_roles.py),
  [passage records](../../backend/services/research/passage_records.py),
  [extractor](../../backend/services/research/passage_extractor.py): reader
  wrapper metadata cannot supply incident evidence; prioritize relevant complete
  paragraphs, preserve exact offsets, and observe speaker sections/surname quotes
  without identity authentication. Encyclopedia/raw captures remain inspectable.
- [Entity resolver](../../backend/services/research/entity_resolver.py),
  [relevance gate](../../backend/services/research/relevance_gate.py),
  [source planner](../../backend/services/agent_reach/source_planner.py): repeated
  given-name tokens aren't independent context; acquired body context and bounded
  public-statement searches improve qualification without lowering access gates.
- [Financial comparison](../../backend/services/research/financial_observations.py):
  Decimal monetary-scale equivalence with matching currency/context, no FX
  conversion or range/actual conflation.
- [Trending clustering](../../backend/agents/trending/clustering.py): publisher
  tier and headline keywords cannot adjudicate truth; count-velocity wording is
  explicit about its limits.
- [Synthesis](../../backend/application/research/synthesis.py): a URL is not a
  proposition. [Specialist brief](../../backend/services/research/specialist_brief.py):
  observed statements count consistently, using subject identity rather than a
  query URL, without presenting statements as proof of safety or abuse.
- [Terminal harness](../../scripts/audits/run_terminal_agent_quality.py): optional
  per-case queries, empty overrides omitted, grouped native metadata not treated
  as source arrays; saved processing never permits live AI and blocks network.
- [Offline scorer](../../scripts/evaluation/evaluate_research_quality.py): exact
  coverage, frozen label digest and captured source hashes, exclusive output,
  separate accuracy/abstention/retrieval/span metrics. Empty labels fail. Declared
  reviewer independence and exact span matches do not establish entailment.

Calibration regressions:
[specialist/context/financial tests](../../tests/unit/test_research_quality_completion.py)
and [scorer/harness tests](../../tests/unit/test_research_quality_evaluation.py).
These deliberately are **not independent held-out evaluation**.

## Evidence and commands actually run

The [review](../testing/RESEARCH_QUALITY_COMPLETION_REVIEW_2026-10-18.md) records
normal versus guided-source measurements and remaining research failures.
The [packet](../testing/RESEARCH_QUALITY_REVIEWER_PACKET_2026-10-18.md) is ready
for another reviewer to select, adjudicate and freeze cases, not an already
completed evaluation. The [proof index](../testing/evidence/2026-10-18_research_quality_completion/README.md)
separates final locked replay from intermediate harness failures.

| Command | Observed result |
| --- | --- |
| `python -m pytest tests/ -q` | Final backend snapshot: 1,422 passed, exit 0, 50.88s |
| `python -m pytest tests/unit tests/chaos tests/security -q` | 1,214 passed, exit 0, 27.40s |
| `flake8 backend tests scripts --count --select=E9,F63,F7,F82 --show-source --statistics` | 0 fatal errors, exit 0 |
| All `node tests/frontend/test_*.js` scripts | All eight discovered scripts passed, exit 0 |
| `python scripts/validate_release_candidate_smoke.py` | `OFFLINE_SMOKE_PASS`, exit 0; temporary storage/test mocks |
| `python scripts/validate_rollback_compatibility.py` | `OFFLINE_PERSISTENCE_PASS`, exit 0 for isolated worktree scope; not deployed rollback |
| Same rollback command with `--archive` pointing to original checkout dossier directory and fresh `--output` | `HISTORICAL_ARCHIVE_FAIL`, exit 1; 2,445 legacy-unsealed, 55 failed, zero verified |
| `python scripts/validation/verify_frozen_benchmarks.py` | Hashes verified, exit 0 |
| `git diff HEAD --name-only -- tests/retrieval_benchmark backend/data/dossiers artifacts research` | No changes in protected tracked paths |
| `git diff HEAD --check` | Existing unrelated frontend README trailing blank line reported; no silent cleanup of user-owned work |
| AI-disabled terminal harness | Twelve normal local plus four guided-source investigations; later processing offline; no live AI generation/model-list calls |
| Chromium saved-SSE replay | Four agents at three widths, final source/query input correction documented in proof; not production requests |
| Read-only deployed GETs | Cloudflare navigation 200 with Render origin; Render health timed out, end-to-end NOT VERIFIED |

Some initial commands failed: a nonexistent test path collected nothing; a test
fixture omitted a required `content` field; the stricter filter initially dropped
legitimate positive fixtures (two then five full-suite failures); saved processing
initially concatenated a grouped dict as records; an empty optional override
replaced Trending's actual topic. These were corrected and rerun. Intermediate
logs remain in the temporary tree; they are not hidden as successful runs.
An ad-hoc import briefly resolved the older outer checkout instead of this
worktree; it made no generation call and is excluded from verification evidence.
Use an explicit workdir and the guarded harness, not unisolated imports.

## Reproduction (portable commands)

From this worktree, use a new system-temp output directory for every run and
the local server-side `.env` path appropriate to the machine. Never print it.

```powershell
$runDir = Join-Path $env:TEMP ('aegis-specialist-' + [guid]::NewGuid())
python scripts/audits/run_terminal_agent_quality.py --allow-live --env-file .env --output-dir $runDir --case 'brandshield:REVIEWER_TARGET' --case 'personal_watch:REVIEWER_SUBJECT'
```

`--allow-live` allows acquisition, **not AI**. Do not add `--allow-live-ai`.
For saved processing add `--capture-from` with matching numbered native JSON
files; that mode blocks live network. `--query=` omits an optional override;
the actual Trending topic remains its required query. Guided URL results must
not be described as autonomous topic discovery. Browser replay uses the existing
`run_phase9_four_agent_browser_audit.py --replay-dir` and actual pinned Chart.js
bytes; external fonts are deliberately blocked, transport is explicitly replayed.

## Safe continuation / owner actions

1. No more structural rewrites, extra websites or cosmetic redesigns. Fix actual
   positive incident acquisition and unfamiliar-person discovery. DOJ's captured
   body ended before the incident; normal Tim/Fei remain profile-only. Do not
   paper over missing evidence with a title, URL or unsupported claim label.
2. Reviewer selects and freezes new cases before acceptance/tuning. The scorer
   does not automatically normalize every native risk taxonomy into proposition
   verdicts; missing explicit verdicts are a contract gap, not permission to guess.
3. Verify Scout on real comparable financial claims/tables and Trending on genuine
   temporal/independence observations. MSFT articles/AMD empty output don't prove
   those capabilities. Provenance/URLs aren't sufficient entailment checks.
4. Treat Render timeout, actual deployed AI settings, hosted CI of these local
   edits, accessibility, recovered historical dossiers and staged deployed rollback
   as unverified. The 55 malformed originals remain protected, unrecovered.
5. Review the mixed staged/unstaged tree before any separately authorized commit.
   Old five-job CI belongs to the old pushed checkpoint, not this implementation.
   Prepare demo/release only after the declared gates; otherwise release only an
   explicitly limited beta with owner approval. See the review's proposed 14-day
   timebox; no automatic monitoring or future completion is promised.
