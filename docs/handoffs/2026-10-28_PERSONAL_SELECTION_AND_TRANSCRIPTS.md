# Personal discovery and transcript attribution — 2026-10-28

User accepted targeted Personal Watch discovery, rights-notice, DEEP-default and
publisher-selection repairs, followed by two Personal Watch checks and Trending.
Work is local on `fix/personal-evidence-20261028`, base
`8b5a9a55a8df030ccb86ccbd1f99be959e6885d7`, in the isolated deployment checkout.
Root/remediation worktrees and their existing changes remain preserved. No new
commit, push, merge or deployment. Production still runs the earlier `ec5bef1`.

Read the [source-level report](../testing/PERSONAL_SELECTION_AND_TRANSCRIPT_REPAIR_2026-10-28.md)
and [sanitized measurements](../testing/evidence/2026-10-28_personal_selection/measurements.json).

## Changes and rationale

- `harvesting.diversified_queries`: quoted names and interview-first discovery
  for ordinary Personal Watch queries as well as explicit public-statement tasks.
  The ordinary path previously bypassed changes to specialist angles.
- `candidate_selection.score_candidate`: prefer observed statement formats and
  comparable unread publishers, with a bounded diversity penalty so irrelevant
  new publishers cannot displace relevant leads simply for novelty.
- `ResearchBudget.for_profile` and application pipelines: rebase only implicit
  profile defaults; explicit environment/direct caps remain binding. A request
  timeout cannot enlarge the configured server ceiling.
- Native extraction/serialization: generic copyright notice is recorded as an
  observation, distinct from explicit article licence exceptions. Existing
  source permissions, access and SSRF checks remain.
- `passage_records._transcript_speaker_section`: preserve existing explicit
  transcript mode; add transcript-title plus repeated full-name turn recognition,
  honorific matching, host/editor exclusion and multi-speaker span rejection.
  Acquired article turns discovered through a threat query can retain observed
  attribution. No author shortcut for incidental metadata or non-article captures.
- Personal assessment includes transcript-turn attribution in its bounded
  statement list. Rhetorical uses of “scam” without described incidents remain
  source-reported context, rather than identity threats. Genuine phishing,
  fake-stream and reported fraud controls remain unverified incident observations.
- A final review found an actual Mary quotation in a previously rejected article.
  Incidental acquired articles now share the full-name-introduction and ambiguity
  checks used for reported surname quotations. Sentence-leading connectives no
  longer become fictitious competing people; honorific periods are normalized.
  Actual competing names, metadata/indexes and disputed quotes remain excluded.

## Actual acquisition versus offline correction

All live cases used normal local ASGI/SSE requests, DEEP, at most 240 seconds,
24 reads and 120 native HTTP admissions, no article URL supplied by the audit.
Temporary persistence; no notifications, production writes or paid readers.

| Case | Live outcome | Final offline processing |
| --- | --- | --- |
| Mary Barra, initial | 119.35s; 18 reads; no article bodies | No evidence fabricated |
| Fei-Fei Li | 67.17s; nine bodies / 17,154 raw article words; initially only 113 introductory/editorial words published | Same saved sources now publish 5,773 exact speaker-turn words / 90 passages / three records from one publisher; 16 bounded native statement observations; no identity authentication |
| battery recycling | 53.59s; two bodies / 2,656 raw article words; both stale | Zero current sources; 338 older background words remain |
| Mary Barra, one post-query-fix check | 94.01s; four bodies / 5,309 raw article words; initially one 62-word criticism passage | Same saved captures now publish 99 words: 37-word reported statement plus 62-word context, two records; identity risk corrected to UNASSESSED |

Both native replays preserve source IDs, URLs, titles, dates and exact body
hashes, with network and all gateway generation blocked. Initial versus later
Mary live runs have different stable application fingerprints and provider
observations; do not describe them as deterministic before/after proof.

Six local-browser saved-SSE states passed at 390/1440 pixels. All 90 Fei passages
were reached through pagination and matched exact report text; Mary's statement/context and
Trending background matched. No overflow or uncaught exceptions. Fei mobile and
Mary desktop screenshots visually inspected. Readiness was a harness stub;
these were not new live frontend/provider investigations.

## AI and tests

Three advisory reservations across four live requests: two Flash-Lite successes
with 735 known provider tokens total (123 output), one timeout with unknown usage.
Two non-generation capability GETs. Existing local shared eight/day ledger
advanced 0 → 2 → 3 without resetting it. No retries, quota probes or model fallback.
No production AI storage/config change; its durable policy ledger remains a
separate outstanding deployment requirement.

Final regression/validation results are recorded in the linked report after
the closeout run. Initial full/fast failures were two old exact-query assertions;
they were updated to the new quoted interview query while preserving routing
and attribution controls. Targeted useful-yield rerun: 42 passed. Final focused
selection/transcript/source-report checks: 39 passed; late surname/control run:
75 passed. Fatal lint, ten frontend
scripts, frozen hashes, isolated smoke/persistence and protected-tree diff pass.
Final stabilized full/fast reruns: **2,831 / 2,623 passed**, exit 0; pytest times
132.94s / 74.31s. Final fatal lint, ten Node scripts, frozen verifier, isolated
smoke/persistence, protected diff and whitespace also exit 0. Six final browser
states match exact published text. Initial failed and intermediate successful
runs remain separately recorded; none is substituted as final-code proof.

Temporary native reports, bodies, SSE, intermediate failures and full logs:
system-temp basename `aegis-personal-selection-20261028-cafk_ckt`. Selected
measurements/screenshots are durable; temp data can expire. Historical dossiers,
frozen benchmarks, research/artifacts and scrapers remain preserved. The earlier
55 malformed dossiers were not repaired or certified by isolated persistence.

## Remaining work

Research acceptance remains partial. Mary now has one short reported quotation
but needs substantially broader statement evidence;
Trending needs current qualifying articles. Fei's three third-party transcripts
are not independent sources or verification against original recordings. Broader
held-out passage accuracy and production behavior of these local changes remain
unverified. Do not use word growth alone as acceptance or imply this work deployed.
