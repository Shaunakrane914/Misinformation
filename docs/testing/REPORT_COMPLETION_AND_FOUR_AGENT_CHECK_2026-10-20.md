# Source-to-report completion and four-agent check — 2026-10-20

## Decision

**Partial implementation success; overall autonomous research acceptance remains FAIL.**
Adobe now automatically acquires a genuine publisher article and selects its
substantive announcement paragraph instead of an unrelated earnings-call heading.
This is a source assertion, not an independently verified fact or completed
financial claim adjudication. The other three sampled agents did not acquire
qualified article evidence. Downloaded publisher homepages do not satisfy that gate.

No commit, push, merge, deployment, credential/access-policy change or live AI call.
The existing large dirty worktree was preserved. Branch
`fix/p0-lenovo-acquisition-20261018`, HEAD
`39a514b68388450bbc5e6061aba97bda2077fc7f` plus uncommitted changes. The IDE's outer
checkout is not this isolated `.scratch/phase9-remediation-20261016` worktree.

[Continuation handoff](../handoffs/2026-10-20_REPORT_COMPLETION.md) ·
[Selected evidence and screenshots](evidence/2026-10-20_report_completion/README.md).
Earlier [Adobe check](ADOBE_POSTFIX_LIVE_CHECK_2026-10-20.md) remains historical
evidence; its passage/title defect is corrected here, not its wider acceptance gaps.

## Method and limits

1. Reused the previous genuine Adobe capture offline to reproduce passage/title
   loss before requesting new data. Generic synthetic controls cover the same
   boundaries; these are calibration regressions, not independent accuracy labels.
2. Ran exactly the four newly approved AI-disabled local investigations, once
   each: Scout/Adobe, BrandShield/Dyson, Trending/battery recycling, Personal
   Watch/Mary Barra. Research ceiling 120s, at most six deep-reader attempts each.
   Normal internal bounded searches/fallbacks remain; six is not a total HTTP cap.
3. Inspected complete native responses, query records, rejected candidates, read
   attempts and retained bodies. Then implemented further repairs offline.
4. With separate explicit approval, ran exactly one post-fix Dyson and one Mary
   Barra case under the same bounds. No audit-level retries or source sweeps.
5. Rebuilt shared reports from saved native responses with network blocked and
   rendered those reports in Chromium. Result-only SSE is a synthetic transport
   envelope, **not a replay of real progress or another live investigation**.

Both live batches report stable application fingerprints during their own runs.
Initial four-case fingerprint: `6689ab5ca4511eac0e3ed1c1d41a5b308dff187ee4de5ee2cf176e495b2a22e3`.
Application changed between batches and afterward for status/funnel reporting.
The final status/funnel corrections were tested offline, not followed by more
authorized live calls. All six approved live cases are consumed; further network
trials require a new small explicit scope. Live AI credentials were excluded,
mocks false, storage temporary, notifications/background ingestion disabled.

## Measured initial live funnel

| Case | Seconds | Initial queries / execution records | Observed provider attempts / responses | Normalized / accepted candidates | Reads attempted | Captures / article-classified bodies / qualified evidence | Findings |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Scout / Adobe | 44.99 | 13 / 17 | 50 / 49 | 27 / 26 | 6 | 5 / 2 / 1 | 1 |
| BrandShield / Dyson | 36.44 | 9 / 12 | 48 / 41 | 15 / 14 | 3 | 0 / 0 / 0 | 0 |
| Trending / battery recycling | 37.79 | 12 / 14 | 75 / 71 | 13 / 0 | 0 | 0 / 0 / 0 | 0 |
| Personal Watch / Mary Barra | 31.54 | 9 / 12 | 45 / 39 | 10 / 10 | 1 | 0 / 0 / 0 | 0 |

Provider counts include nested publisher-resolution calls. They are not unique
providers or complete HTTP accounting. Search URL samples include duplicates:
375, 307, 603 and 293 respectively, not relevant-source counts. Several query
records lack provider observations; legacy transport remains explicitly unknown.
Article-classified bodies are a structural heuristic, not quality acceptance:
Adobe's second such body contains just 21 retained words and produced no finding.
Rejected-candidate records can repeat across phases; Trending has 16 rejection
observations for 13 initial normalized candidates, not 16 distinct sources.

### Before / after selected observations

| Case | Before | Latest observation | Outcome |
| --- | --- | --- | --- |
| Adobe | Previous authorized run: 3 captures, 1,961 words, five attempts; main article present but selected a 43-character heading | New live run: 5 captures, 3,893 words / 26.530KB, six attempts; same 842-word / 5.957KB article selects complete main announcement paragraph | Article acquisition and source-to-finding continuity demonstrated for this one case |
| Dyson | Initial run: three unresolved wrappers, no bodies | Post-fix: 33.22s, five attempts, two publisher hubs, 2,307 words / 14.586KB; zero articles/qualified evidence/findings | Better bounded discovery path, **not** useful threat intelligence |
| battery recycling | Initial run: all candidates rejected, no reads; generic empty summary | Offline correction explains temporal/entity rejection and requests `when:2d` in future news/feed plans | Honest reporting verified; freshness query change **not live verified** |
| Mary Barra | Initial run: one unresolved wrapper; other leads deferred | Post-fix: 32.68s, two attempts, one publisher homepage, 638 words / 4.019KB; zero articles/qualified evidence/findings | No invented identity threat; substantive acquisition still unresolved |

KB = UTF-8 retained body bytes / 1,000; words = whitespace tokens. These include
background/noise and are not useful-word totals, unique corpora or improvement
percentages. Separate live runs have differing rankings; this is not a controlled
same-response experiment. Do not sum passes into a research corpus.

## First actual loss stage and root causes

### Adobe — acquired text was lost at passage selection and report context

The prior actual article contains the main announcement at offsets 194–701, but
the financial objective matcher omitted leadership events. A later earnings label
qualified instead. `Read more` stayed as the record title despite a real page
title. Readable CMS labels could compete with paragraphs. A visible date had no
explicit publication declaration and must not be guessed into publication time.

Owners and implemented repairs:

- [content_roles.py](../../backend/services/research/content_roles.py),
  `matches_objective` / `paragraph_role`: general leadership-event terms and
  conservative CMS scalar roles. Raw captures retained, not deleted.
- [passage_extractor.py](../../backend/services/research/passage_extractor.py),
  `extract_passages` / `has_usable_passage`: exclude observed headings and short
  noun-only labels while retaining numeric financial rows and complete paragraph
  qualifiers/negation. No new truth/entailment assertion.
- [body_context.py](../../backend/services/research/body_context.py),
  `reconcile_captured_context`, invoked by `DeepReader` and passage analysis:
  actual captured title wins; discovery title/date remain separately inspectable.
  Only explicit publisher-declared publication metadata populates publication.
- [page_extraction.py](../../backend/infrastructure/acquisition/adapters/web/page_extraction.py),
  `observe_text_structure`: exact heading/date-label spans. An unspecified date
  label, update date and future effective date remain distinct.
- [evidence_inspection.py](../../backend/schemas/evidence_inspection.py) and
  [renderer](../../frontend/unified-report-renderer.js): bounded exact date
  observations, escaped rendering and explicit unverified-date warning.
- [report_builder.py](../../backend/services/report_builder.py),
  `_captured_observation_brief`: default briefs may include one complete exact
  captured paragraph with hostname attribution and explicit non-verification.
  Requires a preserved source ID/body match and observation-only metadata; no
  sliced assertion, missing-reference summary or overwritten failure verdict.

The live article's retained-text SHA-256 is
`10416725f0a90cdea2e3e022522beb37e2b09a1bfc64c186d8f00d0f67b2a83e`.
Its canonical ID `ev_page_cc47517fb870` joins the report citation. The body stayed
842 words. Joining a citation does not establish entailment or independent truth.

### Dyson / Mary Barra — useful headlines fail publisher resolution

Search discovery did find relevant headlines. Initial body loss occurs at
`DeepReader._resolve_wrapper`: scoped Bing returned unrelated headlines; Yahoo
returned HTTP 500; legacy fallback returned another Google News wrapper. A
successful query record can therefore contain **zero readable publisher URLs**.
Wrapper cards were correctly not promoted into article text.

Implemented:

- [NativeExecutor](../../backend/services/agent_reach/native/executor.py) and
  [NativeNormalizer](../../backend/services/agent_reach/native/normalizer.py)
  retain the actual feed `<source>` URL/name. One existing resolver query is
  scoped to that observed publisher, not a guessed domain or extra query.
- [search_matching.py](../../backend/infrastructure/acquisition/adapters/web/search_matching.py)
  excludes the `site:` operator from lexical headline tokens; the 75% headline
  join remains unchanged. Scoped lookup still failed in these live observations.
- [DeepReadingStage.run](../../backend/application/research/reading.py): failed
  objective batches can release deferred alternatives for reassessment. Explicit
  catalog/auth/quality exclusions remain enforced. Initial objective priority is
  preserved, not bypassed to inflate content.
- [publisher_links.py](../../backend/services/research/publisher_links.py),
  `failed_feed_publisher_hubs`: at most two actually observed feed publisher hubs,
  within the original remaining attempt/deadline limits, leaving an article slot.
  No fabricated slug or provider proliferation. Credential-bearing/query-token
  URLs are excluded; transport still enforces DNS, SSRF, bytes and access limits.
  Only observed same-publisher links can proceed through entity qualification.

Post-fix hubs downloaded successfully, but none exposed an accepted relevant
article in the inspected bounded link set. Dyson's generic scam-service/product
text and unrelated law articles were not findings. Mary Barra's publisher hub
listed other current stories. **These captures do not solve article resolution.**

Final funnel code identifies `PUBLISHER_RESOLUTION` when unresolved articles are
masked by successful background hub downloads. The saved live funnel predates
that label correction and retains `BODY_OR_PASSAGE_QUALIFICATION` for the two
post-fix cases; do not silently rewrite that historical trace.

### Trending — candidate qualification, chiefly stale feed results

Eleven rejection observations are temporal and five are hard/entity gates. Several
on-topic feed headlines are months old. Topic matching itself is working for
these leads; this is not evidence that the old person/topic bug recurred. The
query planner asked for “latest”, but not a concrete provider freshness window.

[QueryPlanningStage.run](../../backend/application/research/acquisition.py) now
adds `when:2d` to bounded Trending news/RSS search queries, unless a time operator
or direct URL is already present. It is only a search hint: the unchanged temporal
guard still validates timestamps and rejects stale/future/undated sources.
[result_fit](../../backend/infrastructure/acquisition/adapters/web/search_observations.py)
does not count query operators as subject words. No extra queries or weakened
recency/entity gates. Fresh live effect remains unverified.

### Shared report status

`_complete_agent_report` distinguishes transport `COMPLETED` from investigation
`INSUFFICIENT_EVIDENCE` when the measured funnel has no qualified article evidence.
The original transport outcome remains in processing notes. All-read failure
still stays `ACQUISITION_FAILED`; neither status means the subject lacks available
information. Empty reports explain measured qualification reasons. Native status
sync already uses the shared report at all four API boundaries.

## Code/test verification

[test_substantive_report_completion.py](../../tests/unit/test_substantive_report_completion.py)
adds **23 offline controls** covering four domains, CMS/headings, raw span/ID/date
preservation, exact attribution, failed-read alternatives, observed hub → article,
bounded attempts, malformed hub URLs, freshness hints and background-only status.
The broader focused set has 86 passing controls. Mocked hub/article success is
explicitly not live discovery proof. Existing genuine saved search-response
regressions remain intact; no target-specific rule for live sample names.

The historical golden manifest is unchanged. One explicit exception in
`test_research_pipeline_golden.py` now requires the noun-only `primary_escalation`
fixture label to abstain instead of becoming a finding, while preserving its
historical raw hashes, IDs, ranking/query and lineage invariants. Frozen datasets
were not relabeled or regenerated to make a test pass.

| Final command / gate | Actual result |
| --- | --- |
| Focused four Python files | Exit 0; **86 passed / 0.96s** |
| `python -m pytest tests/ -q` | Exit 0; **1,555 passed / 59.55s** |
| `python -m pytest tests/unit tests/chaos tests/security -q` | Exit 0; **1,347 passed / 45.11s** |
| Fatal flake8, E9/F63/F7/F82 | Exit 0; zero fatal findings |
| All nine `tests/frontend/test_*.js` scripts | Exit 0 each |
| Frozen benchmark verifier | Exit 0; hashes verified |
| Protected-path diff against HEAD | Exit 0; dossiers/research/artifacts/scrapers/frozen files/shim unchanged |
| Release smoke with new temp output | Exit 0; `OFFLINE_SMOKE_PASS` |
| Rollback validator with new temp output | Exit 0; `OFFLINE_PERSISTENCE_PASS`; historical archive and deployed rollback **NOT_VERIFIED** |
| Six explicitly authorized live cases | Runners exit 0, no SSE errors; useful research acceptance only demonstrated for the Adobe observation |
| Final report-only reprojection / Chromium | Exit 0; four saved native cases / 12 viewport states |
| `git diff --check` | Exit 0; line-ending warnings are not silently normalized |

Intermediate focused runs failed while the new passage rules and golden exception
were being developed; later a synthetic hub fixture was below the existing
30-character read floor and a test used the wrong keyword-only factory signature.
Both test-harness issues were corrected without lowering the body threshold.
The first report-reprojection artifact omitted the query because serialized
queries live under `_meta`; the utility now reads that field and fails closed on
missing queries. Only corrected `report-only-v2` artifacts were browser-tested.

## Frontend validation

The E2E skill guided isolated native-response reprojection rather than new provider
requests. [rebuild_saved_agent_reports.py](../../scripts/audits/rebuild_saved_agent_reports.py)
blocks network before importing report code, writes only a new output directory,
preserves native evidence/IDs/findings/traces and records original hashes. It emits
result-only SSE, not invented progress. Original live JSON remains untouched.

Input mapping: Adobe and Trending from initial four-case batch; Dyson and Mary
Barra from separately approved post-fix batch. This is deliberately **not one
simultaneous final-code live matrix**. Full research reprocessing was also tried
offline, but can requalify/drop background hubs and mix preserved historical query
observations with blocked adaptive calls. Its timings/counts are not live gains;
the report-only path is used to isolate final presentation without that ambiguity.

At 320/390/1440px all shared reports rendered: source/discovery/finding counts
match 5/20/1, 2/14/0, 0/0/0 and 1/9/0. No missing finding text, horizontal overflow
or uncaught page exceptions. Keyboard source inspection opens in the nine states
with sources; Trending has no source inspection control. One focused screenshot
per agent was visually inspected: the complete Adobe paragraph and conservative
empty specialist/Trending explanations are visible. No lost frontend evidence was
observed in this bounded test.

The browser runner calls its transport mode `EXACT_SAVED_SSE_REPLAY`: here the
saved SSE was generated by **report-only reprojection**, not original progress.
All API calls other than that saved result are blocked; readiness is a stub,
external fonts deliberately blocked. Four blocked-font resource errors are
recorded separately from uncaught exceptions. No accessibility certification,
screen-reader/contrast/axe, cross-browser/mobile hardware, production parity,
hosted CI, independent accuracy or launch-readiness claim.

## Outstanding work / safe continuation

1. **P0, open:** relevant publisher article resolution for Dyson/Mary Barra and
   other subjects. Inspect native query/response transport, observed public
   redirects and accessible existing provider ranking under a newly approved
   small request budget. Do not “solve” by accepting a wrapper, guessing an
   article URL, lowering title/entity gates, bypassing challenges or adding APIs
   without access/owner decisions. Existing Bing/Yahoo behavior is observed;
   exact upstream reason is not established by local call timing alone.
2. **P1, unverified:** fresh Trending query effect. Replay cannot establish that
   a provider has fresh coverage. A legitimate zero-fresh-evidence abstention is
   preferable to describing old stories as current virality.
3. **P1, open:** independent held-out accuracy and useful specialist positive
   cases; financial adjudication, media authentication and actual time-series
   virality are not established by one good article observation.
4. **Release blocked:** no hosted CI/deployed integration or historical dossier
   recovery verification. The known earlier 55 malformed dossiers were not
   touched; their absence from this isolated validator's archive is not recovery.

All full native captures, isolated dossiers, gate logs, and screenshots remain
under the new system-temp tree `aegis-report-completion-12f53696-024e-4109-ae57-9515d0bada50`.
Temp data can expire; selected sanitized hashes, measurements and images are
durable below. This is an engineering command/result account, not a raw transcript
or private reasoning trace. Preserve the dirty implementation and original data.
