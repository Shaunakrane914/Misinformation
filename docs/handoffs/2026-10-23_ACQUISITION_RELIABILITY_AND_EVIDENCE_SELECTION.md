# Handoff: acquisition reliability and exact evidence selection — 2026-10-23

## Scope, checkout and release decision

Implementation continues the October 21 twelve-input audit under the user's P0
repair instruction. [Full engineering/verification report](../testing/ACQUISITION_RELIABILITY_AND_EVIDENCE_SELECTION_2026-10-22.md)
and [durable evidence index](../testing/evidence/2026-10-22_reliability_selection/README.md)
separate the October 22 live observations from October 23 offline corrections.

Worktree `.scratch/phase9-remediation-20261016`, branch
`fix/p0-lenovo-acquisition-20261018`, HEAD
`39a514b68388450bbc5e6061aba97bda2077fc7f`, plus substantial inherited dirty work.
No staging, commit, push, merge or deployment. Preserve this entire implementation;
do not assume every file in `git diff HEAD` originated in this continuation.
No credentials/access flags, frozen datasets, historical dossiers, research or
tracked benchmark outputs were changed.

**Overall research/release acceptance remains PARTIAL.** Apple/BrandShield fresh
acquisition recovered; Tim Cook acquired useful bytes but initially discarded
them. The final body/interpretation fixes use those same bytes offline, not a
second live success. Original DNS incident causality, broad source reliability,
independent accuracy and production parity remain unverified. Do not deploy.

## What changed and why

1. Shared safe transport now distinguishes DNS errors/timeouts/capacity from true
   SSRF violations. A brief negative DNS cache and one OS-declared transient retry
   replace failure amplification, without weakening private/mixed-IP rejection,
   fresh numeric-address pinning or original request deadlines. Destination read
   failures do not suppress unrelated publishers. Late results cannot erase the
   original-expiry 429 fence. An uncancellable OS DNS call remains bounded by the
   eight-slot admission limit, not claimed to be force-cancelled.
2. Exact current-event leads outrank historical keyword-heavy paragraphs.
   Competitor developments are explicitly competitive context; former-affiliation
   mentions do not become target developments. Financial publication/period/
   currency/forecast distinctions remain separate and filing comparison stays
   `NOT_PERFORMED`. Replay preserves original acquisition clocks.
3. A captured article without an article DOM container can recover only a bounded
   set of observed title/byline-anchored prose spans. The full readable source and
   hashes remain intact. Main selection, adjacent-paragraph fallback, source-role
   classification, quotation attribution, specialist serialization and legacy
   excerpt projection all enforce the same exact-hash/span boundary. Short related
   headings, stale hashes and outside cards cannot regain evidence downstream.
4. BrandShield preserves concrete lawsuit/enforcement reporting without turning
   publishers into attacker endpoints; preventive guidance remains advice.
   Personal Watch collapses duplicate source/kind alerts into unverified source
   observations, with risk unassessed, no invented suspect handle or probability.
   Fake Cook media is not Cook speaking or proof of current abuse.
5. Shared canonical findings take precedence over Scout catalyst headlines and
   Personal Watch legacy threat dictionary strings. Frontend competitive context
   is separate from direct-topic developments. Nested-worktree offline isolation
   blanks parent-discovered dotenv keys; the installed dotenv version does not
   honor the disable flag by itself.

These are bounded extraction/role heuristics, not calibrated entailment, identity
authentication, independent corroboration or universal misinformation detection.

## Code and regression map

- Transport: `backend/infrastructure/acquisition/security/url_validator.py`,
  `network/http.py`, routing/native adapters and
  `backend/services/agent_reach/native/operation_capabilities.py`.
  Controls: `tests/unit/test_transport_failure_taxonomy.py` and existing security/
  transport/capability suites.
- Selection: `backend/services/research/trend_context.py`, `financial_context.py`,
  `passage_extractor.py`, `raw_pool.py`, application synthesis/harvest stages,
  Scout assessment and Trending projection. Controls: `test_oct21_event_selection`,
  `test_scout_financial_context`, raw-pool and report-projection suites.
- Structural scope: `page_extraction.py::observe_anchored_article_body`,
  `recovered_span_allowed`, `body_context.py`, `passage_records.py`,
  `backend/schemas/evidence_inspection.py`, BrandShield assessment/intelligence.
  Controls: `test_anchored_article_recovery.py`, `test_recovered_scope_projection.py`.
- Specialist observations: Personal Watch assessment, BrandShield intelligence,
  specialist brief and shared report builder. Controls: source-report,
  incident-precedence and completion-projection tests. Genuine excerpts are
  explicitly labeled; synthetic negatives are not fresh source proof.
- Audit helpers: `compare_saved_passage_selection.py` and
  `probe_public_transport.py`; see the [script index](../development/SCRIPT_INDEX.md).

## Evidence boundaries and next safe step

Exactly two approved new local investigations ran sequentially, AI disabled:
Apple/BrandShield and Tim Cook/Personal Watch, once each, 180s/16 reads/80 native
HTTP admissions per case. Both permissions are **consumed**. No audit retries,
model capability lookup or generation. Two earlier robots probes were transport
diagnostics, not extra investigations. All later source/body/API/browser work is
saved-response replay with external acquisition blocked.

Selected source URLs, hashes, counts, original live failures and replay manifests
are durable in the evidence index. Complete ephemeral native captures, pools,
temporary dossiers and logs use system-temp basename
`aegis-reliability-selection-aeaa2931affd4c7481d7ee5c0f437825`; they may expire.
`live-postfix/` is the original immutable fresh batch. Later replay/browser
directories are separate observations, not replacements for its outcomes.

Start with offline regressions and the exact fixture provenance. A final-code
fresh acquisition check requires a new small explicit request budget; do not
reuse these permissions or run a source sweep. The independent human-review
packet remains the accuracy acceptance boundary. Historical malformed dossiers
were not recovered or silently repaired, and isolated rollback is not a deployed
rollback or full historical-archive acceptance.

This handoff records engineering conclusions and actual evidence, not a raw
execution transcript or private reasoning trace. Final command counts, browser
outcomes and failed-run disclosures are in the linked report.

## Actual final validation

- Full Python: **1,969 passed / 79.26s**, exit 0.
- Fast Python: **1,761 passed / 65.46s**, exit 0; overlaps full suite.
- Fatal flake8: zero findings; all nine frontend Node scripts exit 0.
- Smoke: OFFLINE_SMOKE_PASS; rollback: OFFLINE_PERSISTENCE_PASS, with historical
  archive/deployed rollback NOT_VERIFIED.
- Final saved-SSE Chromium: six states at 320/390/1440px, exit 0, correct source
  identities/hashes/passages/citations and no document overflow/JS exceptions.
  Two intentional resource errors per case remain disclosed.
- Frozen content hashes match; protected-tree Git diff empty; whitespace exit 0;
  322 relative documentation links resolve. No Git checkpoint was created.

Final backend/frontend fingerprint:
`3b8fc973e011eaf4db6a0ff0bec130b003e7240df087f3d03857adf19a84cd2a`.
See [machine-readable final checks](../testing/evidence/2026-10-22_reliability_selection/validation-results.json).
The previous golden manifest is unchanged: a narrow test explicitly accepts the
corrected one-unassessed-report result instead of the historical two-HIGH duplicate
alerts. Initial failed suites/browser checks remain disclosed in the report.
