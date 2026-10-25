# Expansion safety and release integration handoff — 2026-10-24

## Start here

Later continuation: [four newly authorized live retests](2026-10-24_EXPANSION_LIVE_RETEST.md).
The earlier pending-permission and validation statements below are historical.

User authorized fixing the expansion review issues and repeating tests. Read the
[detailed repair report](../testing/EXPANSION_SAFETY_AND_RELEASE_INTEGRATION_2026-10-24.md).
**Local code repaired; fresh expansion live acceptance and20× useful evidence
are NOT VERIFIED. No commit, push, merge or deployment performed.**

Preserve both dirty worktrees. Original branch/base:
`feat/phase8-real-acquisition-proof` /
`1e1c44e89ff635974150770d5d4cea1e9c9fb19e`.
Release target:
`release/specialist-task-20261024` /
`1a90d681361b8e027a12feb88266932a5cb5d1d1`, in
`.scratch/phase9-remediation-20261016` relative to the original checkout.
Do not replace the current release service/router with the older original copies.

## Changes and rationale

- Repaired optional async transport backend, off-loop DNS, numeric socket pinning,
  total deadlines, mixed-case/client credential stripping, bounded decoding,
  loop-local clients and bounded per-domain reservations.
- Added a shared fail-closed adapter boundary. Reddit access flag, SEC declared
  contact and FactCheck credential requirements apply to direct adapter calls too.
  No access settings or credentials were changed.
- Fixed tuple truthiness, irrelevant-result filling, fake empty body/header
  success, guessed consumer domains, abstract/profile/article classification,
  syndicated-feed reads and unsupported verified-review labels.
- Connected repaired new modules through the service, native dispatch and URL
  reader. Release harvest planning uses one existing optional discovery slot.
  External publisher URLs observed in feeds/APIs remain leads for the normal
  secure reader, not evidence owned by the discovery adapter.
- Retained existing canonical16 operation routes and current SEC/arXiv/Reddit/HN/
  ClaimReview paths. No paid reader or new provider was introduced.
- Replaced misleading evaluation mechanics: raw body counts, selected frontend
  passages and synthetic scheduler performance now have separate meanings.
  The optional async helper is not the normal synchronous worker pipeline.
- New regressions are in
  [test_expansion_safety_and_wiring.py](../../tests/unit/test_expansion_safety_and_wiring.py);
  adapter fixtures and async tests are under `tests/unit/test_*adapter.py` and
  `test_async_http_transport.py`. Positive fixtures use scoped synthetic DNS and
  test-only configuration, with live network still blocked.
- Existing evidence-workbench/frontend changes remain intact. Original checkout
  needed the release's pure shared HTML extraction helper as a new module;
  no older extraction implementation replaced the release helper.

## Commands actually run and final results

Counts are per checkout; the fast suite overlaps the full suite. Do not add them.

| Gate | Original checkout | Current release |
| --- | --- | --- |
| `python -m pytest tests/ -q --tb=short` | exit0;1,063 passed /30.05s | exit0;2,292 passed /39.75s |
| `python -m pytest tests/unit tests/chaos tests/security -q --tb=short` | exit0;867 passed /14.01s | exit0;2,084 passed /32.88s |
| Fatal flake8 E9/F63/F7/F82 | exit0; zero | exit0; zero |
| Each Node `tests/frontend/test_*.js` |2 scripts, exit0 each |10 scripts, exit0 each |
| Frozen benchmark verifier | exit0 | exit0 |
| Protected `git diff --exit-code HEAD` | exit0 | exit0 |
| Release smoke, fresh report | exit0; OFFLINE_SMOKE_PASS | exit0; OFFLINE_SMOKE_PASS |
| Default rollback validator, fresh report | exit1; HISTORICAL_ARCHIVE_FAIL | exit0; OFFLINE_PERSISTENCE_PASS |
| Browser saved-response replay | not run in older frontend | exit0;12 states at320/390/1440px |
| `git diff --check` |3 pre-existing EOF-blank warnings | exit0 |

Original historical archive inspection:11 sealed records,2,445 legacy unsealed
records and55 failed JSON files. Release archive is empty and NOT_VERIFIED.
Its persistence pass does not establish archive recovery or deployed rollback.
Protected files were read only and not repaired.

Smoke/rollback were repeated after code stabilization with fresh output filenames;
see the durable [validation summary](../testing/evidence/2026-10-24_expansion_repair/validation.json).
Earlier full-suite failures exposed the audit probe catalogue's missing route,
a required failure endpoint and a missing bounded-decoder import; those defects
were repaired. Their logs remain separate from passing final runs.

Raw temporary logs are under the system-temp basename
`aegis-expansion-repair-b155c7789a4a4c9bba8d13b083059f50`.
Final suite logs are `full-verified-{0,1}.log`,
`fast-verified-{0,1}.log` (0 original,1 release). Temporary logs may expire.
Browser screenshots/measurements are in its `browser-replay` subdirectory.
No private reasoning transcript or reconstructed raw execution transcript is claimed.

## Acceptance boundaries and next actions

1. Keep AI disabled in normal tests. This repair made zero model calls.
2. Fresh bounded four-case live-retest permission was requested but no new
   authorization was received during this repair. Earlier four-case permissions
   are consumed. Do not silently rerun providers or treat saved replay as live.
3. Under a fresh agreed budget, run the existing terminal audit in the release
   checkout using normal queries, inspect first loss and selected passages, then
   check those exact responses in the frontend. Do not mix manually fetched
   reference pages into each agent's output.
4. Previous saved-response measurements still show selected word counts of
   Scout6,948, BrandShield792, Trending0 and Personal Watch0. They are **before**
   this repair. Independent usefulness/accuracy and20× growth are not proven.
5. Do not treat source registration, HTTP200, test count or a longer buffer as
   source availability/relevance/independence/virality. Canonical qualification
   and security controls remain mandatory.
6. Preserve historical corruption for a separately scoped recovery assessment.
   Production parity, hosted CI, previous-version deployment rollback and full
   accessibility acceptance remain unverified.
7. Review and checkpoint the intended release diff before any separately
   authorized publish. No Git index changes or remote mutations were made here.
