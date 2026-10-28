# Personal Watch selection and transcript repair — 2026-10-28

## Decision and scope

**Partial research acceptance.** Personal Watch can now retain and publish actual
speaker turns from acquired interview transcripts. Mary Barra's saved sources now
yield one 37-word attributed quotation plus 62 words of commentary; breadth and
depth remain limited. Trending retained
older background but acquired no articles within its 48-hour current window.
These limitations are not resolved by larger raw word counts or passing tests.

User accepted a focused continuation: improve Personal Watch discovery, correct
rights-review false positives, preserve DEEP defaults and explicit server caps,
improve publisher selection, then check two Personal Watch subjects and Trending.
Three local investigations were followed by one bounded Mary Barra post-fix
investigation. Saved captures were used for subsequent interpretation repairs
and browser verification; no additional research requests were made for replay.

Working branch: `fix/personal-evidence-20261028`, base
`8b5a9a55a8df030ccb86ccbd1f99be959e6885d7`, plus preserved uncommitted work.
Implementation is in the isolated `.scratch/deployment-20261028` checkout.
Original root and remediation worktrees remain preserved. No push, merge or
deployment occurred in this continuation. Production remains the previously
deployed `ec5bef1` application; this report does not attest new production bytes.

[Measurements](evidence/2026-10-28_personal_selection/measurements.json) ·
[Final browser measurements](evidence/2026-10-28_personal_selection/browser-final-summary.json).

## What the actual sources established

| Observation | Seconds | Candidates | Reads / successful captures | Article bodies / raw article words | Qualified sources | Published passage words | Older background words |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Mary Barra, initial live | 119.35 | 37 | 18 / 6 | 0 / 0 | 0 | 0 | 0 |
| Fei-Fei Li, initial live | 67.17 | 25 | 20 / 16 | 9 / 17,154 | 1 | 113 | 0 |
| battery recycling, live | 53.59 | 20 | 7 / 2 | 2 / 2,656 | 0 current | 0 current | 338 |
| Mary Barra, interview-first live | 94.01 | 42 | 17 / 11 | 4 / 5,309 | 1 | 62 | 0 |
| Fei-Fei Li, final offline native replay | Not live latency | Same saved set | Historical observations only | Same nine saved bodies | 3 | 5,773 | 0 |
| Mary Barra, final offline native replay | Not live latency | Same saved set | Historical observations only | Same four saved bodies | 2 | 99: 37 statement + 62 context | 0 |

Counts are native pipeline observations, not distinct verified claims or recall
measurements. Raw article words include irrelevant material. Replay rows cannot
be added to live rows as new acquisitions. All three final Fei sources share
`singjupost.com`; all four post-fix Mary article captures share
`deadlinedetroit.com`. Publisher independence is not established.

The initial three-case application fingerprint was
`9c080cac9693a415f0d8917f3a6fb81dcbdfa90d7c509c375b6c3a7caf505053`.
The later Mary live application fingerprint was
`4f2a90527ebe135e49d416dfb4d96b3a43f6adcb3410acfac63c0240e0dadb15`.
Each remained stable throughout its own live run. Final speaker-list and
rhetorical-scam and incidental surname corrections were tested afterward offline; they are not claimed
as part of that Mary live code version. External ranking/content can change,
so the two Mary runs are observations rather than a controlled causal estimate.

## First useful-source losses and corrections

### Personal discovery and read selection

Mary's initial query still began with `"Mary Barra" public statement`.
`HarvestingEngine.run` correctly separates explicitly requested specialist tasks
from ordinary name-only requests, but the latter uses `_OBJECTIVES.personal`.
Changing `_TASK_ANGLES.PUBLIC_STATEMENT` alone therefore did not affect that path.
Both now prioritize the exact quoted name plus `interview`, retaining separate
identity-threat searches and caller-specific objectives. The new regression
checks both paths, rather than only explicit specialist-task queries.

Initial Mary reads produced no article bodies: three unresolved publisher
wrappers, one reader-not-selected outcome, seven budget-exhausted outcomes and
one access denial. Successful captures were indexes/homepages/metadata. The
post-fix run acquired four real articles, with three publisher-resolution and
three access failures. Those articles were executive/pay commentary; three
initially had no task-relevant passage. Later saved-body review found an actual
quotation attributed to Barra in one rejected article. The late surname repair
below recovers that paragraph offline. An initial rejection is not proof that
the retained body contains no useful text.

`score_candidate` gives observed statement/interview formats more read priority
and penalizes clearly speculative executive headlines without statement cues.
For Personal Watch and Trending, a bounded same-publisher penalty favors
comparable unused publishers. Its size cannot demote a relevant candidate below
an unrelated new publisher simply for diversification. Selection signals do not
qualify snippets as bodies or make evidence independent.

### Acquired transcripts were lost at passage attribution

Fei's initial report published an introductory paragraph and editorial note,
despite retaining substantial actual transcript text. Three concrete causes:

1. `_transcript_speaker_section` required a standalone `TRANSCRIPT:` delimiter;
   the saved source uses a transcript title and repeated colon speaker turns.
2. `DR. FEI-FEI LI` did not match the target after normalization of honorifics.
3. `public_statement_attribution` excluded observed transcript turns discovered
   through an identity-threat query. A planner angle should not override the
   contents of an actually acquired, structurally eligible article.

The corrected boundary logic retains the existing explicit-marker mode and
supports titled transcripts only with at least three observed colon turns by
two distinct full-name speakers. Honorifics are normalized for matching, not
removed from source text. Editorial introduction, host questions/advertisements,
speaker rosters and paragraphs crossing speaker boundaries cannot borrow the
target's attribution. Incidental discovery requires a native acquired article;
metadata, feed indexes and author shortcuts do not qualify.

The introduction classifier also recognizes the observed “The following” form.
Personal Watch's final statement allowlist now includes the already-defined
`OBSERVED_TRANSCRIPT_SPEAKER_SECTION` state. Previously those attributed turns
could reach the workbench while disappearing from native `public_statements`.

Final offline native/API/SSE replay publishes 90 exact paragraphs, 5,773 words,
three source records and 16 bounded native statement observations. All passage
offsets resolve to the original retained body, and original IDs, URLs, titles,
dates and body hashes are unchanged. This includes actual discussion of vision,
AI research and autobiographical context. It is publisher-attributed text, not
authenticated speech or independent verification against the original recordings.
Publication dates remain unknown where the retained metadata does not establish
them. Captured decoding replacement characters were preserved, not guessed away.

### Rhetorical “scam” was incorrectly treated as identity abuse

Mary's post-fix article quotes criticism of compensation and stock buybacks,
calling the transaction a scam. The generic personal passage classifier promoted
the word into an identity allegation. It is now `SOURCE_REPORTED_CONTEXT` unless
the passage describes an abuse mechanism/incident, such as phishing, impersonated
accounts, solicitations, victims or reported fraud charges. Actual reported scam
and synthetic-media controls remain investigable and explicitly unverified.

Replaying that same Mary payload changes identity risk from
`UNVERIFIED_ALLEGATIONS` to `UNASSESSED`, retaining the 62-word source assertion
and emitting no threat. A later surname correction also retains a separate
37-word quotation attributed to her in a second article. This is not confirmation
that the quoted financial accusation is true, or that the subject is safe.

### Final saved-body review recovered an incidental surname quotation

One acquired article contains an explicit quotation followed by “Barra said”
about American manufacturing. The pipeline had rejected it because an incidental
identity-search path only recognized full-name quotations. Additionally,
`_captured_surname_unambiguous` mistook sentence-leading “Perhaps” and “Despite”
for competing given names, and did not normalize the period in `Ms.`.

Both public-statement and incidental native-article paths now require the same
observed full-name introduction, explicit quote/reporting-verb linkage and
no competing given name. A small connective/adverb exclusion prevents those
grammatical words from creating fictitious competing people; actual alternative
names still block attribution. Metadata, indexes, disputed quotations and
speaker mismatches remain excluded. This is attribution, not identity or truth
authentication. A genuine 787-word saved body plus a competing-name and index
control exercises the failure. No new network request was made.

Final Mary native replay publishes two records/99 words: one 37-word reported
statement and 62 words of criticism/context. This is a bounded recovery, not
substantial multi-source research or a current authenticated statement.

### Rights observations, budgets and Trending

- `extract_readable_page` records a generic copyright footer separately as
  `rights_notice_observed`. It no longer treats every “all rights reserved” footer
  as a specific exception to an otherwise reviewed source licence. Explicit
  third-party, republished-with-permission and not-covered-by-licence notices
  remain review-blocking. Native, raw-pool and public-inspection projections
  preserve the observation. No licence, source permission or access bypass was
  granted by this change.
- `ResearchBudget.for_profile` rebases only implicit STANDARD defaults when a
  request selects DEEP. Explicit environment limits and directly constructed
  budgets remain binding. `run_harvest_pipeline` also takes the minimum of the
  profile, server budget and request timeout; a request cannot raise a server cap.
  These controls are covered offline; the live runner explicitly selected its
  DEEP caps, so its counts alone do not prove production default rebasing.
- Both battery-recycling article bodies were stale. Current evidence remained
  empty; 338 actual older passage words survived in the existing background
  section. This run does not demonstrate better fresh-source recall. It is less
  background than the preceding production sample's 580 words, not a yield gain.

## Implementation and regressions

| Owner | Changed behavior / regression |
| --- | --- |
| [harvesting.py](../../backend/services/research/harvesting.py), [candidate_selection.py](../../backend/services/research/candidate_selection.py) | Ordinary versus explicit-task queries, exact names, observed-format priority and bounded publisher diversity |
| [passage_records.py](../../backend/services/research/passage_records.py), [passage_extractor.py](../../backend/services/research/passage_extractor.py), [content_roles.py](../../backend/services/research/content_roles.py) | Transcript turn ownership, full-name attribution, introduction exclusion and rhetorical-scam context |
| [Personal assessment](../../backend/agents/personal_watch/assessment.py) | Transcript statement enumeration and incident-qualified reported fraud |
| [research_budget.py](../../backend/services/research/research_budget.py), [pipeline.py](../../backend/application/research/pipeline.py), [harvest_pipeline.py](../../backend/application/research/harvest_pipeline.py) | Default profile rebasing with preserved explicit bounds |
| [page_extraction.py](../../backend/infrastructure/acquisition/adapters/web/page_extraction.py), [native executor](../../backend/services/agent_reach/native/executor.py), [raw_pool.py](../../backend/services/research/raw_pool.py), [inspection](../../backend/schemas/evidence_inspection.py) | Generic rights notice retained separately from explicit article exceptions |
| [Selection regressions](../../tests/unit/test_oct28_evidence_selection_repairs.py) | Eleven cases covering rights notices, caps, both query paths, ordering and diversity |
| [Transcript regressions](../../tests/unit/test_transcript_speaker_sections.py) | Genuine saved Tim Cook and Fei turn controls, honorifics/timestamps, editor/host exclusion, merged turns, native statement enumeration and exact hashes |
| [Personal source reports](../../tests/unit/test_personal_source_reports.py), [native metadata](../../tests/unit/test_native_text_metadata.py), [useful-yield tests](../../tests/unit/test_useful_yield_repair.py) | Rhetorical versus incident reports, preserved genuine fake-stream detection, notice propagation and matching cross-channel objectives |

The new Fei fixture is an explicitly labeled exact contiguous prefix of the
actual native capture. It ends at an observed interviewer boundary and records
both the original body hash and prefix hash; it is not new live evidence.

## Browser proof and AI accounting

Six local Chromium states, at 390 and 1440 pixels, used exact saved native SSE
through real page buttons and renderers. API readiness was a harness stub and
all provider acquisition was blocked. All 90 Fei passages were reached through
12 workbench pages at each width; displayed text and total 5,773 words matched
the report. Final Mary showed two passages/99 words, separately labeled statement
and context; Trending showed no current
passages and 338 older words. No horizontal overflow or uncaught page exception
was observed. Fei mobile and Mary desktop captures were visually inspected.
This is rendering proof for local changes, not a new deployed investigation or
an accessibility certification.

Across the four live requests, three shared-budget advisory reservations were
consumed: two Gemini `gemini-3.5-flash-lite` successes (348 and 387 provider tokens,
735 known tokens total, 123 output tokens) and one read timeout with unreported
usage. The timeout is not counted as zero provider usage. Two bounded model
capability GETs were non-generation requests. No generation retries, key/model
fallback or quota probes were made; the existing shared local eight/day ledger
advanced 0 → 2 → 3 without resetting it. Advice did not become research evidence.
Offline replay/browser/tests used no live model generation. The earlier production
durable-policy-ledger requirement remains separate and unchanged.

## Verification and remaining work

Focused correction checks passed (77 cases before the final incidental-speaker
and rhetorical-context changes; 39 selection/transcript/source-report cases;
75 final useful-yield/source-report/statement/transcript cases). Failed intermediate controls were retained and corrected:
an over-strong publisher penalty, outdated footer semantics, an incorrect test
telemetry key, a scam-context rule that dropped a genuine solicitation paragraph,
and fraud-kind normalization. No new network request was used to repair a test.

The first full/fast closeout found two older assertions that still expected the
previous unquoted `public statement` query string: full 2,828 passed / 2 failed;
fast 2,620 passed / 2 failed. Those assertions now require the exact quoted-name
interview query while retaining all three channel/objective/attribution checks;
their 42-case file passed afterward. An intermediate complete rerun passed
2,830 full and 2,622 fast cases before the late surname correction. The last
new genuine-body test adds one case; final results below are for that code.

Final gates on the stabilized code all exited 0:

| Command / scope | Actual result |
| --- | --- |
| `python -m pytest tests/ -q` | **2,831 passed**, 132.94s pytest time |
| `python -m pytest tests/unit tests/chaos tests/security -q` | **2,623 passed**, 74.31s pytest time |
| `python -m flake8 backend tests scripts --count --select=E9,F63,F7,F82 --show-source --statistics` | Zero fatal findings |
| Each `tests/frontend/test_*.js` with Node | Ten scripts passed |
| `python scripts/validation/verify_frozen_benchmarks.py` | Frozen content unchanged |
| `python scripts/validate_release_candidate_smoke.py --output <fresh-temp-json>` | `OFFLINE_SMOKE_PASS` |
| `python scripts/validate_rollback_compatibility.py --output <fresh-temp-json>` | `OFFLINE_PERSISTENCE_PASS`; historical archive/deployed rollback not verified |
| Protected-tree Git diff, whitespace and new relative links | Passed |
| Final saved native replay and local browser replay | Two native replays / six viewport states passed; zero new network/model calls |

[Final gate accounting](evidence/2026-10-28_personal_selection/final-gates.json)
retains exact command scopes, exits and wall times. An isolated persistence pass
does not recover the historical 55 malformed dossiers or establish deployed rollback.
Smoke uses explicit isolated test mocks; it is not live research proof.

Remaining priorities: broader Mary statement discovery across suitable
publisher families; recent Trending articles; independently reviewed passage
quality and transcript authenticity; broader held-out subjects. No 20× useful
evidence target, universal subject coverage or completed research acceptance is
claimed. No further live requests or deployment are implied by this closeout.

Full native responses, saved bodies, SSE, raw logs and intermediate failures are
under the system-temp basename `aegis-personal-selection-20261028-cafk_ckt`.
Only selected sanitized measurements/images are durable here; temporary files
may expire. Protected dossiers, frozen datasets, research and artifacts remain
unchanged. Changes remain uncommitted and unpushed.
