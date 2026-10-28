# Pipeline review repairs and bounded pilot — 2026-10-25

**Reviewed engineering defects repaired; broad research-quality/yield acceptance remains unmet.**
The default controller remains `legacy`; `pipelined_v1` is an explicit experiment. No commit, push,
merge, deployment, credential replacement or access-policy change occurred.

Scope: user's approval to repair the [progress-review findings](ACQUISITION_GROWTH_PROGRESS_REVIEW_2026-10-25.md)
and complete the bounded four-agent comparison. Checkout `.scratch/phase9-remediation-20261016`, branch
`release/specialist-task-20261024`, HEAD `7ad13a5` plus preserved user implementation. Existing predicate,
GDELT provenance, baseline tooling and other uncommitted work were retained.

## Implemented repairs

| Owner | Behavior and rationale |
| --- | --- |
| [PipelinedAcquisition](../../backend/services/research/pipelined_acquisition.py), `_dispatch_reads` / `_complete_read` / `run` | Workers receive private candidate copies. Only the open coordinator merges completed results. Cancellation cannot mutate returned candidates or telemetry through shared references. Late-arriving query aliases and specialist lineage survive the completed merge. |
| [DeepReader.deep_read](../../backend/services/research/deep_reader.py) | Optional reserved attempt identities keep dispatch, completion and interrupted-work records joined. Existing callers retain the prior interface behavior. |
| Scheduler attempt lifecycle | One stable record exists from submission onward. Queued cancellation is `CANCELLED_BEFORE_START`, with provider-start false. Running work at closure is `INTERRUPTED`, with provider-start unknown. No HTTP failure/status is invented. `attempted` remains the submitted read-slot count for compatibility; native service starts and lifecycle fields describe actual execution separately. |
| Scheduler `_dispatch_advice` / `_complete_advice` | One optional weak-yield suggestion uses the existing advisory helper, policy ledger, shared HTTP/operation budgets and remaining read opportunity. A suggested search consumes a query slot rather than increasing the profile's query cap. Advice never becomes a source body, claim or verdict. |
| [Source planner](../../backend/services/agent_reach/source_planner.py), [search advice](../../backend/services/research/search_advice.py) | The small suggestion prompt is restricted to the same news/web channels permitted by validation; other planner callers retain their existing channel set. |
| [ReplayService / label_replay_costs](../../scripts/audits/acquisition_replay.py) | Recorded failed searches receive an explicitly estimated charge when admission cost is unknown. Explicit not-started observations remain zero; recorded counts take precedence. Replay charges/ratios live under `MODELED`, separate from original `MEASURED` fields. Requested Markdown output is now written with the correct estimate label. |
| [ResourceSampler](../../scripts/audits/resource_sampler.py) | Missing/unusable psutil no longer aborts investigations. Memory/thread fields become null with an unavailable reason; CPU/wall timing remains available. |
| [.env.example](../../.env.example), [terminal runner](../../scripts/audits/run_terminal_agent_quality.py) | Correct strict advisory model example, explicit enable flags and persistent-policy guidance. The runner accepts the nonsecret advisory model setting while continuing to blank AI credentials for native-only checks. |

Local server settings were explicitly enabled for search suggestions: `AEGIS_LIVE_ADVISORY_ENABLED=true`,
`AEGIS_SEARCH_ADVISOR_ENABLED=true`, `AEGIS_EVIDENCE_ADVISOR_ENABLED=false`, exact model
`gemini-3.5-flash-lite`. Existing credentials and policy ledger were preserved. Settings apply to a
backend process loading that environment; production settings and existing running processes were not
changed. No backend restart or successful live inference is claimed.

Existing controls remain: 160 output tokens, one generation attempt per investigation, the shared
runtime three-reservation UTC-day allowance, bounded provider time, cooldown and no key/model fallback.
Ordinary regression tests use mocks/network isolation. The native pilot below deliberately made zero
AI calls under the approved comparison scope. AI integration was exercised with a synthetic suggestion
whose observed lead reached the real reader, not by spending provider quota.

## Actual four-case live pilot

Exactly one normal local SSE investigation each: Adobe, Dyson, battery recycling, Mary Barra. DEEP;
240-second request ceiling, 24 reads and 120 native HTTP admissions per case. No whole-investigation
retries, manual article URLs, paid readers, model calls, background ingestion or production writes.
Temporary SQLite/dossiers were used. Runner exit **0**, all four completed; **301 total native admissions**
within the batch ceiling of 480. Provider adapter retries, where normally present, share these admissions.

Application fingerprint stayed stable throughout this pilot:
`66b33be1803cea7a0776cb41f122662cbac690f897260216e94ab717d06a8b0d`.
The subsequent selection/headline/alias follow-ups below are offline-only and belong to a later code
fingerprint, preserved in the [measurement record](evidence/2026-10-25_pipeline_review_repairs/measurements.json).

| Agent / input | Seconds | Read slots | Native admissions | Raw article bodies | Qualified records | One selected passage/source, deduplicated words | Frontend workbench words |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Scout / Adobe | 24.69 | 24 | 66 | 16 | 15 | 822 | 6,963 |
| BrandShield / Dyson | 31.27 | 22 | 86 | 7 | 5 | 317 | 1,629 |
| Trending / battery recycling | 31.18 | 11 | 73 | 1 | 0 | 0 | 0 |
| Personal Watch / Mary Barra | 28.18 | 9 | 76 | 2 | 1 | 114 | 114 |

Raw article-body counts precede semantic/duplicate qualification. Frontend words include multiple
bounded paragraphs per qualified source; they must not be compared as a growth ratio with the
one-passage/source column. Exact same definitions were re-evaluated for the earlier saved observations.
All 12 baseline inputs and the four new native responses remained unchanged during measurement.

| Prior separate interleaved observation → new pipeline observation | Qualified records | Workbench words | Native admissions |
| --- | ---: | ---: | ---: |
| Scout | 10 → 15 | 5,413 → 6,963 | 67 → 66 |
| BrandShield | 8 → 5 | 1,851 → 1,629 | 85 → 86 |
| Trending | 0 → 0 | 0 → 0 | 79 → 73 |
| Personal Watch | 1 → 1 | 114 → 114 | 83 → 76 |

These are separate network observations, not a randomized or identical-response causal comparison.
Scout improved in this sample, BrandShield did not, and substantive Personal Watch/Trending coverage
remains weak. Neither 2× useful yield nor 20× evidence growth is demonstrated.

## What was lost and what the follow-up fixes prove

**Trending:** discovery produced 49 eligible leads. Eleven reads included wrappers, publisher homes,
search indexes, product-report catalog pages and one stale article. The coordinator reached
`FUTILITY_STOP`, leaving 38 eligible candidates unread. Among them was the automatically observed ECS
article URL already represented by a genuine saved fixture. The first decisive loss for that article
was **read selection**, not a demonstrated HTTP denial or the final finite-predicate check.

Three offline corrections followed the live batch:

1. Descriptive article slugs at a publisher's host root now receive the article-shape prior. A second
   path segment is no longer required. Shape remains a routing hint, not body qualification.
2. Empty wrapper/index reads cannot trigger futility while selectable, untested article-shaped leads
   with fresh or unknown dates remain. Existing total, host, deadline and read limits still apply;
   explicitly stale/future dates do not gain a freshness exception.
3. Page extraction retains a later observed headline when an earlier image-only anchor points to the
   same URL. The previous deduplication froze the first empty label. A synthetic HTML control reproduces
   this mechanism; the captured live child leads had empty titles, but the exact originating HTML anchor
   order is not available to prove that mechanism for every live title omission.

The [offline combined-source control](evidence/2026-10-25_pipeline_review_repairs/postfix-saved-control.json)
replays the new investigation's observed links, supplementing only the unread ECS URL's outcome with
its earlier genuine saved body. The corrected pipeline acquired and qualified that exact saved body,
retaining one 100-word passage. This is **not fresh live acquisition, a new timestamp observation or
latency proof**. The four live permissions are consumed; no fifth investigation was run.

**Personal Watch:** the retained source is a September 2021 attributed statement/report about Mary
Barra. It supplies historical context, not current identity verification, impersonation findings or
proof of no risk. Broader public-statement discovery remains unresolved.

**BrandShield:** five qualified sources contain allegations and reports spanning historical dates,
including counterfeit litigation, warnings and complaints. They remain source-attributed/unverified,
not adjudicated current threats. Generic catalog captures were rejected. Some retained passages still
contain incidental editorial/navigation text; byte-exact retention is not proof that every word is useful.

**Scout:** the workbench includes historical and forecast/mixed financial context. Period-aware claim
adjudication, independent source authority and current-filing completeness are not established by the
15-record count.

## Integrity, resources and browser verification

All **150 published passages** across the live reports were checked against raw-pool source joins,
SHA-256 body hashes, exact character slices and deterministic passage identities: **zero errors**.
No passage was omitted by the workbench/source display budgets. Publisher hosts are observations,
not verified ownership or independent corroboration.

Sampled local-process peak RSS was 234.4–277.5 MiB; process CPU time 7.844–12.391 seconds per case.
These are desktop observations, not Render measurements. At the user-stated 0.1 CPU share, the
CPU-only floor projects to roughly 78–124 seconds before other overhead; this is an estimate, not a
deployed latency guarantee. Read-worker count remained two. No concurrency increase is justified here.

The exact four saved API responses were replayed through the real shared renderer on native agent
pages at 320/390/1440 px: **12 states passed** passage pagination/filtering, zero horizontal overflow
and zero uncaught page exceptions. All external browser traffic was blocked; no extra acquisition or
AI call occurred. Four focused workbench screenshots were visually inspected. This does not exercise
native form submission against production, the whole native page, screen readers or WCAG contrast.

[Browser measurements](evidence/2026-10-25_pipeline_review_repairs/browser-measurements.json) ·
[Scout mobile](evidence/2026-10-25_pipeline_review_repairs/scout-390.png) ·
[BrandShield desktop](evidence/2026-10-25_pipeline_review_repairs/brandshield-1440.png) ·
[Trending empty state](evidence/2026-10-25_pipeline_review_repairs/trending-390.png) ·
[Personal Watch historical result](evidence/2026-10-25_pipeline_review_repairs/personal_watch-390.png).

## Validation and continuation

Final checks: **2,556 full /2,348 fast tests passed**, fatal lint zero, ten Node suites passed,
offline smoke/persistence and frozen verification passed within their isolated scopes.
[Actual command results](evidence/2026-10-25_pipeline_review_repairs/test-results.json) and the
[handoff](../handoffs/2026-10-25_PIPELINE_REVIEW_REPAIRS.md) retain counts, durations and limitations. New controls
cover delayed processing after closure, queued cancellation, stable attempt joins, worker errors,
late-discovery aliases, optional advice and read/query caps, root article slugs, futile-discovery
stopping, observed duplicate-anchor headlines, modeled failed-search costs and unavailable resource
sampling. Passing tests do not remove the live quality failures above.

Detailed isolated logs/native captures/SSE streams are under system-temp basename
`aegis-pipeline-repair-8uv6z1ek`; temporary data may expire. Selected sanitized measurements/screenshots
are durable here. Initial test-path selection referenced a nonexistent file and collected no tests;
it was corrected. An initial read-only metric glob included an events list and failed; explicit native
report filenames corrected that diagnostic. These instrumentation failures did not trigger provider
retries and are not presented as research successes.

Next work should test the post-pilot selection fix under a separately bounded live scope, improve
attributed Personal Watch article supply, and independently review current, case-relevant passages.
Preserve strict date, role, access and evidence-integrity controls. Keep rollout opt-in. Historical
dossiers/frozen benchmarks/research/artifacts remain untouched; archive recovery, hosted CI for this
uncommitted code and deployed rollback remain unverified. No deployment is warranted by this pilot.
