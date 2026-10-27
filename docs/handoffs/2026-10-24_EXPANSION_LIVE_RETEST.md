# Four-case expansion live retest handoff — 2026-10-24

## State and authorization

The user approved four bounded retests after the expansion repair:
Scout/Adobe, BrandShield/Dyson, Trending/battery recycling and Personal Watch/Mary
Barra. **All four ran once; permission is consumed.** Limits:240 seconds,24 reader
attempts and120 native HTTP admissions per case. AI/paid readers disabled.
No audit POST retry, deployment, commit, push, merge or production mutation.

Release checkout `.scratch/phase9-remediation-20261016`, branch
`release/specialist-task-20261024`, HEAD
`1a90d681361b8e027a12feb88266932a5cb5d1d1` plus preserved dirty work.
[Detailed findings](../testing/EXPANSION_FOUR_CASE_LIVE_RETEST_2026-10-24.md)
and [durable measurements](../testing/evidence/2026-10-24_expansion_live_retest/measurements.json)
separate the live batch from the later offline correction.

## Outcome

| Case | Raw acquired article words | Qualified sources | Published words |
| --- | ---: | ---: | ---: |
| Adobe |16,254|13|6,484|
| Dyson |7,656|4|774|
| battery recycling |9,596|0|0|
| Mary Barra |484|0|0|

Live selected-word counts did not improve over the preceding sample.20× is not
demonstrated. Each local HTTP request returned200/result and no SSE error;
that is transport completion, not four research-quality passes. Native HTTP
admissions80/82/88/74 are partial network accounting, not total provider requests.

Yahoo discovery now has a traceable positive result:3 leads, one actual acquired
article surviving qualification/publication. Newswire/Substack returned zero
matches in these cases; Bluesky failed explicitly. Do not claim all new
adapters are live-productive from registration or tests.

## Offline repair triggered by the fresh observation

Trending actually acquired a fresh374-word ESS News article with substantive
recycling-of-batteries text. Passage selection rejected it because literal
`battery` did not match `batteries`. The runtime resolver's generic phrases use
`general`, which must be covered alongside `topic`.

A small current-release-only change in
[PassageExtractor](../../.scratch/phase9-remediation-20261016/backend/services/research/passage_extractor.py) handles
regular consonant-`ies` plurals for Trending topic-like profiles. It preserves
the overlap threshold, exact source text/offsets, temporal/depth/security checks,
and named-person/company matching. No article URL/body or special case for the
live subject is embedded in production code.

[Eight regressions](../../.scratch/phase9-remediation-20261016/tests/unit/test_topic_plural_passages.py) cover varied
topics, the actual request classifier, wrong topics, dates, snippets and names.
Two initial positive controls failed before the change. The first topic-only
attempt still yielded zero on genuine replay; the actual generic-profile path
is now explicitly tested.

At fixed reference time2026-10-24T12:32:40Z, requalifying the same saved source
pool produced0 →1 qualified source and one exact56-word passage. Input and
original-pool hashes match. **No fifth live case or corrected native report was
created.** This is offline requalification, not live post-fix acceptance or a
verified factual finding. The twelve browser checks used original live reports.

## Commands and actual validation

Live command, run once from release checkout:

```text
python scripts/audits/run_terminal_agent_quality.py --allow-live --env-file <server-env> --output-dir <fresh-temp>/live --case scout:Adobe --case brandshield:Dyson --case "trending:battery recycling" --case "personal_watch:Mary Barra" --research-profile DEEP --timeout-seconds 240 --max-deep-reads 24 --max-http-admissions 120
```

Do not reuse that as permission for another batch. No `--allow-live-ai` flag.
The normal routes used isolated SQLite/dossier storage and no lifespan ingestion.

| Gate after offline code correction | Actual result |
| --- | --- |
| `python -m pytest tests/ -q --tb=short` | exit0;2,300 passed /51.62s |
| `python -m pytest tests/unit tests/chaos tests/security -q --tb=short` | exit0;2,092 passed /38.29s |
| Fatal flake8 E9/F63/F7/F82 | exit0; zero |
| Each Node frontend script | ten scripts; exit0 each |
| Frozen verifier / protected Git diff / whitespace | exit0 |
| New-temp smoke / rollback validators | exit0 each; offline persistence only; empty release archive NOT_VERIFIED |
| Four exact reports in Chromium shared renderer |12 states320/390/1440px; exit0 |
| Fixed-time raw-pool requalification before/after | exit0 each; no new requests/models |

Live application fingerprint stayed
`d6916d41e5716e178d56a31cb5c642bf4f66f152452c3d376e665b3bd74a449e`.
After the later offline passage fix it is
`6d40a218574cdc66bdaa112a0f311d9d5ea6836d79869d3f20fa68b6f79226d8`.
Do not describe the live batch as running the later fix.

Raw responses, events, temporary dossiers, logs and browser images are under
system-temp basename
`aegis-expansion-live-retest-09b70d0d441741e1af4a1a3d4e2aa899`.
Selected sanitized measurements are durable; temp files can expire. No raw
transcript or private reasoning trace is claimed. Two ad hoc summary commands
failed on wrong JSON shape/encoding assumptions; raw results were not altered
and corrected summaries were generated from the saved files.

## Resume safely

- Preserve existing dirty changes in both worktrees; only the current release
  application received the passage fix. Original checkout application tests
  were not relabeled as a fresh rerun.
- Personal Watch still lacks a usable specialist passage. Examine its saved
 1,143-word Economic Times unclassified capture and publisher-resolution records
  before any new requests. One acquired2021 article and a homepage do not prove
  identity-threat or quotation investigations.
- Trending host expansion still spends reads on stale/tangential pages. Improve
  selection from saved captures rather than weakening freshness/relevance or
  making repeated live calls.
- Further live post-fix verification needs a fresh agreed bounded scope. No AI
  calls are justified by these deterministic defects.
- Historical55 malformed dossiers remain untouched. Empty-release rollback is
  not original-archive recovery, hosted CI or deployed rollback.
- No hosted CI, production parity, full accessibility or independent
  research-accuracy acceptance was performed.20× useful evidence remains unmet.
