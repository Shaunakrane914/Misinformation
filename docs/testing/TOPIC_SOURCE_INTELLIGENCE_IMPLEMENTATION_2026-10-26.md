# Topic-aware source intelligence — 2026-10-26

Latest continuation: [usable-source repair and individual website checks](USABLE_SOURCE_REPAIR_AND_SITE_CHECKS_2026-10-26.md). It records the 60-family inventory, four direct probes, scoped-search/directory/pacing repairs and the remaining DNS/connection blocker. The earlier measurements below are preserved.

## Decision

**Topic routing, explicit source reviews and source-to-renderer controls are implemented and tested. New-family live acquisition acceptance is NOT MET. No deployment.** The two authorized local pilots acquired zero bodies. The later user-requested AI enablement succeeded in a separate single suggestion call; it does not turn either acquisition pilot into a success.

Worktree: `.scratch/phase9-remediation-20261016`, branch `release/specialist-task-20261024`, base `7ad13a5`, with preserved uncommitted work. The original IDE root is another checkout. No commit, push, merge or deployment was performed. Existing source files already had uncommitted acquisition repairs; pre-task copies and Git status were retained in a new system-temp tree before editing.

Scope: the attached topic-aware implementation brief, the user's instruction to retain explicit gates because no publisher agreements are configured, the two approved 180-second native pilots, and the subsequent instruction to enable AI suggestions. The [58-family research catalog](../architecture/source_candidates_2026-10-26.json) remains unchanged as research, not runtime configuration. The [operational runbook](../operations/TOPIC_SOURCE_ROUTING.md) explains configuration and review scopes.

## Implementation and first-loss corrections

| File / function | Implemented behavior |
| --- | --- |
| [topic_context.infer_context](../../backend/services/research/topic_context.py) | Agent task, subject, tentative topics/type, language, geography, time window and explicit ambiguity. Whole-token/phrase cues; no hardcoded celebrity identity or model requirement. Subject-linked observed titles can supply weak routing context. Script alone is not language identification. |
| [SourceRegistry](../../backend/services/research/source_registry.py), [operational definitions](../../backend/services/research/source_registry_data.json) | 59 declared families: the researched 58 plus Global Voices. Topics/tasks/hosts, native capabilities, authentication, review scopes, freshness/archive limitations and unknown costs/rate limits are explicit. Definitions are not 59 working integrations. Planning uses cached observations and performs no synchronous doctor/network probes. |
| [Public reviews](../../backend/services/research/source_public_licence_reviews.json) | Versioned, expiring public-policy reviews for eligible Global Voices and GOV.UK text only. New commercial families stay gated. External server review files are bounded and fail closed; browser hints cannot grant rights. Discovery, body and excerpt approval remain separate. |
| [SourcePlanningEngine.plan / refine_topics](../../backend/services/agent_reach/source_planner.py) | At most two topic-family actions inside existing action caps. Unknown names begin with neutral discovery; observed subject-linked titles may replace an unsubmitted same-channel action once. Explicit site/direct-URL requests retain their constraints. |
| [QueryPlanningStage](../../backend/application/research/acquisition.py), [harvest pipeline](../../backend/application/research/harvest_pipeline.py) | Research context and permitted channels reach the planner. Validated core actions now reach Harvesting for Scout/Trending as well as specialist agents; previously some actions were generated but discarded at that boundary. |
| [HarvestingEngine](../../backend/services/research/harvesting.py), [PipelinedAcquisition](../../backend/services/research/pipelined_acquisition.py) | Pending-only topic refinement, bounded provenance, and configuration-only body-permission admission before spending reader slots. Denied leads stay inspectable with explicit unread reasons. They cannot count as useful supply or exhaust the reader budget. Final access checks still run. |
| [source_diversity](../../backend/services/research/source_diversity.py), [expanded catalog](../../backend/infrastructure/acquisition/adapters/expanded_catalog.py) | Entertainment/sports/politics requests avoid generic technical fallback. Unknown Trending/Personal subjects use neutral reporting; role-specific requests avoid unrelated Substack fan-out. Other native routes remain registered. |
| [DeepReader](../../backend/services/research/deep_reader.py), [safe HTTP](../../backend/infrastructure/acquisition/network/http.py) | Check rights before cache/read and on redirects. New reviewed families use bounded lazy robots checks, cached for 15 minutes, with 5-second/128KB/one-attempt limits. Unknown/denied robots and unenforced crawl delays remain blocked. SSRF/provider restrictions are preserved. |
| [page extraction](../../backend/infrastructure/acquisition/adapters/web/page_extraction.py), [raw pool](../../backend/services/research/raw_pool.py) | Preserve observed HTML language, licence declarations, contrary rights notices and routing lineage without rewriting source text. New controlled captures are explicitly marked. |
| [PassageExtractor](../../backend/services/research/passage_extractor.py), [inspection](../../backend/schemas/evidence_inspection.py), [workbench](../../backend/services/research/evidence_workbench.py), [renderer](../../frontend/unified-report-renderer.js) | Separate excerpt rights from body access. Global Voices passages require captured author/licence observations and no contrary notice. Credit/licence/language are rendered with escaping and validated links. Exact source text, IDs and offsets remain intact. No generated translation or fabricated facts. |

Public-policy basis: [Global Voices attribution policy](https://globalvoices.org/about/global-voices-attribution-policy/), [GOV.UK reuse guidance](https://www.gov.uk/help/reuse-govuk-content). These are conditional text reviews, not private publisher agreements, authenticated runtime access, third-party media rights or proof of article availability. Existing native policies remain separate from this registry.

## Offline before/after evaluation

The new [comparison script](../../scripts/audits/compare_topic_source_plans.py) loads the actual saved pre-task planner, blocks network before application imports, and compares the two planners under the same current controller and source-review policy. Exact original claims for saved cases were reconstructed from their recorded command line, not supplied article URLs. Source bytes and hashes remained unchanged.

Eight synthetic routing cases cover Bollywood, regional cinema, cricket, politics, semiconductors, company finance, fake celebrity advertising and public-figure quotation verification. Three negative controls cover an ambiguous name, a name containing an incident-like word, and absent topic evidence. **11/11 labels match.** These fictional calibration inputs are not independent research-accuracy tests or genuine body acquisitions for eight topics.

Four genuine October 25 source worlds were replayed once per planner, giving eight offline runs. Final closeout results:

| Saved source world | Previous planner qualified records / selected words | Topic planner qualified records / selected words |
| --- | ---: | ---: |
| Battery recycling | 1 / 100 | 1 / 100 |
| Semiconductor manufacturing | 0 / 0 | 0 / 0 |
| Mary Barra public statement | 0 / 0 | 0 / 0 |
| Tim Cook public statement | 0 / 0 | 0 / 0 |

**No useful-yield improvement is demonstrated by this saved replay.** Earlier pre-closeout replay retained one 50-word Tim record under both planners; the final time-compressed replay retained none. Missing read/search observations, scheduling and changed shared policy limit comparison with original native reports. These are simulator observations, not deterministic measurements of live recall or speed. Some replay query counters also exceed generated query counts because legacy observations/reservations differ; they are not an accepted network-cost metric. Actual zero network/model calls are enforced separately. Original native historical word yields are not replaced by these replay values.

The synthetic provider regression demonstrates unknown-name → observed title → permitted scoped query → native body capture in both acquisition controllers. A second regression supplies six denied leads and one permitted source with a single reader slot: both controllers preserve the slot for the permitted body and retain six policy-denial reasons. Neither positive control is a real article capture.

## Authorized live pilot — failed acquisition, preserved diagnostics

Ran exactly the two approved cases, AI disabled, once each: 180 seconds, 16 reader selections and 80 native HTTP admissions maximum per case. Body access was restricted in the child process to the reviewed `global_voices,govuk` families. Temporary SQLite/dossiers, no background ingestion/notifications, no paid readers and no production writes. Application fingerprint remained stable during the batch. The later preflight-allocation correction is **not** part of those captured live bytes.

| Stage / result | Trending: Bollywood cinema | Personal Watch: Jasprit Bumrah public statement |
| --- | ---: | ---: |
| Wall seconds | 98.99 | 13.02 |
| Generated queries | 18 | 16 |
| Query records | 9 TIMEOUT, 4 SUCCESS, 1 FAILED, 4 NOT_SUBMITTED | 4 SUCCESS, 2 UNRECORDED, 10 NOT_SUBMITTED |
| Unique discovered URLs | 4 | 20 |
| Relevant read leads before source-policy check | 4 | 17 |
| Reader selections | 4 | 16 |
| Actual read-service starts | 0 | 0 |
| Native HTTP admissions, including discovery | 39 | 6 |
| Body captures / qualified sources / published words | 0 / 0 / 0 | 0 / 0 / 0 |
| Final investigation state | ACQUISITION_FAILED | ACQUISITION_FAILED |

HTTP 200/result events indicate completed transport only. Corpus funnel `deep_reads_count` counts acquired/deep-read source records, not every reader selection; it is zero here while harvesting selections are 4 and 16. Query-level trace is the authority for unsubmitted/unknown work. The two Personal queries marked UNRECORDED were dispatched without an inspectable returned execution record; neither is counted as a successful search.

**Bollywood first loss:** approved-family discovery. The scoped Global Voices search timed out; the available direct leads belonged to disallowed families. Two such direct reads were rejected before network and two opaque publisher resolutions failed. No approved publisher body was attempted, so this run proves neither that Global Voices lacks relevant articles nor that its body reader/robots/licence extraction works live.

**Personal first loss:** scoped provider results and selection. The subject's observed titles correctly refined routing to cricket, and the Global Voices scoped query actually executed. The provider returned other hosts despite the scoped query. Fifteen policy-denied selections and one reader-not-selected outcome exhausted the read allowance; actual body reads never began. The subsequent configuration-only preflight prevents that measured scheduling failure offline. It does not improve the provider's ranking or prove a relevant permitted article exists. No live post-fix rerun was made.

The Personal finding is an explicit UNVERIFIED/INSUFFICIENT_EVIDENCE assessment with no support IDs, not a positive identity-threat claim. Empty reports remain empty. Safety advice, metadata, profiles and search cards are not promoted into article evidence.

## AI enablement — separately authorized afterward

The user's later instruction superseded the AI-disabled implementation scope for this limited enablement check. Local `.env` switches for runtime advice, planner suggestions, search advice and passage advice are now true. The existing configured model is unchanged: `gemini-3.5-flash-lite`. Other configuration values and credentials were preserved; no secret was printed or copied to this worktree. Existing backend processes require restart to reload changed flags. No hosted service was changed.

One exact-model capability GET returned 200, followed by **one** permitted generation request: HTTP 200, 931.23ms, 22 input + 18 output = **40 provider-reported tokens**. The test capped output at 48 tokens; the normal hard ceiling remains 160. JSON structure was checked, but no returned query was used for source acquisition. No retries, model/key fallback, new quota bucket, source investigation or paid reader call. The shared daily ledger recorded one reservation. All suggestion paths retain one call/investigation and three/UTC-day limits, privacy checks and cooldown. Automated suites below made no live AI calls. See [sanitized check](evidence/2026-10-26_topic_source_intelligence/ai-enablement-check.json).

## Verification actually run

| Command / scope | Exit and result |
| --- | --- |
| `python -m pytest tests/unit/test_topic_source_registry.py tests/unit/test_pipelined_acquisition.py -q` | 0; 69 passed / 14.84s, including 41 registry/routing controls |
| `python -m pytest tests/ -q` | 0; **2,616 passed / 127.24s** |
| `python -m pytest tests/unit tests/chaos tests/security -q` | 0; **2,408 passed / 107.59s** |
| `python -m flake8 backend tests scripts --count --select=E9,F63,F7,F82 --show-source --statistics` | 0; zero fatal findings |
| Each of ten `tests/frontend/test_*.js` Node scripts | 0 each |
| `python scripts/validate_release_candidate_smoke.py --output <new-temp-json>` | 0; OFFLINE_SMOKE_PASS |
| `python scripts/validate_rollback_compatibility.py --output <new-temp-json>` | 0; OFFLINE_PERSISTENCE_PASS; historical archive/deployed previous-version rollback NOT_VERIFIED |
| `python scripts/validation/verify_frozen_benchmarks.py` | 0; protected hashes match |
| `compare_topic_source_plans.py` with saved previous planner, exact recorded claims and genuine saved batch | 0; 11 calibration matches, eight offline replays, no network/model calls |
| `audit_evidence_workbench.py` on both native pilot reports | 0; six states at 320/390/1440px, empty passages honestly rendered |
| Same browser script on labeled synthetic credit/language control | 0; three states, one synthetic paragraph, no claimed live evidence |
| `git diff --check` / protected-tree diff | 0; no whitespace errors or changes to protected trees |

Browser replay used real Chromium and the shared renderer loaded by actual agent pages. All external traffic was blocked; it did not resubmit investigations. Nine states had matching passage counts, keyboard pagination/filter behavior, no detected horizontal overflow and no uncaught page exceptions. The synthetic credit/language mobile capture and the native Trending empty-state capture were visually inspected. This is not fresh form-to-provider acceptance, source/licence authenticity, screen-reader/contrast certification, or deployed behavior.

Intermediate failures were retained, not rewritten as passes: initial full run 15 failed/2,593 passed; old unknown-topic fallback assertions, three historical semantic fixtures and ten diagnostic-only golden differences were corrected. New rights checks apply to new controlled reads; they do not retroactively claim to license historical captured bytes. Golden canonicalization excludes the new plan diagnostics only inside a plan-shaped object; actual query/evidence changes remain hashed and frozen manifests were untouched. An initial routing matrix exposed the `Recall Labs` name collision and was corrected. One focused invocation referenced a nonexistent test file and collected zero tests before correction. An early target-only replay completed its JSON but had a shell-wrapper exit error; the final exact-claim replay above exited zero. Subsequent broad suites passed on stabilized code.

## Outstanding acceptance

1. No newly reviewed family produced a genuine article body in this pilot. There is no honest new article/date/useful-word example to present.
2. Eight-topic routing calibration is implemented; eight-topic genuine acquisition and independently reviewed exact-claim accuracy are not established. Broad coverage remains constrained by missing commercial permissions, provider ranking/transport and actual archive availability.
3. The pre-access scheduling fix has synthetic offline proof only. More AI suggestions or larger limits do not substitute for a relevant permitted source capture.
4. Registry rate/cost fields deliberately retain unknown values until provider-specific observations exist. Robots/access/licence/freshness checks must succeed independently.
5. Source-to-browser checks do not verify production parity, hosted CI, historical malformed dossier recovery or deployed rollback. No deployment is authorized by this report.

Selected portable evidence is indexed [here](evidence/2026-10-26_topic_source_intelligence/README.md). Original native responses, logs, pre-task copies, isolated dossiers and full screenshots remain in system-temp basename `aegis-topic-routing-x7zv_fpn`; that storage may expire. Protected historical records and frozen benchmarks were preserved.
