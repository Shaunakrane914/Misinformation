# Autonomous discovery repair — 2026-10-20

> Subsequent separately authorized [Adobe live check](ADOBE_POSTFIX_LIVE_CHECK_2026-10-20.md)
> demonstrates one query-discovered 842-word article acquisition on this code.
> Downstream heading selection still prevents research-quality acceptance.
> The two earlier live observations and before/after replay evidence below
> remain unchanged; they predate that fresh post-fix check.

## Decision

**Targeted repairs implemented; autonomous live article discovery NOT ACCEPTED.**
The two authorized fresh cases did not demonstrate a relevant publisher article
surviving discovery, native body acquisition and passage qualification. Passing
HTTP responses, large text counts and offline tests are not research acceptance.

This continues [October 19's checkpoint](SEARCH_RESOLUTION_TRIAL_LOOP_2026-10-19.md).
The session crossed midnight locally. Branch `fix/p0-lenovo-acquisition-20261018`,
HEAD `39a514b68388450bbc5e6061aba97bda2077fc7f`, plus preserved uncommitted work.
The active implementation is in `.scratch/phase9-remediation-20261016`, not the
outer IDE checkout. No commit, push, merge, deployment, credential/access change,
new provider or model/quota call. **Zero live AI generation requests.**

[Handoff](../handoffs/2026-10-20_AUTONOMOUS_DISCOVERY_REPAIR.md) ·
[Durable measurements and screenshots](evidence/2026-10-20_autonomous_discovery/README.md).

## Authority and method

- Inspected the dirty worktree, handoff, planning, search/normalization, candidate
  gates, selection, native reading, passage roles and prior rejected candidates.
- Retained the existing headline-overlap fallback, inline title spacing,
  topic/person distinction and advice-versus-incident repairs. Their regression
  controls still pass; they were not removed or represented as new successes.
- Offline first: synthetic boundary controls and normalized genuine saved
  search observations. Then exactly **two** approved local normal-query SSE
  investigations: Scout/Adobe and BrandShield/Dyson, once each, AI credentials
  blanked, mocks off, 120-second research ceiling, six deep-reader attempts per
  case, no audit-level POST retry. Normal provider fallback remains bounded.
- New isolated SQLite/dossier directories, lifespan/background ingestion off,
  remote writes/notifications disabled. Existing local provider gates retained.
- Post-capture fixes were tested with saved bytes and blocked network, not a
  second live investigation. Browser checks replay that resulting SSE only.

## Per-case funnel: fresh observations and saved-byte corrections

Counts below are **not unique sources**. Provider rows include nested publisher
resolution. Response counts exclude unknown legacy transport. Candidate samples
can repeat URLs across queries/providers. Initial generated queries differ from
main lifecycle records, which include adaptive/escalation work.

| Measurement | Adobe — fresh live | Dyson — fresh live |
| --- | ---: | ---: |
| End-to-end local seconds | 51.94 | 41.12 |
| Initial generated queries | 13 | 9 |
| Main lifecycle records | 17 | 12 |
| Provider invocations observed | 48 | 41 |
| Responses observed | 42 | 35 |
| Candidate URL decisions sampled | 325 | 257 |
| Search discards | 275 | 211 |
| Normalized candidates, including later leads | 25 | 14 |
| Accepted candidates | 23 | 13 |
| Selected acquisition attempts | 5 | 3 |
| Native retained records | 4 | 0 |
| Retained text words / decimal KB | 3,012 / 20.311 | 0 / 0 |
| Genuinely demonstrated article bodies | 0 | 0 |
| Native outcome | COMPLETED acquisition, not research acceptance | ACQUISITION_FAILED |

Adobe's original telemetry incorrectly counted two article-shaped captures and
one qualified finding. Manual inspection showed a headline index and SVG-label
text, not two articles. Those original measurements remain intact as defect
evidence; the corrected role checks do not retroactively make the live run pass.

| Same captured bytes, before → after current processing | Adobe | Dyson |
| --- | --- | --- |
| Retained record count / content hashes | 4 → 4; unchanged | 0 → 0 |
| Classified article bodies | 2 → 0 | 0 → 0 |
| Qualified evidence | 1 false-positive index → 0 | 0 → 0 |
| Displayed findings | 1 headline dump → 0 | 0 → 0 |
| Honest interpretation | Captures exist; no article-qualified finding | Unable to acquire evidence, not proof of no information |

Saved reprocessing expands inspectable observed links and preserves historical
failed attempts. Its query/provider counters mix saved observations and
network-blocked invocations; **they must not be advertised as new discovery
throughput or a before/after retrieval recall improvement**. Source-text hashes
match across the fresh capture and final reprocessing. The old icon record is
preserved for diagnosis; current link selection rejects a new icon read.

### First demonstrated losses, not guesses from empty reports

**Adobe:** discovery returned corporate home/news pages and a MarketBeat news
collection. Reading acquired those; Reuters returned HTTP 401. A captured
newsroom exposed an actual CEO-announcement URL, but the new link selector's
narrow financial keyword check discarded that lead as `OFF_OBJECTIVE` while
accepting an investor-relations SVG. This is a measured **link-selection defect**,
not proof the unrequested announcement body would have been accessible or
financially sufficient. Separately, passage qualification promoted the collection
of headlines into a finding because semantic `<article>` markup was mistaken for
an actual article. About 68.4 research seconds remained after processing: the
global 120-second deadline did not cause the result.

**Dyson:** news discovery found titles about a free-vacuum scam, phishing and a
trademark lawsuit. The three selected leads were encrypted Google News wrappers.
Their bodies were never acquired. Two nested headline searches started, returned
unrelated Bing results and Yahoo HTTP 500s, then timed out. One nested search
waited five seconds without starting (`QUEUE_TIMEOUT`). The first complete loss
of selected article leads is **publisher URL resolution / nested scheduling**,
not body extraction or a lack of possible reports. About 79.5 research seconds
remained. This also demonstrates that more total waiting alone is not the cure.

Prior captures remain different observations: LEGO lost publisher resolution;
Lisa Su retained only profile metadata; quantum computing candidates failed
freshness/topic qualification; Sony retained shallow pages. Missing historic
provider measurements stay unknown. No post-fix live rerun of those cases occurred.

## Changes and exact ownership

| File / function | Repair and limits |
| --- | --- |
| [Search observations](../../backend/infrastructure/acquisition/adapters/web/search_observations.py), `capture_search`, `result_fit`, `empty_search_failure` | Request-local provider observations; safe locators; subject/title/query coverage decisions. Uses the existing conservative topic matcher. A weak financial issuer hub remains a discovery lead, never article evidence. All measured transport failures cannot silently become SUCCESS/empty. |
| [Router](../../backend/infrastructure/acquisition/routing/router.py), `_execute_web_search`, `_execute_yahoo_search` | Evaluate/rank observed candidates before truncation, trigger existing fallback on irrelevant/weak returns, export decisions and HTTP/error categories. No new provider or unlimited retries. |
| [Standard handlers](../../backend/infrastructure/acquisition/routing/standard_handlers.py), `_execute_feed`, `_execute_web`, `_qualify_legacy_search` | Feed observations and irrelevant-result fallback; legacy news/web fallbacks must pass the same gate instead of restoring rejected hits. Legacy network internals remain explicitly uninstrumented. |
| [Service](../../backend/infrastructure/acquisition/service.py), `retrieve_many` / `_run_single_query`; [query record](../../backend/services/agent_reach/channels.py), `QueryExecutionRecord` | Detach request-local search observations into query records on success/failure; preserve current bounded pools, deadlines and cached capability routing. |
| [Typed search adapter](../../backend/services/agent_reach/native/adapters/search.py), `discover_candidates`; router `execute_retrieval_request` | Preserve query class/ID/text and fragment metadata. This is a separate compatibility path, not claimed as the principal normal-pipeline failure. |
| [Page extraction](../../backend/infrastructure/acquisition/adapters/web/page_extraction.py), `extract_observed_page_details` | Separate small navigation-discovery sample from extracted prose. Never append navigation to a purported article body. |
| [Publisher links](../../backend/services/research/publisher_links.py), `observed_publisher_articles`; [reading](../../backend/application/research/reading.py), `DeepReadingStage.run` | Up to two rounds of observed same-host/subdomain hub links, within original attempt/time caps; record rejection reasons. Financial hub reads reserve existing slots. Reject assets; permit corporate announcements as leads. No guessed URLs or cross-publisher expansion. |
| [Deep reader](../../backend/services/research/deep_reader.py), `_resolve_wrapper`, `deep_read`, `_http_status` | Resolver chain receives at most two-thirds of remaining read time, capped at ten seconds; reserve body time, keep each HTTP bound. All-wrapper batches use two workers to match the shared web bulkhead. Preserve structured transport HTTP status. This scheduling repair is offline-tested, **not freshly live-verified**. |
| [Content roles](../../backend/services/research/content_roles.py), `document_role` | Collection endpoints with several observed links are NEWS_INDEX, not substantive articles; assets are ASSET_METADATA. A normal extensionless `/news/story` remains eligible. Raw captures unchanged. |
| [Funnel](../../backend/services/research/discovery_funnel.py), `build_discovery_funnel`; [assembly](../../backend/application/research/assembly.py), `CorpusAssemblyStage.run`; [report](../../backend/services/report_builder.py), `_complete_agent_report` | Export planning/provider/candidate/read/body/passage/finding counts, reasons and uncertainty at the report boundary. First empty boundary is a diagnostic cue, not causal proof or calibrated research accuracy. |
| [Terminal runner](../../scripts/audits/run_terminal_agent_quality.py), `main` / `saved_reads` | Explicit audit bounds; rich corpus metadata wins over redacted display metadata in replay; historical read failures retained once and labeled SAVED_CAPTURE. |
| [Summarizer](../../scripts/audits/summarize_discovery_funnel.py), `summarize` | Network-free saved-output measurement with native/source hashes; exclusive new output file, no overwrite. |

Existing claim-aware `QueryPlanningStage` / `SourcePlanningEngine` already provide
bounded financial, brand, individual and topic plans and preserve explicit claims.
They were inspected and retained rather than replaced. The demonstrated remaining
losses do not justify another planner rewrite or a provider sweep.

## Actual verification

Python 3.13.5; Node v22.17.1. Twenty-seven new controls in
[test_autonomous_discovery_funnel.py](../../tests/unit/test_autonomous_discovery_funnel.py)
cover empty/irrelevant/mixed search, blocked reading, observed-link continuation,
expiry, scope isolation, varied subjects, all four agent callers, topic inflection,
transport status, collection/assets and the resolver's parent deadline. Synthetic
HTTP controls exercise the real native HTML reader and passage extractor, not a
fabricated production article. [Saved title/URL pairs](../../tests/unit/fixtures/search_drift_20261019.json)
come from a genuine captured Bing response; its HTML test envelope is reconstructed
and explicitly labeled normalized replay, not a raw transport capture.

| Command/check | Final actual result |
| --- | --- |
| `python -m pytest tests/ -q` | Exit 0; **1,532 passed / 50.98s** |
| `python -m pytest tests/unit tests/chaos tests/security -q` | Exit 0; **1,324 passed / 36.47s** |
| Fatal flake8 command in AGENTS | Exit 0; zero fatal errors |
| All nine `tests/frontend/test_*.js` scripts with Node | Exit 0 each |
| `validate_release_candidate_smoke.py --output <new-file>` | Exit 0; OFFLINE_SMOKE_PASS, final recheck recorded in session logs |
| `validate_rollback_compatibility.py --output <new-file>` | Exit 0; offline persistence/readers pass; historical archive and deployed rollback NOT_VERIFIED |
| Frozen benchmark verifier / protected Git diff | Exit 0; frozen hashes match, protected paths unchanged |
| Two authorized terminal investigations | Exit 0 transport harness; research acceptance FAIL |
| Saved-byte reprocessing / read-only summarizer | Exit 0; source-text hashes unchanged; no fresh provider requests |
| Chromium saved-SSE replay | Exit 0; six states, matching record/finding/discovery counts, no horizontal overflow or uncaught page exceptions |
| Hosted CI / production parity | NOT RUN / NOT VERIFIED; no push or deployment authorized |

Historical evidence/lineage golden manifests were **not regenerated**. Their
comparison excludes the additive discovery diagnostics, independently tested by
the new controls; existing candidate/corpus/dossier invariants remain checked.
One legacy contract fixture used a URL-less fallback; it now uses a valid matching
public test URL, preserving fallback behavior without allowing invalid candidates.

Disclosed iteration failures: early golden differences were additive telemetry,
not candidate/dossier changes; test-only frozen-response mutation, wrong passage
keyword and incomplete offline DNS stubs were corrected. A blocked-read control
exposed the real transport-status loss. Initial saved replay incorrectly let
redacted display metadata overwrite captured page links and failed to preserve
prior read failures; the runner was corrected and outputs regenerated in new
directories. A narrowly misplaced asset-role edit was caught and corrected by
its focused test. Earlier totals/logs are intermediate, not final acceptance.

Browser replay uses E2E testing-skill isolation: actual buttons/renderers, saved
SSE, no provider requests or production mutations. Six states at 320/390/1440px;
one captured-source inspector opens by keyboard at each Scout width. Selected
desktop Scout and mobile BrandShield reports were visually inspected. External
fonts were deliberately blocked. Console resource errors include blocked fonts
and harness API/static failures; these are disclosed, not an all-console-clean
claim. No screen-reader, complete WCAG, cross-browser or real-device certification.

## Remaining release blockers and next bounded step

1. **P0 remains open:** neither held-out live case acquired a verified relevant
   publisher article body. Discovery correction is partial, not completed v1.
2. Need a new separately authorized, small live case set to verify post-capture
   resolver scheduling and actual article acquisition. The two-case authorization
   is consumed; no additional live provider investigation was run.
3. Yahoo's 500s and Bing's unrelated headline results remain external observed
   failures. No access bypass, unapproved paid provider, fabricated publisher URL,
   lower relevance/75% title threshold or result-card-as-body shortcut was used.
4. Same-host link restrictions intentionally do not establish corporate ownership
   of sibling domains. Dynamic newsroom fragments and off-host references may
   remain inaccessible. Selected bodies still require case-specific support review.
5. Provider observations are bounded, incomplete HTTP accounting; absent social/
   legacy measurements and unfinished worker observations remain unknown.
6. Independent accuracy, historical dossier recovery, hosted CI, deployed-stack
   checks and production-launch readiness remain unverified. The isolated worktree
   does not prove recovery of the previously reported malformed archive.

Do not merge or deploy this as an accepted discovery fix. Continue from captured
candidate decisions and source bodies, not another unrestricted website sweep.
