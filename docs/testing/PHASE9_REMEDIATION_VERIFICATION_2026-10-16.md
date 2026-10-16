# Phase 9 remediation verification — 2026-10-16

## Decision

**Software remediation: verified within the checks below. Research-quality
acceptance: FAIL / Phase 9 remains PARTIAL. No merge or deployment authorized.**

This checkpoint fixes demonstrated integrity and reasoning defects. It does
**not** establish that the agents reliably answer real misinformation questions.
The comparable reference replay resolves fewer cases, and eight of twelve final
entity investigations returned no retained records. Do not describe passing CI,
source counts, or safe abstentions as misinformation-detection accuracy.

| Package | Status | Acceptance boundary |
|---|---|---|
| 9A — Benchmark | PARTIAL | Honest replay metrics and split preservation; no independent human labels/new blind validation |
| 9B — Discovery | PARTIAL | Exact-claim planning, read reservations and body preservation; eight final entity scans still empty |
| 9C — Reasoning | PARTIAL | Focused context controls and live title correction; lexical heuristics remain limited |
| 9D — Accuracy/calibration | FAIL | Comparable resolution decreases; calibration not measured |
| 9E — Four agents | PARTIAL | Shared assessment/preservation fixes; domain research effectiveness not accepted |
| 9F — Extraction | PARTIAL | Successful explicit bodies retained; required linked financial statements still missing |
| 9G — Frontend | PARTIAL | Rendered/replay controls pass after clipping fix; strategic explanations and broader accessibility incomplete |
| 9H — Acceptance | PARTIAL | Offline software/CI verified; end-to-end research quality and launch readiness not accepted |

## Scope and baseline

Fetched `origin/main`: `ff6d246bfe1e9cfd0f21d8e32135582e631636f1`, newer than the
attachment's historical main SHA. Work is isolated on
`feat/phase9-intelligence-remediation-20261016`. The previous release worktree's
49 known changed/new files were copied without its credentials and preserved
in checkpoint `9e5b6e3`; its original dirty worktree was not reset or rewritten.
The preserved baseline passed **1,243** full-suite tests before these fixes.

The existing modular monolith, four agents, acquisition adapters, access gates,
report/replay contracts and all sixteen recovered operations remain in place.
No new paid service, production configuration, historical dossier or frozen
retrieval dataset was changed.

## Implemented changes and rationale

- Canonical evidence IDs survive BrandShield, Personal Watch and Trending
  normalization. Discovery/failed-read context is exported by all agents instead
  of vanishing at the shared-report boundary.
- Exact user claims are separated from generic agent-purpose text. Queries no
  longer repeat the entity unnecessarily; known single-domain issuer mappings
  can constrain financial/product discovery. Personal entity scans retain
  identity intent without putting the threat-purpose paragraph in searches.
- Initial and escalating discovery share a bounded slice; reading leaves a
  synthesis reservation. Official corporate landing pages no longer receive
  primary-document priority merely because of ownership.
- Successful `source_url` reads previously lived only in `source_article`, then
  disappeared from research candidates. They now pass through qualification and
  are carried into investigation/reporting without a second request.
- Profile/search/navigation metadata is not sufficient for a supported finding.
  Grouped source observations are UNVERIFIED, not claim adjudications. Explicit
  specialist claims reuse the shared proposition assessor, and its claim,
  verdict, rationale and canonical citations reach `claim_decomposition`.
- Numeric comparisons gate on metric, period, currency and unit; percentages and
  percentage points differ. Separate sentences prevent cross-pairing every
  number in a document. Ambiguous context abstains instead of forcing a number
  comparison. This conservative policy loses coverage; see the measured table.
- Missing literal quotations, incomplete conjunctions, other CVE/arXiv IDs,
  flattened title/author fields and unsupported independence assertions have
  focused regression controls. These lexical heuristics are **not** a general
  entailment model or calibrated probability.
- Tata's anti-scam warning no longer becomes the observed high-severity scam
  finding. Scout model output loses invented citation IDs and cannot declare
  low manipulation risk merely because a model returned JSON. Warning-context
  classification remains heuristic, not a universal abuse adjudicator.
- Nonempty Gemini credentials are treated as configured opaque secrets, not
  validated/rejected by an `AIzaSy` prefix. Authentication uses a server-side
  header, not a key-bearing URL. Configured does not mean upstream healthy.
- BrandShield's zero-source branch still mounts the completed shared report.
  Finding list insets are restored. Claim rationale, canonical citation links
  and captured excerpts render with explicit uncalibrated-score labeling.
  A 320px card-clipping defect found visually was fixed in the existing theme.

## Comparable reference replay — not live accuracy

The runner formerly injected reference authority, counted citation presence as
validity and excluded abstentions from SUPPORT false negatives. The corrected
[evaluation record](PHASE9_EVALUATION_INTEGRITY_2026-10-16.md) defines the metrics.
Both columns below use runtime source classification, not the historical oracle
mode. Labels are recorded as source-adjudicated but **0/88 human reviewed**;
the runner neither fetches the reference URLs nor independently adjudicates the
passages. Some references are illustrative. These are diagnostic fixtures, not
population-level ground truth.

| Split | Cases | Resolved / eligible before | Final | Acceptable before → final | Unsupported SUPPORT before → final |
|---|---:|---:|---:|---:|---:|
| Development | 38 | 22/31 | 20/31 | 28/38 → 25/38 | 0 → 0 |
| Regression | 20 | 17/20 | 14/20 | 18/20 → 15/20 | 0 → 0 |
| Existing held-out | 30 | 8/28 | 5/28 | 10/30 → 7/30 | 0 → 0 |

Final abstentions: 18/38, 6/20, 25/30 respectively. TRUE claims not SUPPORTED:
2, 3, 10. Binary SUPPORT precision/recall: 1.0/0.8, 1.0/0.625,
1.0/0.2308; these exclude other truth labels. Citation joins with literal
supplied excerpts: 22/38, 14/20, 11/30; these do not establish entailment.
Retrieval recall, independent entailment accuracy and calibration remain null.
Convenience, correlated fixtures do not justify population confidence intervals.

The first post-change evaluation was followed by additional controls found in
development/regression/live data. No held-out examples were inspected to tune
the code, but aggregate evaluations were repeated. The final existing-held-out
run is **not a new independent blind validation**. Preserve that limitation.
Intermediate `after_*.json` includes a regression-set false positive about wire
independence; it was fixed, retained as failed evidence, and is absent from the
`final_*.json` results. Do not delete this failure or silently relabel it PASS.

## Real investigations

### Eleven claim probes, then two explicit live title rechecks

The maintained probe runs real `ResearchEngine` acquisition, qualification,
reading, assessment, fresh dossier persistence and shared report assembly.
References are URL leads, **not injected reference passages**. This diagnostic
is not the complete HTTP/browser claim-verifier workflow.

- Apple iPhone 15 announcement: SUPPORTED with an acquired issuer passage.
- arXiv correct/incorrect title: initial true-title **false refutation** exposed
  flattened author parsing. After the fix, fresh bounded rechecks returned
  SUPPORTED / REFUTED, both source-linked. The initial failure remains recorded.
- Microsoft acquisition, false Apple net-income figure, outdated executive role
  and NVD CVSS claim remained INSUFFICIENT_EVIDENCE. The Apple press release was
  acquired but the required net-income statement was not present in the captured
  passage; the linked financial statement was not read. Do not compare revenue
  or earnings per share to net income to manufacture a refutation.
- Impersonation allegation, absent quotation, unsupported mixed premise and
  unavailable-source controls abstained. Lack of evidence is not proof of fraud,
  falsehood, threat absence or media authenticity.

All eleven initial dossiers and both title-recheck dossiers passed their captured
payload/candidate checksum checks. This proves persistence integrity, not that
the contents are factually correct. Source-adjudicated diagnostic expectations
are not human-reviewed labels. After the targeted correction there are three
correctly resolved factual examples across seven factual probes; this combines
a recheck with an earlier pass, not one untouched 3/7 acceptance experiment.

### Final normal entity scans — three per agent

Real Chromium buttons → real local SSE endpoints → real acquisition; no transport
fixtures or POST retries. Isolated SQLite/dossiers, lifespan/background ingestion
off, remote persistence and notifications disabled. Actual Chart.js 4.4.1 was
served; external fonts were blocked. Gemini was configured, mocks off, with a
5-second diagnostic timeout and `max_retries=1` (one attempt per model/key).
These bounds differ from the older audit.

| Agent | Input | Seconds | Native records | Retained KB | Words |
|---|---|---:|---:|---:|---:|
| Scout | TATAMOTORS.NS | 15.11 | 0 | 0 | 0 |
| Scout | INFY.NS | 28.95 | 0 | 0 | 0 |
| Scout | AAPL | 26.25 | 0 | 0 | 0 |
| Trending | OpenAI | 13.93 | 0 | 0 | 0 |
| Trending | NVIDIA | 12.61 | 0 | 0 | 0 |
| Trending | electric vehicles | 4.89 | 0 | 0 | 0 |
| BrandShield | Nike | 18.83 | 2 | 8.202 | 1,398 |
| BrandShield | Apple | 2.42 | 0 | 0 | 0 |
| BrandShield | Tata Motors | 1.87 | 0 | 0 | 0 |
| Personal Watch | Sam Altman | 10.87 | 1 | 0.101 | 18 |
| Personal Watch | Tim Cook | 11.68 | 1 | 0.059 | 8 |
| Personal Watch | Satya Nadella | 16.02 | 1 | 0.073 | 10 |

Total **five records / 8.435 KB / 1,434 words**. Counts are whitespace tokens in
one native `content`/`snippet` per record; KB means UTF-8 bytes / 1,000, excluding
JSON metadata/discovery and duplicated report projections. Personal records are
profile metadata, not impersonation proof. Nike text contains storefront/brand
descriptions, not authenticated counterfeit findings. Eight inputs acquired zero
records. Discovery candidates remain inspectable separately.

The previous audit's fixed direct pass had six records / 1,948 words; its separate
live browser pass had twelve / 3,527. These changing provider observations and
different LLM/category/budget conditions are **not controlled retrieval recall or
latency improvements**. First relevant rank, completeness, contamination and
network-request cost are not independently measured. Query counts are not HTTP
request counts. This work does not prove all sixteen live operation contracts.

## Frontend evidence and limits

- Final acquisition snapshot `30fe3d1`: 12 completed real SSE investigations,
  HTTP 200/result events, matching findings/evidence/discovery counts at 390 and
  1440px, no missing finding text, uncaught page exceptions or document overflow.
  Application fingerprint remained unchanged during that run.
- After CSS changes, the same twelve saved event streams were replayed through
  all page buttons at both widths. This is **24 replay states**, not twelve more
  live acquisitions.
- Initial 44 rendered fixture/report-replay states exercised seven verdicts,
  hostile links/text, 200 records, saved reports and native BrandShield zero-source
  behavior. Basic invariants passed, but visual inspection found internal card
  clipping that document-width checks missed. The stronger 22-state check failed
  nine narrow cases before the CSS fix and **zero afterward**. Keyboard Enter
  toggled disclosure state; injected markup/unsafe links did not execute/render.
- Selected mobile captures for every agent plus claim/empty-state captures were
  visually inspected. The updated 320px claim card wraps its verdict, score,
  rationale and citation. Source prose still contains navigation and long
  excerpts; the count summary is not yet an executive strategic explanation.

These are limited automated/visual checks, **not accessibility certification**.
Manual screen readers, measured WCAG contrast, axe, Safari/Firefox, real mobile
hardware, production parity and final visual/launch acceptance remain UNVERIFIED.
Blocked-font resource errors are retained separately from page exceptions; not
every HTTP resource error was independently attributed. See the
[evidence index](evidence/2026-10-16_phase9_remediation/README.md).

## Regression and delivery

Local Python 3.13: **1,285 full / 1,077 fast tests passed** (42 cases above the
preserved baseline). All eight Node frontend scripts passed; fatal Flake8: zero.
Offline smoke and fresh-process rollback validators exited zero. Rollback's
actual verdict is `OFFLINE_PERSISTENCE_PASS`: the ignored historical archive is
NOT_VERIFIED in this worktree. The protected 55 malformed historical dossiers
were neither repaired nor removed. Deployed rollback is NOT_VERIFIED.
Frozen hashes and protected-tree diff checks passed.

Hosted backend checkpoint `8c8b6c5` passed all five jobs:
[run 38928988850](https://github.com/Shaunakrane914/Misinformation/actions/runs/38928988850).
This includes Python 3.11–3.13 fast suites, full offline regression/persistence,
fatal lint and frontend contracts. The later CSS/replay changes have separate
publication verification; consult the handoff/closeout, not an assumed main merge.

## Highest-value remaining work

1. **P1:** Acquire relevant primary bodies for financial/corporate investigations;
   follow bounded issuer statement/PDF links and align metric, unit and fiscal
   period. The false-number investigation is still unresolved, not accepted.
2. **P1:** Recover useful resolution without restoring unsupported overlap-based
   verdicts. Audit the lost development/regression cases and get independently
   reviewed references. Do not tune to the existing held-out examples.
3. **P1:** Verify successful live LLM inference. Configured generation attempts
   still failed; a separate documented Interactions endpoint probe also returned
   HTTP 503. Models listing success/presence is not inference success. Do not
   print credentials, automatically enable mocks, buy services or bypass access.
4. **P2:** Align bibliographic registry source-role presentation with the scoped
   authority used by grounding. A bibliographic title record is not proof of a
   preprint's scientific conclusions. Improve exact passage boundaries and
   case-specific evidence-gap explanations without inventing facts or dates.
5. Preserve explicit Reddit/SEC/FactCheck access limitations. The retained local
   Reddit flag is an operator setting, not proof of provider authorization or a
   production change. Do not merge/deploy this branch as a finished Phase 9.
