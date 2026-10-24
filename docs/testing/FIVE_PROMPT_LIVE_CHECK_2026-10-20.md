# Five new local live prompts — 2026-10-20

## Decision

**Research-quality result: FAIL for this sample.** All five local HTTP/SSE
operations completed, but none produced useful current agent-specific intelligence.
Unilever produced one source-cited observation, but it is decades-old encyclopedia
history, not current financial research. This is a qualitative review of five
ad-hoc subjects, not a statistically random sample or independent accuracy score.

User requested five prompts and a report. **No application code, tests, access
flags, credentials or deployment settings were changed.** Existing dirty changes
were preserved. No commit, push, merge, deployment or live AI call. This does not
invalidate the earlier Adobe article demonstration; it shows poor generalization.

## Scope

Worktree `.scratch/phase9-remediation-20261016`, branch
`fix/p0-lenovo-acquisition-20261018`, HEAD
`39a514b68388450bbc5e6061aba97bda2077fc7f` plus existing dirty implementation.
Application fingerprint before/after all five cases is unchanged:
`fcce2eb9e8174b73f78ba553aff3f697389d6aa42e751a19a45c34f79f28e271`.

Exactly one normal local ASGI streaming request per input, sequentially, no
manually supplied URL, no audit retries. Real source acquisition, not replay.
Each has a 120-second research ceiling and at most six deep-reader attempts.
Internal search/provider fallbacks remain normally bounded; this is not a cap
of six total HTTP requests. Temporary SQLite/dossiers, no background ingestion
or external persistence/notifications. AI credentials excluded, mock LLM false.
All five approved requests are consumed, not permission for additional sweeps.

## Actual outputs

| Agent / input | Seconds | Captured records | Retained KB | Words | Displayed findings | Assessment |
| --- | ---: | ---: | ---: | ---: | ---: | --- |
| Scout / Samsung | 38.19 | 0 | 0 | 0 | 0 | ACQUISITION_FAILED; six unresolved publisher wrappers |
| Scout / Unilever | 29.14 | 4 | 18.934 | 3,069 | 1 | COMPLETED technically; historical Wikipedia paragraph, plus corporate homepages |
| BrandShield / Adidas | 36.40 | 2 | 19.551 | 3,002 | 0 | INSUFFICIENT_EVIDENCE; publisher homepages only, no threat evidence |
| Trending / grid-scale energy storage | 40.92 | 0 | 0 | 0 | 0 | INSUFFICIENT_EVIDENCE; five leads lack publication timestamps, no reads |
| Personal Watch / Sundar Pichai | 36.19 | 2 | 12.812 | 2,060 | 0 | INSUFFICIENT_EVIDENCE; publisher homepages only, no identity-abuse evidence |

KB = UTF-8 retained content bytes / 1,000, words = whitespace tokens. These
include noise/background and duplicates, not useful evidence volume. Unilever's
root URL with/without trailing slash produced the same 475-word body twice:
`02bb5a955e3ff08585e2f8bb7cdb9c1d9ec4f09d7ab11c05dc43bf771bd6b3d4`.
Four records therefore do not mean four unique documents or independent sources.

All five returned HTTP 200, a result event and no SSE error event. That establishes
route completion only. No browser or deployed frontend/backend was tested in this
turn. No independent adjudication of the source assertions was performed.

## Discovery funnel and first loss stage

| Input | Initial queries / execution records | Provider observations / responses | Initial normalized / cumulative accepted candidates | Reader attempts | Captures / structurally article-like / qualified | First measured failure or quality loss |
| --- | ---: | ---: | ---: | ---: | ---: | --- |
| Samsung | 13 / 16 | 61 / 50 | 13 / 16 | 6 | 0 / 0 / 0 | PUBLISHER_RESOLUTION |
| Unilever | 13 / 16 | 38 / 37 | 25 / 20 | 6 | 4 / 1 / 1 | No empty funnel boundary; history incorrectly satisfies useful-financial-output expectations |
| Adidas | 9 / 12 | 44 / 40 | 19 / 17 | 5 | 2 / 0 / 0 | PUBLISHER_RESOLUTION; captured hubs do not remedy missing articles |
| grid-scale energy storage | 12 / 14 | 90 / 83 | 5 / 0 | 0 | 0 / 0 / 0 | CANDIDATE_QUALIFICATION: missing timestamps |
| Sundar Pichai | 9 / 12 | 50 / 43 | 11 / 13 | 5 | 2 / 0 / 0 | PUBLISHER_RESOLUTION |

Initial normalized and cumulative accepted counters cover different phases;
accepted can exceed initial normalized after adaptive discoveries. These are
not comparable subset totals or deduplicated source counts. Provider observations
include nested URL-resolution searches and explicitly uninstrumented legacy
fallbacks. The **283 observed search/fallback attempts** are not 283 AI calls,
complete HTTP accounting or unique providers. Bing often returned irrelevant
results, Yahoo recorded HTTP 500, and legacy wrapper searches remained unresolved.
The volume is a search-efficiency concern despite bounded elapsed time.

## Confirmed defects / follow-up priorities

### P0 — Publisher URL resolution still fails on new subjects

Samsung found relevant headlines, including a Samsung earnings announcement, but
all six read attempts failed `PUBLISHER_UNRESOLVED`. Its body-reading stage took
about 8.81s, with roughly 38s end-to-end; this was not the entire 120s deadline
being consumed. Adidas and Sundar each had three unresolved article attempts,
followed by two successful publisher hub captures. Those hubs did not expose
accepted subject articles in the bounded link set.

Owner: [DeepReader._resolve_wrapper](../../backend/services/research/deep_reader.py),
the existing [search adapter chain](../../backend/infrastructure/acquisition/routing/router.py)
and [DeepReadingStage.run](../../backend/application/research/reading.py).
For Samsung, all six allowed attempts were spent on wrappers, leaving zero for
the observed publisher-hub fallback, which requires at least two remaining slots.
This is a selection/budget-allocation limitation as well as a provider-result
problem; it does not prove a hub would have contained the missing article.

### P1 — Financial usefulness gates admit old encyclopedia history

Unilever's sole finding is from Wikipedia and discusses events spanning
1954–1978. It is correctly cited and labeled UNVERIFIED, but unsuitable as the
leading answer to current financial intelligence. No primary filing was acquired.
The deterministic report brief repeats that historical paragraph because it
passes objective keywords such as acquisition/profits. The structural
`qualified_evidence: 1` counter is not independent truth, timeliness or usefulness.

Owners: [content roles/objectives](../../backend/services/research/content_roles.py),
[PassageExtractor](../../backend/services/research/passage_extractor.py),
[synthesis](../../backend/application/research/synthesis.py),
[_captured_observation_brief](../../backend/services/report_builder.py).
Preserve history as background, not a current finding. Do not invent current
dates or treat an undated capture as recently published.

### P1 — Missing discovery timestamp blocks reading that could establish it

The actual Trending rejection reason for all five leads is
`TEMPORAL_MISSING_TIMESTAMP`, **not proven staleness**. The normal news queries
do contain the new `when:2d` hint. Three native feed searches returned irrelevant
results; retained leads came through other discovery paths with empty timestamps.
No page was read to inspect publisher metadata. Rejected titles include a storage
deployment report, a construction announcement and validation/project reports;
their actual freshness/accessibility remains unknown without captured bodies.

Owners: [CandidateQualificationStage](../../backend/application/research/acquisition.py)
and [RelevanceGate / temporal guard](../../backend/services/research/relevance_gate.py).
A future fix should distinguish bounded **provisional read eligibility** from
eligibility for a current-trend finding. Do not relax the final freshness guard
or infer dates from “latest”, a URL, or the search hint.

### P1 — Subreddit routing uses substring matches

Read-only offline check reproduced:
`EntitySubredditResolver().resolve("Unilever")` → `automotive_ev` →
`teslamotors`, `electricvehicles`, `stocks`.
Actual live logs show those automotive subreddit RSS requests returning 429.
The resolver tests `"ev" in clean_q`, which matches inside **Unilever**.
Similar short-substring risks exist for `ai` and `car`.

Owner: [EntitySubredditResolver.resolve](../../backend/infrastructure/acquisition/resolution/social_resolver.py).
Use entity-linked sector/context and token-aware matches before spending source
requests. This is independent of Reddit's rate limit; changing the access flag
would not fix the wrong community choice. No access flag was changed here.

### P2 — Duplicate root documents inflate volume

Unilever's root with/without `/` survived as separate retained records with
identical body hashes. Review canonical URL identity across the
[research model](../../backend/services/research/research_models.py),
[independence ranking](../../backend/services/research/source_independence.py) and
[observed-hub fallback](../../backend/services/research/publisher_links.py).
Do not collapse genuinely distinct article paths or query variants indiscriminately.

## Validation and retained evidence

No implementation was made during this verification. Existing code rerun results:

- Full offline suite: **1,555 passed / 78.35s**, exit 0.
- Fast suite: **1,347 passed / 45.15s**, exit 0.
- Fatal flake8: zero findings, exit 0. All nine frontend Node scripts exit 0.
- Frozen benchmark verifier and protected-path diff exit 0.
- Release smoke exit 0, OFFLINE_SMOKE_PASS.
- Rollback exit 0, OFFLINE_PERSISTENCE_PASS; historical archive/deployed rollback
  remain NOT_VERIFIED. This does not recover the earlier malformed dossiers.
- Terminal runner and read-only funnel summarizer exit 0; unchanged application
  fingerprint. Existing dirty files, frozen data and historical evidence preserved.

Actual live command, portable form:

```text
python scripts/audits/run_terminal_agent_quality.py --allow-live --env-file <local-server-env> --output-dir <new-temp-directory> --case scout:Samsung --case scout:Unilever --case brandshield:Adidas --case "trending:grid-scale energy storage" --case "personal_watch:Sundar Pichai" --timeout-seconds 120 --max-deep-reads 6
```

No `--allow-live-ai` and no `--capture-from`. Full responses/events, isolated
dossiers and redacted logs are in system-temp tree
`aegis-five-prompts-fa296fd445534d3a8fea6aa6258171f3`; offline gate logs are in
the corresponding `-gates` sibling. Temp outputs may expire. Sanitized selected
[funnel/source hashes](evidence/2026-10-20_five_prompt_check/funnel.json) are durable;
no full native dossiers or credentials copied into documentation.

## Conclusion

The main remaining failure is still autonomous acquisition of **useful relevant
article bodies**, with additional premature timestamp qualification and downstream
historical-text usefulness defects. Frontend rendering was not tested here and
must not be blamed for empty native responses. Successful regressions/HTTP status
do not override these observed research-quality failures. No further live calls
or repairs were silently performed after the five requested cases.
