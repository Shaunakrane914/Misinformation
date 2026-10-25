# Expansion safety and release integration repair — 2026-10-24

## Decision and scope

The reviewed transport, adapter-boundary, integration and measurement defects are
repaired locally. **20× useful-evidence growth and fresh live expansion acceptance
remain unverified. Nothing was committed, pushed, merged or deployed.** Normal
tests and saved-report replay made no provider/model calls. The earlier four-case
live batch is historical evidence from before this repair, not a post-fix result.
A fresh bounded live-retest permission question was issued; no new authorization
was received during this repair.

Two checkouts were preserved:

| Checkout | Observed branch | Base HEAD |
| --- | --- | --- |
| Original workspace | `feat/phase8-real-acquisition-proof` | `1e1c44e89ff635974150770d5d4cea1e9c9fb19e` |
| Current release, `.scratch/phase9-remediation-20261016` | `release/specialist-task-20261024` | `1a90d681361b8e027a12feb88266932a5cb5d1d1` |

The original checkout is substantially behind the release. Its old service/router
were **not** copied over current global worker pools, security controls or the
existing evidence workbench. New repaired modules and targeted integration edits
were applied to the release. Existing unrelated dirty changes remain intact.

## Defects and resulting behavior

| Defect confirmed by inspection/regression | Repair and ownership |
| --- | --- |
| Async TCP backend instantiated an abstract backend; DNS ran on the event loop | [async HTTP](../../backend/infrastructure/acquisition/network/async_http.py): working AutoBackend delegates only validated numeric addresses; DNS is offloaded |
| Redirect scrubbing missed mixed-case and implicit client credentials | Case-insensitive allowlist strips request/default headers on origin changes; implicit client auth disabled; HTTPS downgrade refused |
| Deadline floor could hide exhaustion; response streaming lacked a total deadline | Entire async operation includes DNS, admission waits and streaming inside a maximum five-second operation bound; bounded raw bytes and bounded gzip decoding |
| Client/limiter state could cross loops; excessive request thread counts | Loop-local clients, max16 connections; thread-safe bounded domain reservations. Original compatibility service capped at8 workers; current release worker controls retained |
| Platform labels/substrings authorized foreign URLs; validator tuples were treated as booleans | [Safety boundary](../../backend/infrastructure/acquisition/adapters/expansion_safety.py) verifies host boundaries and unpacks boolean decisions. Observed external publisher URLs can remain validated discovery leads; they never become adapter-owned captures |
| New Reddit/SEC/FactCheck adapters skipped existing access/configuration requirements | Missing approved Reddit flag, declared SEC contact or FactCheck credential fails closed; no credentials or approval flags were changed |
| Empty responses, feed text, references, abstracts and navigation could appear as articles | Empty content rejected; feeds explicitly syndicated; Wikipedia/background and Wikidata/profile roles retained; arXiv is abstract-only; semantic article extraction reused for HTML |
| Substack filled its limit with unrelated posts; consumer discovery guessed domains | Substack requires observed query matches; consumer reviews require an explicit supported review URL rather than an invented company domain |
| Feed metadata could satisfy a purported article read | Newswire acquire now reads the actual linked document. Feed summary alone never satisfies the read |
| New adapters existed in a dictionary without a normal integration path | [Catalog](../../backend/infrastructure/acquisition/adapters/expanded_catalog.py) connects service, native dispatcher and URL reader. Current release harvest pipeline reserves one of its existing two optional discovery slots; ceilings stay unchanged |
| Aggregate raw counts and sleep benchmarks were presented as evidence/20× proof | [Saved-output measurement](../../scripts/evaluation/test_4_agents_word_extraction.py) counts returned bodies separately from frontend-selected passages. [Scheduler example](../../scripts/benchmarks/benchmark_async_throughput.py) explicitly measures no HTTP acquisition |

The optional async helper is repaired and tested; normal adapter acquisition still
uses the existing bounded synchronous transport in workers. This is **not** a
claim that the four-agent pipeline was rewritten as native async or became20× faster.

## Integration contract

The current release can opportunistically plan one bounded `expanded_sources.search`
action:

| Domain | Discovery adapter | Acquired content requirement |
| --- | --- | --- |
| Financial | Yahoo Finance | Separately read observed article URL; quote metadata alone is not article evidence |
| Brand | Newswire feeds | Separately read linked article; feed text is not a threat finding |
| Trending | Bluesky | Separately acquired public post; never a measured-virality assertion |
| Personal | Substack | Separately acquired body; subject relevance still required |

Wikipedia, Wikidata, Telegram and explicit review URLs have host-specific readers.
Existing canonical SEC/arXiv/Reddit/Hacker News/ClaimReview routes remain in place;
their parallel new adapters do not replace these established routes. Original
checkout integration supports the channel and observed reads; automatic optional
harvest planning is implemented in the **current release** pipeline only.

Provider health remains NOT_PROBED until observed. Registration and synthetic
tests do not establish provider availability, policy approval, source relevance,
independence or accuracy. No Huginn configuration, paid Firecrawl calls, new
providers, permission expansion or access bypass was introduced.

## Verification method and reproducibility

New [security/integration regressions](../../tests/unit/test_expansion_safety_and_wiring.py)
cover all four domain selectors, actual shared-service/native-dispatch consumption,
separate discovery/read failures, body extraction, observed external links, blocked
configuration, host spoofing, compressed/XML bounds, mixed-case/default/client auth,
off-loop numeric socket routing, streaming deadline and truthful measurement.
Positive adapter fixtures use explicitly synthetic DNS/configuration and mocked
HTTP; they do not enable live access. The fixture is restricted to those modules.

Commands, from each intended checkout:

```text
python -m pytest tests/ -q --tb=short
python -m pytest tests/unit tests/chaos tests/security -q --tb=short
python -m flake8 backend tests scripts --count --select=E9,F63,F7,F82 --show-source --statistics
node tests/frontend/<each test_*.js>
python scripts/validation/verify_frozen_benchmarks.py
python scripts/validate_release_candidate_smoke.py --output <new-temp-json>
python scripts/validate_rollback_compatibility.py --output <new-temp-json>
```

The current-release browser audit command was
`python scripts/audits/audit_evidence_workbench.py --report <saved-report>`
(repeated for four genuine saved agent responses), with a fresh `--output-dir`.
All browser traffic outside the local frontend was blocked. Twelve states across
320/390/1440px passed report-count, filter/keyboard, overflow and exception checks.
This is saved-report replay, not new form-to-provider research or a full
accessibility/production acceptance.

The corrected measurement was run on those same four prior responses. Values
below are returned unique native body words, **not** the larger raw acquisition
pool, separately fetched pages or independent quality scores:

| Prior response | Returned body words | Published selected words | Published passages |
| --- | ---: | ---: | ---: |
| Scout / Adobe |16,705|6,948|127|
| BrandShield / Dyson |3,070|792|16|
| Trending / battery recycling |0|0|0|
| Personal Watch / Mary Barra |0|0|0|

These measurements do not demonstrate improvement from this repair. The two zero
cases remain zero; their earlier raw captures did not become qualified evidence.
The synthetic equal-concurrency16-task scheduler example observed about0.81×,
with **zero HTTP requests**, and explicitly reported acquisition throughput
NOT_MEASURED /20× NOT_DEMONSTRATED.

## Remaining boundaries

- Fresh repaired-expansion live recall, latency and relevance remain unverified.
  Reuse the existing bounded terminal runner only under a fresh agreed case budget.
- The historical original archive still has55 malformed JSON files. The read-only
  rollback validator reports HISTORICAL_ARCHIVE_FAIL; no original was repaired,
  deleted or overwritten. Release-worktree archive is empty/NOT_VERIFIED: its
  offline persistence pass does not validate that historical collection.
- No hosted CI, production parity, deployment rollback, independent accuracy
  acceptance, manual screen-reader or all-provider live sweep was performed.
- Frozen datasets, historical dossiers, research/artifact proof and working
  scrapers/shims remain protected. Test counts alone are not research acceptance.
- Intermediate failures are retained in fresh temp logs: missing audit probe
  definition, missing SEC bounded-decoder import and required failure endpoint
  were corrected. They are not counted as passing runs.

See the [repair handoff](../handoffs/2026-10-24_EXPANSION_SAFETY_AND_RELEASE_INTEGRATION.md)
for final command counts and next-agent instructions.
