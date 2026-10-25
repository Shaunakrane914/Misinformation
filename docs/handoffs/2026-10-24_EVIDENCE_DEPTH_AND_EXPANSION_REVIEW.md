# Evidence depth implementation and separate expansion review — 2026-10-24

## Status and scope

Owner requested a 20x target, broader websites and application of the proposed
architecture. Implemented locally on `release/specialist-task-20261024`, base
`1a90d681361b8e027a12feb88266932a5cb5d1d1`, initially clean. **Uncommitted, not
pushed/merged/deployed; 20x useful-evidence acceptance NOT demonstrated.**

Owner then requested review of expansion in the separate original checkout:
`feat/phase8-real-acquisition-proof`, HEAD `1e1c44e`. No application edits there.
Preserve both worktrees. That branch is15 commits unique/101 commits behind the
locally available `origin/main`; do not bulk-copy it over the deployed release.

## Implementation map and tradeoffs

[Architecture and contract](../architecture/EVIDENCE_DEPTH_AND_SOURCE_DIVERSITY_2026-10-24.md).
`source_diversity.py` adds24 domain search hints/eight families, up to3 scoped
queries within original caps; not24 verified adapters. `harvesting.py` adds
publisher-share admission reservations, read tie-breaks and planned/submitted
family telemetry, without increased network/read/concurrency limits.

`passage_extractor.py`/`evidence_workbench.py` preserve the compatibility winner,
also selecting bounded complete paragraphs through the same paragraph gates.
No new verdicts; forecasts/history/corrections remain labeled. Native metadata
and inspection validate full-body hashes/IDs/exact offsets. Shared reports expose
a bounded512-passage/240k UTF-8 text-byte collection, deduplicated and source-fair.
Frontend uses8/page with search/publisher/role filters, keyboard pagination,
escaping/safe URLs and responsive styling. This is client-side pagination,
not a new server pagination service or background crawler. Payload/memory rises;
selection remains heuristic and publisher hints can produce inaccessible pages.

Controls: [35 offline tests](../../tests/unit/test_evidence_depth_workbench.py),
[Node tests](../../tests/frontend/test_evidence_workbench.js), existing metadata/
golden/read-opportunity contracts. Historical manifests/frozen data unchanged.
Golden hash canonicalization excludes only additive passage projections; existing
source bytes, IDs, findings/citations remain asserted. Old non-Trending publisher
ordering test now asserts the deliberate tie-break while preserving other gates.

## Source replay and separately authorized live observations

[Replay measurements](../testing/evidence/2026-10-24_evidence_depth/replay-measurements.json)
and [live measurements](../testing/evidence/2026-10-24_evidence_depth/live-measurements.json).
Replay used genuine October23 captures, network/generation blocked, exact original
IDs/URLs/bodies retained. Original observation clock retained for Trending.

| Replay case | Original selected excerpt words | Workbench words/passages |
| --- | ---: | ---: |
| Adobe |650|6,618/124|
| Dyson |48|101/3|
| battery recycling |28|59/2|
| Mary Barra |0|0/0|

Old excerpt counts are NOT all previously inspectable frontend text; old cards
already had chunks/structured passages. Do not call these ratios20x UI growth.

Owner approved exactly four fresh AI-disabled normal local ASGI/SSE cases,
once each, DEEP, <=240s/24 reads/120 native HTTP admissions. All completed with
one result/no SSE error. Zero AI reservations, paid readers, supplied article
URLs, audit retries, notifications or production writes. **Permission consumed.**

| Live case |Seconds|Raw article bodies/words|Code-qualified sources|Published passages/words|
| --- | ---: | ---: | ---: | ---: |
|Adobe|43.88|14/17,104|13|127/6,948|
|Dyson|31.32|9/9,089|5|16/792|
|battery recycling|40.72|9/12,280|0|0/0|
|Mary Barra|26.56|1/484|0|0/0|

Stable before/after application hash:
`4c6aee7bcd14eb1faa25df504e0eba98e9b0009a9cebaa0e8f751c2c73c2ba4f`.
Historical/forecast context is included but labeled. Source assertions are not
independent confirmation. Trending/Mary still fail relevant/fresh task coverage.
Fresh results at different times/budgets are not causal before/after proof.

## Actual implementation-checkout validation

- `python -m pytest tests/ -q --tb=short -p no:cacheprovider`: exit0,
  **2,219 passed/39.07s**.
- `python -m pytest tests/unit tests/chaos tests/security -q --tb=short -p no:cacheprovider`:
  exit0, **2,011 passed/30.28s**.
- Fatal flake8 E9/F63/F7/F82: exit0. All10 Node frontend scripts: exit0 each.
  Frozen verifier/protected tracked diff/whitespace checks: exit0.
- Offline smoke/rollback validators: exit0, `OFFLINE_SMOKE_PASS` and
  `OFFLINE_PERSISTENCE_PASS`. Historical archive/deployed rollback NOT_VERIFIED;
  the original55 damaged dossiers were not touched or silently repaired.
- Four current API/SSE genuine-source replays and exact-span summaries: exit0.
- Actual Chromium saved-report rendering on four native pages at320/390/1440px:
  **12 states passed**. Every published passage reachable with keyboard paging,
  search/publisher/role filters pass, no horizontal overflow/uncaught JS errors.
  External browser traffic blocked. Initial missing inset corrected, all12
  repeated. Scout desktop/BrandShield mobile visually inspected. Not native form
  submission, screen-reader/contrast, all-browser or production acceptance.
- Intermediate full run had9 failures: metadata compatibility, additive golden
  hashes and intentional publisher ordering; corrected before final passes.
  One initial focused command named a nonexistent test and collected nothing;
  never counted as passing. Focused101/25/55 runs overlap the full inventory.

Raw logs/responses/screenshots are in system-temp basename
`aegis-depth-2188fc26b45f4278bbc914460ee3342e`; may expire. Selected sanitized
measurements are durable above. Portable commands:

```text
python scripts/audits/replay_specialist_completion.py --input <saved-native-json> --output-dir <fresh-temp-dir> --agent <agent> --subject <subject>
python scripts/audits/audit_evidence_workbench.py --report <current-response> --output-dir <fresh-browser-output>
python scripts/audits/summarize_evidence_depth.py --mode SAVED_SOURCE_REPLAY --result <current-response> --output <new-summary-json>
```

## Separate original-checkout expansion: review findings, NOT fixes

Reviewed owner's Phase9/10 handoffs, transport, adapters, wiring, benchmark,
coverage/workspace docs and relevant diffs. Its40 focused tests passed/0.90s;
full1,033 passed/32.66s; fast837 passed/13.21s; fatal lint exit0. Those counts
belong to its older checkout, not this release. No benchmark rerun/source sweep.

Blocking findings to verify/fix before integration:

1. `AgentReachService.adapters` populated but no normal planner/router consumer
   found. Async API wraps synchronous retrieval in `asyncio.to_thread`; async
   transport/domain limiter are not called by normal acquisition.
2. New pinned backend constructs the unimplemented base `AsyncNetworkBackend`.
   Pure introspection confirms its `connect_tcp` raises `NotImplementedError`.
3. Network-free MockTransport reproduction retained uppercase AUTHORIZATION and
   COOKIE across origins, and submitted a request despite an expired deadline.
   Synchronous DNS helpers also run in async paths. Not covered by the passing
   original tests. No real credentials or external requests used in reproduction.
4. Several adapters use `(False, reason)` URL-validation tuples as truthy bools.
   Canonical inner HTTP still validates sockets; this alone is not a demonstrated
   SSRF bypass. Substack accepts unrelated posts via `text_match or count<limit`;
   several acquisition paths emit SUCCESS/FULL_ARTICLE from headers/snippets.
5. New Reddit Deep omits approved-access checks; SEC variants use hardcoded
   contact identity instead of required server configuration. Reuse existing gates.
6.120,570-word benchmark adds separately fetched adapter text to normal agent
   output; "useful" means non-stopwords, not reviewed relevant passages. Its
   BrandShield result reports zero threats/dossiers/claims. Async benchmark is
   sleep-vs-sleep, not HTTP throughput, and labels>=15x as achieved20x. Word script
   overwrites fixed artifact paths; do not rerun it over historical proof.

Do not deploy either expansion on headline word counts. Integrate small reviewed
changes onto current release, preserve policy and exact-source contracts, then
evaluate normal query-to-qualified-report behavior at separately approved bounds.
