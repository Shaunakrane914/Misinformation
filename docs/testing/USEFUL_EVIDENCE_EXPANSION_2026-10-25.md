# Useful evidence expansion — 2026-10-25

## Decision and scope

**Implemented and locally verified another expansion increment. The 20× target
is NOT DEMONSTRATED; broader research-quality acceptance remains partial.**
This continues the [October 24 retest](EXPANSION_FOUR_CASE_LIVE_RETEST_2026-10-24.md).
Application edits are in `.scratch/phase9-remediation-20261016`, branch
`release/specialist-task-20261024`, HEAD
`1a90d681361b8e027a12feb88266932a5cb5d1d1`, plus preserved dirty work.
The original IDE checkout remains a different, older branch. No commit, push,
merge, deployment, credential change or protected-data rewrite was performed.

The client task date is October 25 in Asia/Calcutta. Saved observations retain
their actual October 24 UTC timestamps; dates were not advanced to make sources
appear fresh. All live investigations used the normal local agent SSE routes,
DEEP profile, a 240-second request ceiling, at most 24 reader attempts and 120
native HTTP admissions per case. There were no audit-level POST retries,
supplied article URLs, paid readers, AI reservations or model calls. Bounded
provider transport retries/redirects still count against existing admissions.
Native accounting explicitly remains incomplete; admissions are not all sockets
or a billing measurement. Notifications/background ingestion and production
persistence were disabled; storage was isolated in new temporary locations.

## What changed and why

| Owner | Implemented correction |
| --- | --- |
| [Publisher continuation](../../backend/services/research/publisher_links.py), `observed_publisher_articles` | Acquired articles can contribute a small number of explicitly observed source/document links. Article mode uses body links, excludes navigation links, allows one citation generation and preserves parent/child provenance. Cross-publisher candidates have empty bodies and no inherited ownership/primary-source claim. Normal SSRF, DNS, access and body qualification still apply. |
| [Harvesting](../../backend/services/research/harvesting.py), `_observed_children`, `_read_priority` | Removed a weaker fallback that re-admitted off-subject links after helper rejection. Citation leads can reach the existing bounded reader; stronger topic/person matching avoids spending slots on unrelated continuations. No reader or HTTP caps were raised. |
| [Source diversity](../../backend/services/research/source_diversity.py), `diversify_search_plan` | Match existing query angles to publisher families: safety authorities receive safety/recall angles rather than an unrelated impersonation template. Explicit task and validated source-plan priority remain authoritative. These are discovery hints, not access grants. |
| [Personal attribution](../../backend/services/research/passage_records.py), `public_statement_attribution` | Connect quotations to the actual reporting verb/speaker, including a bounded relative clause. An observed surname alias requires the full target in the same capture and no competing given name. Middle-name collisions, accented competing names, suffix matches and borrowed quotations are rejected. A reported statement is not identity authentication. |
| [Content roles](../../backend/services/research/content_roles.py), [passage extraction](../../backend/services/research/passage_extractor.py), [BrandShield](../../backend/agents/brandshield/intelligence.py) | Limited deterministic French/Spanish native-prose and abuse/warning recognition retains substantive already-acquired passages previously dropped by English-only checks. Singular/plural denials remain disputed/insufficient; warnings are not observed attackers. This is not translation, multilingual entailment or full language coverage. |
| [Evidence workbench](../../backend/services/research/evidence_workbench.py), `select_source_passages`, `build_evidence_workbench` | Retain narrowly bounded adjacent issuer/payment-mechanism context only after an explicit subject/task anchor. Preserve exact body offsets, uncertainty and historical/forecast roles. Omit overlapping spans and collapse fully contained duplicate text across captures so publication word counts cannot grow by repeating bytes. |
| [Inspection schema](../../backend/schemas/evidence_inspection.py) | Preserve explicit adjacent-context and overlap-accounting fields across API publication. |
| [Query planning](../../backend/services/research/harvesting.py), `diversified_queries` | A post-run regression showed internal agent intent changing the first personal query's task without changing its text. The task now changes only when that intent actually replaces the submitted query. News/RSS completion order no longer changes the meaning of an unchanged public-statement query. |

The common acquisition layer remains shared. Agent-specific task, attribution,
temporal and relevance gates still decide what becomes usable evidence. More
captured bytes do not automatically become findings.

## Measured fresh results

[Sanitized final measurements](evidence/2026-10-25_useful_yield/final_live_measurements.json)
preserve native-response hashes, source roles, funnels, joins and separate code
fingerprints. [Earlier observations from this cycle](evidence/2026-10-25_useful_yield/prior_cycle_measurements.json)
are retained separately. Raw bodies and source records are not reproduced in the
durable summaries.

The final four-case batch used stable application fingerprint
`3df7720e94d4506da05832d03a9619cc2a2ca656eef12ea2b84cf830a78d6c92`.
Every case returned one complete result, but that alone is not acceptance.

| Agent / ordinary input | Seconds | Deduplicated article bodies | Raw article words | Qualified sources | Published passages / selected words | Native admissions |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Scout / Adobe | 49.79 | 15 | 17,910 | 14 | 111 / 7,111 | 77 |
| BrandShield / Dyson | 29.64 | 9 | 8,302 | 8 | 19 / 1,080 | 93 |
| Trending / battery recycling | 34.53 | 10 | 11,978 | 1 | 6 / 322 | 88 |
| Personal Watch / Mary Barra, before final routing fix | 33.61 | 1 | 484 | 0 | 0 / 0 | 77 |

Totals are 35 deduplicated article bodies, 38,674 raw words, 23 qualified sources
and 8,513 published words across 136 passages. These are code-selected source
assertions, not 136 independently adjudicated claims. All 136 primary spans and
17 identical-text source observations matched retained bodies; body hashes and
evidence-ID joins passed, with no overlapping primary spans. Duplicate mirror
captures are excluded from the article totals. Publisher host groups do not
establish independent corroboration.

### Actual autonomous source-citation acquisition

A captured TechTimes Adobe article contained an observed link to the
[Motley Fool Q2 earnings transcript](https://www.fool.com/earnings/call-transcripts/2026/06/11/adobe-adbe-q2-2026-earnings-transcript/).
The application followed it without a supplied article URL:

- Parent `ev_hv_5c9c7e62a9faf6ac6d84` → child
  `ev_hv_cc50f383461d48cb6c23`.
- Native HTTP reader returned 200 and actual article text: 2,935 retained words.
- Normal qualification retained the source; nine exact passages / 958 selected
  words reached the shared workbench. Its compatibility winning excerpt has
  109 words; that is a different metric.
- A second citation candidate remained unread and unqualified at the existing
  cap. Its source-looking link was never counted as acquired evidence.

This demonstrates the sampled article-to-cited-document path live. It does not
prove every cited URL is reachable or every transcript assertion is correct.

### Personal Watch failure, repair and separate live verification

The failed four-case result is preserved above. Both earlier and failed runs
acquired the same 484-word body, SHA-256
`530fa5799c4afcf87949e388547c29cbd4d5b50f4baa333c9181247a08555f2a`.
The first actual loss was task routing: unchanged query `Mary Barra public
statement` was labeled `IDENTITY_THREAT`, so its surname-attributed paragraph
correctly failed that stricter incidental-threat branch. This was not a
transport failure or a reason to relax attribution safeguards.

After the query/task consistency fix and offline regressions, one separate
AI-disabled normal investigation completed in **18.49 seconds**: one qualified
source, one exact passage / **114 published words**, 76 native admissions.
Its stable fingerprint was
`ff015131a463520c0d0f0250c10295e063b72848cf15e100e2a42c835f955532`.
This is separate post-fix proof, not a replacement for the failed batch result.

The source is a **2021 historical reported statement**. Identity remains
unauthenticated and identity risk unassessed. It does not prove current
impersonation/deepfake discovery. The native specialist section labels a public
statement; the generic workbench currently labels the paragraph ARTICLE_CONTENT
and displays the original publication date. This projection-label difference
is retained as a presentation limitation, not hidden as full semantic parity.

### Growth interpretation

The immediately preceding October 24 workbench sample published
6,484 / 774 / 0 / 0 words for these inputs. Current sampled outputs are
7,111 / 1,080 / 322, plus the separately verified 114 for Personal Watch.
Source availability, routing and code versions differ; this is descriptive
progress, not a controlled causal multiplier.

Earlier legacy *winning-excerpt* counts were 679 / 132 / 0 / 0. Comparing those
with all new workbench passages is not growth over all previously inspectable
frontend text. A zero baseline has no finite growth ratio. **No honest 20×
useful-evidence or accuracy claim follows from these measurements.**

## Browser and offline verification

The exact final four saved API responses were rendered using the real shared
renderer loaded from each native agent page at 320, 390 and 1440px: **12 states
passed**. The separate post-fix Personal Watch response passed **three more
states**. Every expected passage was reachable through keyboard pagination;
search, role and publisher filters worked. No measured horizontal overflow or
uncaught page exceptions occurred. All external browser traffic was blocked.
Selected Scout desktop, BrandShield mobile, Trending mobile and post-fix
Personal Watch desktop captures were visually inspected.

This harness mounts the shared report on the actual page, replacing the page
body. It does not test native form submission, fresh browser-to-provider
integration, every native specialist panel, screen-reader behavior, contrast,
other browser engines or production parity. Long reports remain lengthy, even
with bounded pagination.

[Durable browser measurements](evidence/2026-10-25_useful_yield/browser-measurements.json)
and selected screenshots preserve this narrower scope.

| Command / scope, final code | Actual result |
| --- | --- |
| Focused yield and overlap controls | Exit 0; 48 passed / 0.52s |
| `python -m pytest tests/ -q` | Exit 0; **2,348 passed / 41.71s** |
| `python -m pytest tests/unit tests/chaos tests/security -q` | Exit 0; **2,140 passed / 34.14s** |
| Fatal flake8 E9/F63/F7/F82 | Exit 0; zero fatal findings |
| All ten Node `tests/frontend/test_*.js` scripts | Exit 0 each; individual logs retained |
| Isolated release smoke, fresh output | Exit 0; OFFLINE_SMOKE_PASS |
| Isolated rollback validator, fresh output | Exit 0; OFFLINE_PERSISTENCE_PASS; release historical archive and deployed rollback NOT_VERIFIED |
| Frozen verifier, protected Git diff, whitespace and new relative links | Exit 0; protected data unchanged |

Regressions: [42 yield controls](../../tests/unit/test_useful_yield_repair.py),
[six overlap controls](../../tests/unit/test_workbench_overlap_safety.py), plus
existing specialist, adapter, security, operation-contract, frontend and golden
tests. Mocked positive chains remain explicitly offline controls, not fresh
article acquisition. Frozen benchmark fixtures/labels were not rebaselined.

One initial focused command referenced a nonexistent test filename and collected
no tests; the corrected command above and final full/fast runs passed. An early
Node log command reused one filename; all ten scripts were rerun with separate
logs. Neither instrumentation mistake is counted as a test pass.

## Remaining work and handoff

The most limited outputs remain Trending (one fresh qualified source) and
Personal Watch (one historical statement). More discovered/readable pages do
not establish task-relevant fresh evidence. Prioritize the recorded rejected
source/date/attribution boundaries and held-out subjects, not larger counters
or another provider catalog. BrandShield now retains more relevant native
reporting, but allegations, preventive guidance and historical enforcement must
remain distinct from observed current attacker infrastructure. Scout's longer
report includes historical and forecast context; financial claim adjudication
and period/currency reconciliation remain separate acceptance gates.

The four-case batch plus separate post-fix case are complete. Earlier in this
continuation another four-case batch and one language-postfix Dyson run were
performed; their measurements/fingerprints remain in the prior-cycle summary.
**Ten fresh local investigations total in this continuation, zero model calls**;
no silent batch retries or provider sweep. No new live calls were made for
measurement compilation or browser replay.

Full native responses, SSE, temporary dossiers, logs and screenshots are in
system-temp basename `aegis-useful-yield-648b5eb59537470ea08558920b838c3a` and may
expire; selected sanitized evidence is durable here. The original archive's
55 malformed dossiers was not repaired or overwritten. Independent accuracy,
full expanded-source live coverage, production parity, hosted CI and deployed
rollback remain unverified. See the [continuation handoff](../handoffs/2026-10-25_USEFUL_EVIDENCE_EXPANSION.md).
