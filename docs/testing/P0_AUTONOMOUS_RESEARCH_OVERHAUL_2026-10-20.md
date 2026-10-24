# P0 autonomous research overhaul — 2026-10-20

Latest integrity continuation: [reporting origins and reviewer readiness](REPORTING_ORIGIN_AND_REVIEW_READINESS_2026-10-21.md).
Repaired false same-wire corroboration and final-report source counts offline;
independent research accuracy and release gates remain unverified. Historical
acquisition observations below remain intact.

Latest continuation: [Trending fresh-source completion](TRENDING_FRESH_ACQUISITION_COMPLETION_2026-10-20.md).
Two normal topic queries acquired fresh articles; corrected source-to-browser
processing is verified offline. The sampled Trending blocker is repaired, while
broader accuracy, measured virality and release gates remain separate.

Earlier continuation: [four-agent source-to-browser completion](FOUR_AGENT_COMPLETION_2026-10-20.md).
It records additional real acquisitions, corrections, browser proof and the still-open
Trending freshness gate. This earlier failure checkpoint remains preserved below.

Historical checkpoint: the later [expanded harvesting report](EXPANDED_HARVESTING_TWO_LAYER_REPORT_2026-10-20.md)
records new real article acquisition and its remaining acceptance limits. The
failed observations below are preserved unchanged, not the newest runtime state.

## Acceptance decision

**Implemented targeted acquisition/qualification and AI-advisory repairs; live
research acceptance remains NOT MET. Do not deploy.** Passing offline regressions
and successful Gemini suggestions did not produce qualified articles in the new
five-case batch. One case suffered a major host-time interruption and is not a
normal latency or before/after-quality measurement. No push, merge or deployment.

Scope: user's attached P0 overhaul instruction, following the
[five-prompt failure baseline](FIVE_PROMPT_LIVE_CHECK_2026-10-20.md).
Worktree `.scratch/phase9-remediation-20261016`, branch
`fix/p0-lenovo-acquisition-20261018`, base HEAD
`39a514b68388450bbc5e6061aba97bda2077fc7f` plus preserved dirty work.
Existing shims, scrapers, research/artifacts, historical dossiers and frozen
datasets were not removed or rewritten. No credentials/access flags changed.

[Measured live proof](evidence/2026-10-20_p0_overhaul/live-funnel.json) ·
[Original live summary and AI accounting](evidence/2026-10-20_p0_overhaul/live-summary.json).

## Implemented acquisition flow

The existing pipeline remains: deterministic source planning and native discovery
→ subject/task ranking → bounded reading → exact-body/temporal qualification →
source-only findings/shared report. No new agent, search provider or architecture
replacement. Focused changes separate three formerly conflated decisions:

1. A lead can be worth **reading** without already qualifying as evidence.
2. Downloading a hub/feed/search index is **discovery**, not article acquisition.
3. A relevant-looking captured paragraph is **not** independent truth or a
   current event merely because it contains financial/threat keywords.

Optional Gemini advice runs after weak deterministic discovery, not as synthesis.
One suggested query must pass existing source-planner validation and normal
capability, subject, security and evidence gates. Generated URLs/bodies/verdicts
are never used as evidence.

## Files/functions and rationale

| Owner | Change |
| --- | --- |
| [EntitySubredditResolver.resolve](../../backend/infrastructure/acquisition/resolution/social_resolver.py) | Whole-token/phrase matching for brand and sector routing; `ev` inside Unilever, `ai` inside Pichai, partial brand names no longer classify the subject |
| [source_identity.py](../../backend/services/research/source_identity.py) | Conservative URL identity: root slash, host case, default ports and fragments; preserve meaningful paths/queries/ports. Exact body duplicate detection retains canonical ID, duplicate IDs and reasons |
| [DeepReader](../../backend/services/research/deep_reader.py) | Avoid duplicate canonical reads, exclude reference-only reads, classify feed/search captures as discovery-only; existing byte/time/access/SSRF limits remain |
| [DeepReadingStage.run](../../backend/application/research/reading.py) | Reserve original slots for publisher continuation instead of spending all on wrappers; prefer actual financial-event titles; one observed publisher hub leaves slots for its feed/search and articles |
| [publisher_links.py](../../backend/services/research/publisher_links.py) | Follow bounded observed same-publisher links; direct subject articles outrank additional discovery hops; observed RSS/Atom and public GET search forms can lead to article URLs, never guessed slugs |
| [page_extraction.py](../../backend/infrastructure/acquisition/adapters/web/page_extraction.py) | Retain explicit feed declarations and one same-publisher public GET search form. POST, external forms and unknown parameter names are not executed |
| [discovery_document.py](../../backend/infrastructure/acquisition/adapters/web/discovery_document.py), [NativeExecutor.execute_web_read](../../backend/services/agent_reach/native/executor.py) | Parse already-fetched bounded RSS/Atom/sitemap XML into observed links; no second fetch to parse the same bytes, no XML entities/DTD. Sitemap lastmod is not publication |
| [RelevanceGate](../../backend/services/research/relevance_gate.py), [CandidateQualificationStage](../../backend/application/research/acquisition.py) | Explicit provisional-read mode for on-topic undated Trending discovery; default qualification stays strict. Stale/future timestamps are not provisionally accepted |
| [PassageAnalysisStage](../../backend/application/research/synthesis.py), [body_context.py](../../backend/services/research/body_context.py) | Deduplicate captures and requalify actual body/entity/date before findings. Unique explicit Article/NewsArticle JSON-LD publication declaration may be observed; unspecified date lines remain unverified labels |
| [content_roles.py](../../backend/services/research/content_roles.py), [PassageExtractor](../../backend/services/research/passage_extractor.py) | Encyclopedia/reference text remains inspectable background across all domains, not a current financial/trend/threat finding. Temporally ineligible bodies cannot regain a usable excerpt |
| [search_advice.py](../../backend/services/research/search_advice.py), [AdaptiveExpansionStage](../../backend/application/research/adaptive.py) | Optional one validated query after insufficient task-appropriate direct leads; short subject/context only, sensitive input excluded; deterministic continuation on any advisory failure |
| [advisory_policy.py](../../backend/infrastructure/llm/advisory_policy.py), [GeminiProvider](../../backend/infrastructure/llm/providers/gemini.py) | Existing SQLite reservations/cooldown and strict model/160-token/one-attempt limits retained; sanitized model/purpose/status/latency/provider token accounting, scoped to investigation and batch |
| [ResearchPipeline](../../backend/application/research/pipeline.py), [CorpusAssemblyStage](../../backend/application/research/assembly.py), [discovery_funnel.py](../../backend/services/research/discovery_funnel.py) | Expose advisory decisions, duplicate aliases and post-read rejection reasons. All instrumented discovery-provider failures with no candidates cannot appear as an empty successful investigation; uninstrumented legacy transport stays unknown |
| [Terminal runner](../../scripts/audits/run_terminal_agent_quality.py) | At most five AI-authorized cases per batch; one non-generation capability lookup for the configured model, no model/key substitution; opens explicit advisory scope only on observed support, preserves shared ledger and saves actual reservation/usage counts |

Observed form/feed URLs receive normal safe reads, not evidence acceptance.
Feed/search index text cannot become a finding even when long. Subject mismatches
and blocked/failed pages remain rejected. Existing title-token joins, irrelevant
result fallback, topic/person separation and safety-advice protections remain.
No CAPTCHA/paywall/rate-limit bypass, proxy proliferation or forced acceptance.

Research ceilings remain 120s in the authorized checks, six reader attempts,
bounded provider HTTP calls/concurrency. The baseline's 30–40s empty outcomes
were not caused solely by a 120s total limit, so increasing it again was not
justified. No arbitrary delay or unbounded retries were introduced.

## Baseline → implementation evidence

First used genuine saved five-case responses with network blocked. Unilever's
historical finding disappeared, duplicate root capture collapsed (4 → 3 records;
3,069 → 2,594 retained words); background source bytes remained. Trending's five
undated leads became inspectable read candidates, not fresh findings. Replay is
an interpretation regression, not proof of live source recall.

The new deterministic suite also covers a generic wrapper → observed hub → feed
→ actual article chain inside four attempts; context/negation and canonical IDs
survive. This mocked positive control is not presented as a fresh article capture.

## Authorized five-case live batch

Ran exactly one request for each original failure input, after offline stabilization.
Temporary SQLite/dossiers, no notifications/background ingestion or production
writes. One bounded model-capability GET, then at most three short Gemini calls.
No audit retries, supplied article URLs, broad source sweeps or model/key fallback.

Application fingerprint stayed unchanged during this batch:
`f71cff883b42a9668872d148a624e37e267708f858b8eed6c46027228373317d`.
Later priority/advisory-attribution/failure-reporting corrections are offline
tested and must not be described as part of that earlier live code version.

| Input | Baseline retained words / qualified evidence | New live observation | Actual source quality / first loss |
| --- | ---: | --- | --- |
| Samsung | 0 / 0 | 41.59s, 455 retained words / 12.000KB, one capture, zero qualified evidence/findings | Yahoo Finance landing page, not an article. Three attempts: one HTTP failure, one unresolved wrapper, one hub. Generic direct leads displaced task-specific headlines; corrected offline afterward |
| Unilever | 3,069 / 1 historical heuristic item | No result event; 504 observation failure after 14,747.90s; late isolated dossier says no acquired body | Interrupted/non-comparable. Adaptive stage spans the host-time gap, then read deadline exhausted; no automatic retry. Offline replay proves removal of historical/duplicate output, not live recovery |
| Adidas | 3,002 / 0 | 23.25s, zero candidates, reads, bodies or findings | Native discovery transport/security failures; legacy fallback transport unknown. Earlier code's insufficient status was misleading; final failure propagation corrected offline |
| grid-scale energy storage | 0 / 0; five missing-date rejections before reading | 35.14s; four accepted read leads, one attempted read, zero bodies/findings | Provisional qualification progressed to reading; read rejected at SSRF layer. No guard bypass. Not proof that candidates were fresh or accessible |
| Sundar Pichai | 2,060 / 0 | 45.17s, one 9-word / 0.068KB profile; six read attempts, zero article bodies/findings | Five publisher-resolution failures. Profile is metadata, not identity or threat evidence |

Raw words/KB include noise and metadata, not useful article words. **New qualified
article bodies: zero; qualified useful excerpt words: zero; qualified current
sources: zero; independent qualified publishers: not established.** No unsupported
positive finding was emitted. Empty output is not proof of safety or absence of
public information. Since no new relevant article was acquired, there are **no
honest new article URL/date/useful-word examples to list**. The earlier Adobe
[historical control](ADOBE_POSTFIX_LIVE_CHECK_2026-10-20.md) is not substituted as
a success in this batch.

### Host-time interruption and access diagnostics

Unilever logs jump from host time 06:46:34 to 10:52:00. An offline Windows system
event query records Kernel-Power sleep/resume events near the start of the gap;
this supports a host interruption but does not establish the exact cause of the
entire gap. Stage telemetry locates 14,729.705s in adaptive expansion. Afterward
the exhausted deadline prevented reads and the stream returned an observation
504. The late dossier is preserved separately, not passed off as the missing SSE
result. This is not normal 120-second deadline compliance or a latency gain.

After resumption, saved native feed observations include `SecurityPolicyViolation`
and search transport errors; a Trending read records `ACCESS_REJECTED` / `SSRF`.
Later read-only DNS/validator checks for the already-queried Google News/Bing
hosts returned public address classes and safe URL checks. Thus the recorded
failures cannot honestly be described as a proven persistent private-IP block;
transient resolution/transport details remain unverified. Security code was not
weakened. No extra HTTP acquisition sweep was used to hide those failures.

## Gemini — actual provider inference succeeded

Configured advisory model: **`gemini-3.5-flash-lite`**. One capability GET returned
200 and declared that exact model supports `generateContent`. Generation responses
reported the same model. The unrelated general-service default printed at startup
was not used for these strictly scoped suggestions.

| Investigation | Provider status | Latency ms | Prompt tokens | Output tokens | Total tokens |
| --- | --- | ---: | ---: | ---: | ---: |
| Unilever | 200 / GENERATED | 1,172.69 | 391 | 90 | 481 |
| Adidas | 200 / GENERATED | 1,438.33 | 389 | 51 | 440 |
| Sundar Pichai | 200 / GENERATED | 1,317.48 | 396 | 48 | 444 |

**Exactly three reservations/generation attempts; 1,365 provider-reported tokens
total, 189 output tokens.** At most one call per investigation, each below 160
output tokens. No generation retry, key/model fallback, quota probe, AI verdict
or generated research summary. Capability support is not research success:
these suggestions did not yield acquired article evidence in this batch. Monetary
cost was not independently measured. Earlier live trace snapshots include
cumulative advisory observations; final telemetry filters to the current
investigation while retaining batch accounting. Original captures stay unchanged.

## Testing and remaining gates

New [25 regressions](../../tests/unit/test_p0_source_overhaul.py) cover routing
collisions, preserved explicit sectors, conservative identity/body deduplication,
the genuine normalized encyclopedia failure excerpt, provisional-to-final date
qualification (missing/stale/future/fresh), observed XML/forms, bounded full chain,
financial priority, policy admission and investigation-level audit isolation.
All provider generation in normal tests is mocked/disabled; real calls occur only
in the explicit live scope. The historical golden manifest is unchanged; its
canonicalizer excludes only additive advisory diagnostics, separately tested.

### Final commands actually run

| Command / scope | Actual closeout result |
| --- | --- |
| Focused overhaul + substantive/funnel tests | Exit 0; **75 passed / 1.75s** |
| `python -m pytest tests/ -q` | Exit 0; **1,580 passed / 61.93s** |
| `python -m pytest tests/unit tests/chaos tests/security -q` | Exit 0; **1,372 passed / 44.77s** |
| Fatal flake8, E9/F63/F7/F82 | Exit 0; zero fatal findings |
| Each of nine `tests/frontend/test_*.js` Node scripts | Exit 0 each; no frontend code changed this continuation |
| Release smoke, fresh temp JSON | Exit 0; OFFLINE_SMOKE_PASS |
| Rollback validator, fresh temp JSON | Exit 0; OFFLINE_PERSISTENCE_PASS; historical archive and deployed rollback NOT_VERIFIED |
| Frozen verifier / protected Git diff / whitespace and document-link checks | Exit 0; content hashes match, protected data unchanged, relative links resolve |
| Five-case terminal runner | Exit 1 because Unilever has an observation error; not passed off as a successful batch |
| Separately authorized Samsung runner | Exit 0 transport; ACQUISITION_FAILED / zero bodies, not research success |
| Saved genuine-response reprocessing / read-only funnel summaries | Exit 0; no fresh acquisition or live AI in replay |

Portable live command (run once, authorization now consumed):

```text
python scripts/audits/run_terminal_agent_quality.py --allow-live --allow-live-ai --env-file <server-env> --output-dir <new-temp-directory> --case scout:Samsung --case scout:Unilever --case brandshield:Adidas --case "trending:grid-scale energy storage" --case "personal_watch:Sundar Pichai" --timeout-seconds 120 --max-deep-reads 6
```

The extra Samsung command omitted `--allow-live-ai`, used only `--case
scout:Samsung`, and a new `samsung-postfix` directory. Actual offline commands
were the AGENTS full/fast/fatal-lint commands, each Node script,
`python scripts/validation/verify_frozen_benchmarks.py`,
`python scripts/validate_release_candidate_smoke.py --output <new-temp-json>` and
`python scripts/validate_rollback_compatibility.py --output <new-temp-json>`.
Source responses and gate outputs use fresh temp paths, never tracked benchmark
results. No remote CI or deployment ran. Historical malformed dossiers were not
silently repaired to claim recovery; this isolated archive is not that collection.

Intermediate full run exposed the new
feed discovery read being rejected by ordinary subject-score eligibility; that
was corrected only for explicitly observed discovery-index reads. It did not
relax article qualification. Ten golden hash differences were new diagnostic
fields, not changed evidence; explicit projection exclusion restored the old
core hashes without changing frozen fixtures. These failed runs remain in temp
logs and are not reported as passes.

## Outstanding work and recommendation

### Separately approved Samsung post-fix check

User subsequently approved exactly one additional AI-disabled Samsung check, with
the same 120s/six-reader ceiling. It ran once in **32.35s**, no SSE errors, no AI
calls. Application bytes were stable during that run
(`40604e4533b9d2aee4d286774637c7ca664f99c610cd2a7cb62c9462ccf51b09`).
The actual earnings-announcement candidate was now read first; two publisher
lookups remained unresolved and the observed `https://news.samsung.com` hub
returned **HTTP 403**. Three attempts, zero captures/qualified evidence/findings.
This confirms selection correction and a concrete access failure, not acquisition
success or evidence that every Samsung source is inaccessible.

[Post-fix native measurements](evidence/2026-10-20_p0_overhaul/samsung-postfix-funnel.json)
preserve that outcome. Afterward, a final **offline-only** regression corrected
fallback allocation: an inaccessible first publisher may use a second observed
publisher while reserving feed/article slots within the original six attempts.
The mocked blocked-publisher → second hub → feed → article test passes, but this
last fallback adjustment has no fresh live proof. No seventh investigation or
fourth Gemini call was made. Both the five-case and one-case permissions are
consumed.

### Release decision

**Not ready for separately authorized production verification.** First obtain a
valid awake-host local acquisition run with real relevant article bodies. Main
remaining P0 is publisher resolution/transport, not cosmetic frontend work or
more model calls. Evaluate the existing deterministic/public publisher paths
under a small approved request budget; do not add guessed targets, loosen title/
entity/date checks or bypass access controls to manufacture success.

No fresh independent truth/accuracy evaluation, rendered-browser run, hosted CI,
deployed rollback or recovery of historical malformed dossiers was performed.
All normal data-integrity constraints remain. Full source events/logs/temp
dossiers and regression logs are under system-temp basename
`aegis-p0-overhaul-7bfe8bdb5d464f3490946f0761ab4d6d`; selected sanitized summaries
are durable in the evidence folder. Temp data may expire. This report records
engineering decisions and actual outcomes, not a private reasoning transcript.
