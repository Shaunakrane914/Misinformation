# Production research failure repair — 2026-10-19

## Decision and scope

**Focused offline regression: PASS. Fresh acquisition and research-quality acceptance: NOT VERIFIED.**

This implements the requested October 18 failure repairs, not another architecture
phase. No provider investigation, Gemini/model/key/quota call, credential edit,
access-gate change, commit, push, merge or deployment was performed. The production
failure remains a real failure; replay cannot establish that an upstream publisher
is now reachable.

Branch: `fix/p0-lenovo-acquisition-20261018`; starting HEAD:
`39a514b68388450bbc5e6061aba97bda2077fc7f`. The worktree started clean. All changes
described here are **uncommitted**, on top of the existing patient-window/P0 fixes.
Final replay application fingerprint:
`df0dcf9bd27b5c7290fece6ffe9a505fa1ff36b4a24e6c9759d98e5f8052f442`.
Both terminal reprocessing and browser replay recorded an unchanged application
during their runs. This fingerprint is not a Git commit or deployment attestation.

See the [handoff](../handoffs/2026-10-19_PRODUCTION_RESEARCH_FAILURE_REPAIR.md)
and [selected measurements/screenshots](evidence/2026-10-19_production_research_repairs/README.md).

## A. Root causes and changes

Historical observations come from the [deployed release record](../handoffs/2026-10-18_RELEASE_PREPARATION_AND_DEPLOYMENT.md),
[saved-failure analysis](../handoffs/2026-10-19_SAVED_FAILURE_ROOT_CAUSES.md) and
[defect register](AEGIS_CONSOLIDATED_DEFECT_REPORT_2026-10-19.md). They are not new
live observations. Synthetic controls below use invented `.example` cases, not
hard-coded fixes for the four production targets.

| Failure / actual evidence | File/function | Repair and bounded proof |
| --- | --- | --- |
| Distinct unresolved Google News leads share one publisher quota; saved later Nike/Tim Cook audits excluded 14/6 leads this way. | `deep_reader.py`: `_selection_domain`, `_select_read_candidates` | Separate wrapper read opportunities within the existing attempt cap. Six synthetic wrappers are selectable; their actual source domains and independence classifications are **not** rewritten. Real publisher quotas remain in the selector. |
| Selected wrappers remain unresolved; older traces did not retain the three returned candidate titles/URLs and join rejections. This does not prove the provider returned no information. | `DeepReader._resolve_wrapper` | Preserve at most three observed candidates, title-token overlap and rejection reason; reject invalid/credential-bearing/Google URLs. Keep the existing 75% title join, bounded lookup and protected `service.read`. No guessed publisher URL or search snippet becomes a body. Upstream success still unverified. |
| Specialist reading stops after a failed selected batch despite remaining budget; query-class diversity can admit stock/background leads ahead of incident leads. | `reading.py`: `DeepReadingStage.run` | Prioritize task-matching brand/personal leads, record deferred off-task selections, reserve existing attempt slots for finite replacement batches. No repeated attempted URL, extra total attempt allowance or extended wall-clock deadline. Controlled failures followed by another candidate produce a source with acquisition IDs. |
| Generic follow-ups treat capitalized headline fragments as entities and ask for partnerships rather than the specialist objective. | `planner.py`: `plan_adaptive_follow_ups`; `adaptive.py` | Pass domain/intent and form bounded brand/identity queries. Financial/general behavior remains unchanged. This improves planning, not proof of incident discovery. |
| A wait can time out just before the next monotonic deadline comparison, leaving a tiny window for downstream search. Full-suite closeout reproduced one unexpected search; isolated original test passed. | `acquisition/service.py`: `retrieve_many`, `_read_with_deadline` | Latch source-read deadline exhaustion for the remainder of this retrieval. A deterministic executor-timeout control leaves clock time available but verifies search is `NOT_SUBMITTED`, not attempted. No global timeout increase. |
| A completed search with no remaining read opportunity could look merely evidence-insufficient. | `reading.py`; `acquisition_status.py`: `acquisition_outcome`; `assembly.py` | Record `READING_DEADLINE_EXHAUSTED`; zero acquired sources then become `ACQUISITION_FAILED`. Explain that discovery succeeded but reading could not start. Preserve query/read diagnostics. |
| Timeout/HTTP/policy/challenge/empty outputs were not consistently distinguishable; HTTP success alone could admit a challenge page. | `DeepReader.deep_read`, `_read_failure_kind`, `_http_status`, `_challenge_body` | Export categorical failure, safe message, observed HTTP code and SSRF/runtime rejection layer where available. Reject challenge-prefix bodies and empty extraction, avoid caching challenges. Synthetic cases cover timeout, HTTP 403, SSRF, runtime policy, empty body and CAPTCHA. No raw secret-bearing exception is copied to these new errors. This is not a complete new challenge detector or global log-redaction audit. |
| Captured body author differs from discovery/feed attribution; shared report preferred the latter. | `deep_reader.py`; `report_builder.py`; `unified_report.py`; `evidence_inspection.py` | Prefer the captured byline as an observation, retain both attributions with a conflict flag, carry public metadata through inspection and show the conflict. Neither attribution is independently authenticated. Canonical source/capture IDs are preserved. |
| Shared terms plus denial language produce established contradiction flags, and Scout polarity headings become disagreements. | `ContradictionDetector.detect_contradictions`; `synthesis.py`; Scout `assessment.py`; `ReportBuilder.from_scout` | Lexical matches are only `POSSIBLE_DISAGREEMENT`, never established/CONTESTED from that heuristic. Preserve available exact captured passage IDs/text/offsets and source IDs. Do not manufacture passages for title-only leads. Stop projecting the legacy for/against/unresolved headings as opposing propositions. |
| A legacy conflict type can still sound adjudicated in normalization/rendering. | `_complete_agent_report`; renderer `renderDisagreements` | Without explicit established review and paired passage references, normalize to a possible, unassessed review lead. Display reported rationale as requiring passage review. Paired references alone are not a semantic entailment model. |
| Missing filing comparisons display reconciliation; absent doxxing/impersonation fields default LOW; catalog matches imply identity verification; empty trend samples imply stable public attention. | renderer `renderAgentIntelligence`; Trending `generate_trending_intelligence` | Require relevant capture/measurement context, otherwise UNASSESSED. No-body/sampleless trends cannot establish reach, bot activity or virality. Catalog matching is explicitly not identity verification. Filing consistency requires reported comparable rows, then still requests period/unit/passage review. |
| Personal Watch renders a change dictionary literally. | `ReportBuilder.from_personal_watch` | Use existing bounded description/summary normalization; the saved baseline becomes readable text. A monitoring baseline is not proof of a safe subject. |
| Publishing failure status inside the builder mutated caller input. This task's full suite caught four preservation failures. | `report_builder.py`; API `_sync_investigation_status` | Keep builder input unchanged and publish root failure status at all four agent API attachment boundaries. Deep-copy conflict projections before normalizing. Existing report-preservation/golden tests pass without rebaselining frozen data. |

Slow diagnostic removal, bounded provider bulkheads, 120s patient research
defaults, SSRF/redirect/response-size protections and conservative company/ticker
resolution were already in this branch. They were preserved and regression-tested,
not newly invented here. The longer-window saved failures recorded zero synchronous
doctor calls and unused total time: diagnostics cannot explain those failures.
No company name was added as an unvalidated ticker.

## B. Regression coverage

New [production-failure controls](../../tests/unit/test_production_research_failure_repairs.py)
contain **24 parameterized cases** covering selector/resolver/replacement behavior,
failure categories, deadline latching/starvation, passage provenance, attribution,
readable changes, specialist planning, empty Trending output and all four shared
agent failure boundaries. Together with existing acquisition-policy tests:
**52 passed**.

Updated contradiction unit/integration expectations now require conservative
possible-disagreement semantics, not fabricated factual contradictions. Updated
frontend tests explicitly supply synthetic bodies/measurement basis for positive
specialized modules, and assert missing assessment does not become LOW, reconciled,
critical conflict or measured amplification. Existing preservation/golden checks
pass without changing their benchmark manifests.

The debugging, Python-testing and end-to-end-testing skills guided controlled
failure injection and separation of semantic assertions from HTTP/DOM checks.
No private reasoning transcript is included; this report records reproducible
engineering conclusions and actual results.

## C. Before/after: replay, not new acquisition

Raw October 18 captures were copied read-only to a new temporary input directory.
`run_terminal_agent_quality.py --capture-from` reprocessed those bytes through the
current API/SSE/report code with network blocked before application imports.
It restores only previously acquired content and IDs; discovery/escalation/search
are controlled. Its legacy required `--allow-live` CLI switch does **not** override
the saved-mode network block. AI credentials were blanked in the subprocess;
the existing server `.env` was not printed or edited.

| Saved production case | Original acquired records | Current saved-byte replay | Current report observations |
| --- | ---: | --- | --- |
| Scout / MSFT | 5 | 5 records; 5,272 words; 33.847 decimal KB; 22 discovery cards | Three retained legacy catalyst strings, not three independently adjudicated financial claims. Polarity headings no longer become contradictory evidence. |
| Trending / NVIDIA | 0 | 0 records; 0 words; 3 discovery cards | No invented body or measured virality. |
| BrandShield / Nike | 0 | 0 records; 0 words; 19 discovery cards | Explicit acquisition/evidence limitations; no default LOW impersonation or safety conclusion. |
| Personal Watch / Satya Nadella | 0 | 0 records; 0 words; 3 discovery cards | Doxxing/quote assessment UNASSESSED; readable baseline-change description. |

Words count whitespace tokens once per retained native content/snippet record;
KB is UTF-8 bytes/1,000, not JSON size, unique useful facts or independent coverage.
Microsoft's captured corporate articles are not financial filings or proof of
claim adjudication. Candidate counts can change under current gates/planning;
they are not fresh search results. The saved-read stub does not replay failed
network calls or exercise the new replacement mechanism: controlled unit tests,
not these saved zero-body runs, prove that mechanism's bounded behavior.

Then the exact newly generated SSE results were replayed through actual page
buttons, stream clients and native/shared renderers in Chromium at 320/390/1440px:
**12 states**, reports visible, expected findings/acquired/discovery card counts,
no missing finding text, horizontal overflow or uncaught page exception. Scout's
source inspection opened by keyboard at all three widths. Focused 390px report
captures for all four agents were visually inspected. Personal Watch rendered
text confirms UNASSESSED and readable changes, not a dictionary representation.

Readiness was a labeled browser harness stub. Other backend APIs were blocked;
fonts were deliberately blocked; resource/503 console errors remain in the raw
evidence. This is not a successful real doctor/readiness/source-read request,
screen-reader/contrast/axe audit, all-browser/device check or production-parity
test. It does not establish that the complete page is visually accepted.

## D. Commands and results

Commands ran from this worktree; output went to newly named system-temp files.
These are recorded outcomes, not an invented verbatim shell transcript.

| Command | Exit / actual result |
| --- | --- |
| `python -m pytest tests/ -q` | **0 — 1,498 passed, 54.41s** |
| `python -m pytest tests/unit tests/chaos tests/security -q` | **0 — 1,290 passed, 225.62s**; this run was substantially slower than earlier runs, not a latency benchmark |
| `python -m pytest tests/unit/test_production_research_failure_repairs.py tests/unit/test_acquisition_policy_integrity.py -q` | **0 — 52 passed, 0.74s** |
| `python -m flake8 backend tests scripts --count --select=E9,F63,F7,F82 --show-source --statistics` | **0 — zero fatal findings**, after final code |
| All `tests/frontend/test_*.js` via Node | **0 — all nine scripts passed**, after final frontend changes |
| `python scripts/validate_release_candidate_smoke.py --output <new-temp-json>` | **0 — OFFLINE_SMOKE_PASS**, after final code; disabled acquisition/explicit test doubles |
| `python scripts/validate_rollback_compatibility.py --output <new-temp-json>` | **0 — OFFLINE_PERSISTENCE_PASS**, after final code; temporary fresh-process reload/tamper/legacy reader controls |
| `python scripts/validation/verify_frozen_benchmarks.py` | **0 — frozen content hashes verified** |
| Terminal audit, `--capture-from <saved-capture-dir>` with four `--case` arguments | **0 — four saved-source cases**, unchanged application |
| Browser audit, `--replay-dir <terminal-output-dir>` with the same cases | **0 — 12 saved-SSE rendering states**, unchanged application |
| `git diff --check` | **0**; protected-path status empty during implementation; final protection checks recorded in handoff |

Failures were not hidden:

- Initial red controls included an incorrect test-only `ResearchBudget` constructor;
  corrected to its existing `deep_read_budget` interface. Not an application bug.
- Initial full run: **2 failed / 1,487 passed**. Existing assertions demanded the
  unsafe established-conflict behavior; updated to assert possible disagreement.
- Next full run: **4 failed / 1,492 passed**; fast run **4 failed / 1,284 passed**.
  These caught this implementation's input-mutation regression, fixed at the API
  boundary rather than weakening preservation requirements.
- A later full run: **1 failed / 1,496 passed** at the source-wait deadline race.
  Fixed with a timeout latch plus deterministic control, not a retry-only claim.
- Earlier frontend assertion expected an unreviewed conflict to be critical;
  corrected alongside explicit positive measurement fixtures.
- An `.env.example` audit launch failed validation before investigations because
  empty nonsecret settings were not valid runtime values. Existing config was
  loaded only into an isolated, secret-cleared/network-blocked subprocess.
- The first browser harness blocked readiness and never reached the POST. That
  run was stopped; readiness is now explicitly stubbed in replay. A capture-harness
  issue is not a provider or app success. Some earlier interrupted long-running
  verification attempts have incomplete logs and are excluded from acceptance.

Raw logs, full responses and temporary dossiers remain outside the repository in
the newly created `aegis-offline-production-repair-*` temp tree. The durable index
keeps only selected public measurements and screenshots, not full dossiers or
configuration. Raw temporary output may expire; use the commands and durable
record to reproduce rather than depending on a particular workstation path.

## E. Remaining risks and next verification

Later iterative implementation: [search/interpretation trial loop](SEARCH_RESOLUTION_TRIAL_LOOP_2026-10-19.md).
This separate user-authorized live task corrects further search/topic/advice
classification defects but still does not establish automatic research acceptance.

Later user-authorized live recheck: [four random-pool prompts](FOUR_RANDOM_PROMPT_RECHECK_2026-10-19.md).
This separate follow-up made real local provider investigations with AI off:
Sony partial pages, no quantum-computing/LEGO bodies, Lisa Su profile-only.
It does not alter this repair task's offline-only evidence or establish research
acceptance. Publisher resolution remains a demonstrated blocker.

1. **External publisher resolution/access remains unproven.** The fixed matching
   rule may still reject live candidates; challenge/timeout classifications cannot
   make unavailable sources accessible. No relaxed access policy, guessed URLs,
   fake content or unlimited retry was introduced.
2. **Semantic research acceptance remains incomplete.** These controls do not
   implement general proposition entailment, authenticate bylines, prove threats,
   validate identity or measure virality. Follow the independent reviewer packet.
3. **Not all 17 register entries are closed.** D01/D03/D04/D05/D06/D07/D08/D09/D15
   have focused fixes; D02 remains upstream-unverified and D16 only has added
   regression coverage. Duplicate release findings (D10), generic stopping label
   (D11), saturation-key mismatch (D12), adaptive lifecycle gaps (D13), mixed-scope
   counters (D14) and broader stale documentation (D17) are not declared resolved.
4. **Historical persistence/release:** isolated validation reports historical
   archive and deployed rollback **NOT_VERIFIED**. It does not recover or certify
   the previously reported 55 malformed historical dossiers. Originals remain
   protected. No new hosted CI run or current production SHA was attested.

Exact next production sequence, **only after separate authorization**:

1. Review this complete diff and protected-path hashes; create a fix-branch
   checkpoint and run hosted CI at its exact SHA. Do not merge on replay alone.
2. Verify that staging/production actually serves that SHA and its paired frontend;
   compare Cloudflare routing, SSE and backend version without running doctor in
   critical acquisition paths. Keep AI generation off for the smoke.
3. Authorize **one** bounded specialist investigation, not a new broad matrix.
   Save monotonic stage timings, provider-start/queue states, each resolution
   candidate/rejection, read attempt category/status and remaining budget. Confirm
   replacement attempts consume the original limits and no late mutation occurs.
4. Inspect any acquired body/IDs/attribution and objective-relevant passages before
   the frontend. If access fails, accept accurate failure reporting only—not
   research success. Replay that exact response through the deployed frontend.
5. Obtain independent passage/verdict review and an owner-controlled staging
   rollback; retain the historical archive limitation. Deploy/merge only under a
   later explicit decision. No such action is authorized by this offline report.
