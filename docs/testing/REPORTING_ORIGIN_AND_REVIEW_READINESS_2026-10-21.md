# Reporting-origin integrity and review readiness — 2026-10-21

## Decision and scope

**Two confirmed reporting-integrity defects repaired; independent research-quality
acceptance remains NOT VERIFIED. No deployment.** This continues the
[Trending checkpoint](TRENDING_FRESH_ACQUISITION_COMPLETION_2026-10-20.md), not the
obsolete empty-acquisition state in the preserved P0 report. No new source requests,
AI calls, quota probes, commits, pushes, merges or production mutations occurred.

Worktree `.scratch/phase9-remediation-20261016`, branch
`fix/p0-lenovo-acquisition-20261018`, base HEAD
`39a514b68388450bbc5e6061aba97bda2077fc7f`, with the existing large uncommitted
implementation preserved. The outer IDE worktree is different. Passing tests here
does not establish deployment parity or hosted CI.

## Defects, changes and tradeoffs

### P1: differently titled wire stories could self-corroborate

`SourceIndependenceEngine.cluster_independence()` previously reused the
title-specific wire story family as `independence_group`. Two Reuters-attributed
articles with different headlines therefore counted as two independent origins.
`evaluate_grounded_claim()` trusted those labels and could upgrade matching
passages to `SUPPORTED` with the rationale “independent corroborating sources”.
An offline synthetic reproduction confirmed that upgrade; it is not a real claim
or a held-out accuracy case.

[Origin grouping](../../backend/services/research/source_independence.py) now
separates story-family identity from reporting-origin components. Shared observed
publisher, recognized wire attribution or duplicate headline connects records
conservatively, including transitive publisher/wire bridges. Arbitrary incoming
group IDs and missing URLs cannot manufacture corroboration. Original bodies,
IDs and story-family diagnostics remain intact.
Known wire publisher hosts also join attributed republications when the original
article does not repeat its own wire name in the captured byline. Invalid publisher
keys do not increase counts, and unresolved primary/authority metadata cannot
upgrade corroboration or a claim through another ordinary source's valid locator.
[Claim assessment](../../backend/services/research/proposition_grounding.py) and
[corroboration](../../backend/services/research/corroboration.py) recompute this
same grouping rather than trusting caller strings. Two same-origin passages remain
`UNVERIFIED` absent a separately qualifying authoritative record. Rationale text
now describes heuristic origin grouping, not authenticated independence.

Tradeoff: shared-host and incidental wire-marker matches can conservatively merge
otherwise different reports. The existing publisher-key suffix heuristic is not
an exhaustive public-suffix/ownership registry. Distinct groups still do **not**
prove independent investigation, truth, authenticity or calibrated confidence.
Primary-source classification and passage reasoning remain heuristic and require
the separate reviewer evaluation; this change is not a universal fact-checker.

### P2: final-report trust count described an upstream source pool

`_complete_agent_report()` previously copied `independent_source_groups` from the
pre-specialist acquisition trace into final report trust. Personal Watch could
thus display five groups while retaining one qualified source.

[Report assembly](../../backend/services/report_builder.py) now derives additive
`trust.observed_publisher_count` only from final retained-record URLs, including
the claim-verifier boundary. It leaves `independent_source_count` and the shared
trust independence axis null: no verified-independence contract is implemented.
The upstream heuristic count remains explicitly named in processing diagnostics.
Discovery-only records do not increase the retained publisher count. The
[schema](../../backend/schemas/unified_report.py) no longer promotes corpus group
counts to verified independence. The [renderer](../../frontend/unified-report-renderer.js)
prefers the new count with an explicit independence limitation; historical payloads
without it retain the older clearly labeled heuristic fallback.

## Genuine saved-source replay, not fresh discovery

Reprocessed the original October 20 Samsung and Sundar Pichai raw pools through
the current isolated API/SSE routes. Both replay manifests confirm original source
IDs, URLs, titles, publication dates and body hashes unchanged; network and model
calls were blocked. Different reporting/selection counts below are not new live
acquisition or new source recall measurements.

| Saved case | Previous final trust group count | Current retained records | Current observed publisher groups | Verified independence |
| --- | ---: | ---: | ---: | --- |
| Scout / Samsung | 7 | 7 | 6 | Not established |
| Personal Watch / Sundar Pichai | 5 | 1 | 1 | Not established |

The corrected upstream heuristic origin counts are four and five respectively;
neither is exported as final verified independence. Current reports retain six
and one finding strings, with source-ID joins available. These observations do
not independently establish the correctness of those findings.

Current saved SSE was replayed through actual page buttons and unchanged streaming
client in Chromium at **320, 390 and 1440px**: six rendered states. All had no
uncaught page exceptions, horizontal overflow, missing finding text or source-ID/
URL/title/hash mismatches. The first evidence-inspection disclosure opened with
keyboard Enter in each state. Focused Personal Watch/mobile and Scout/desktop
trust screenshots were visually inspected. External font requests were deliberately
blocked; resource errors from those blocks are not app exceptions.

Application source fingerprint was stable throughout the final browser run:
`53ea40a1ab4ae48eb55fb6f72d98b0b4ff58e9e3d0935a9cec4cc3d408d15eb1`.
Readiness and result transport are replay harness responses, not live-provider
health or original discovery timing. No screen-reader, axe, measured contrast,
alternate-engine, real-device or deployed-browser acceptance is claimed.

## Independent-review tool, not invented ground truth

The existing [48-slot reviewer packet](RESEARCH_QUALITY_REVIEWER_PACKET_2026-10-18.md)
remains unfilled. New [review instructions](RESEARCH_QUALITY_HUMAN_REVIEW_2026-10-21.md)
and an [offline companion](../../scripts/evaluation/reviewer_acceptance.py) bind
human judgments to exact label/observation file hashes. The existing scorer alone
computes verdict accuracy, wrong decisive judgments, justified abstentions, source
recall and exact-span validity. The companion adds per-agent summaries and separate
human acquisition-quality, citation-entailment and usefulness assessments.

Missing reviews remain `NOT_VERIFIED`; span matching cannot become entailment.
Review completion cannot grant research/release acceptance. No expected answers,
human reviews, thresholds or new live investigations were fabricated.

## Commands actually run

All outputs use a new system-temp directory. Counts below are this checkout's
dated observations, not permanent acceptance requirements.

| Gate | Final result |
| --- | --- |
| Initial targeted origin/schema/evaluator tests | Exit 0; 131 passed / 3.74s |
| Corrected golden/origin/integration subset | Exit 0; 59 passed / 1.83s |
| `python -m pytest tests/ -q` | Exit 0; **1,826 passed / 51.12s** |
| `python -m pytest tests/unit tests/chaos tests/security -q` | Exit 0; **1,618 passed / 45.54s** |
| Fatal flake8 E9/F63/F7/F82 | Exit 0; zero findings |
| All nine `tests/frontend/test_*.js` Node scripts | Exit 0 each |
| Frozen benchmark verifier / protected tracked diff | Exit 0; original hashes match, no protected changes |
| Release candidate smoke, new temp JSON | Exit 0; `OFFLINE_SMOKE_PASS` |
| Rollback validator, new temp JSON | Exit 0; `OFFLINE_PERSISTENCE_PASS`; original historical archive and deployed rollback `NOT_VERIFIED` |
| Two current API replays / final Chromium saved-SSE run | Exit 0 each; zero fresh acquisition/model calls |

New regressions: [21 origin/projection cases](../../tests/unit/test_reporting_origin_integrity.py)
and [38 reviewer-tool contracts](../../tests/unit/test_reviewer_acceptance.py).
They are labeled synthetic controls, not independent accuracy labels.

Intermediate full/fast runs passed 1,819/1,611, then 1,823/1,615 before the final
invalid-locator/primary and direct-wire-host controls were complete. The final
replays/browser and full/fast results above include those corrections.
The first full run honestly failed seven cases (1,812 passed): three fixtures
asserted old URL-less/caller-assigned group semantics, and four golden scenarios
serialized corrected origin fields. Fixtures now provide explicit synthetic URLs
or assert unverified independence. A new
[explicit delta manifest](../../tests/unit/fixtures/research_origin_integrity_deltas.json)
records the four intentional hash changes; original golden manifests and protected
datasets were not regenerated. Existing candidate-byte/identity assertions remain.
The first browser harness attempt stopped before rendering on its configuration
isolation assertion when given a nonexistent environment file. Subsequent isolated
replay supplied the existing configuration through the harness's credential-blanking
path, with zero configured Gemini credentials. No production configuration changed.

## Remaining acceptance boundaries

An independent reviewer still needs to select/freeze held-out cases, inspect real
passages and judge acquisition, entailment and usefulness across all four agents.
Repeated observations are needed for trend velocity/virality; grouping alone is
not independence. General provider reliability, future live recall, original
historical dossier integrity, hosted CI, production parity and staging rollback
are not proven by these offline repairs. No new live permission was consumed.

[Selected durable proof](evidence/2026-10-21_origin_integrity/README.md) ·
[Resume handoff](../handoffs/2026-10-21_REPORTING_ORIGIN_AND_REVIEW_READINESS.md).
