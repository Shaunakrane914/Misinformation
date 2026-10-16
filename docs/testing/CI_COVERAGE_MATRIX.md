# CI coverage and evidence

The authoritative executable configuration is [`.github/workflows/ci.yml`](../../.github/workflows/ci.yml), not a proposed workflow copied into documentation. It triggers for pushes and pull requests on all branches, plus manual dispatch. This document describes configured gates; it is not evidence that a remote run has passed.

Latest published remediation evidence: exact `084aae3` passed all five jobs in [run 38933423125](https://github.com/Shaunakrane914/Misinformation/actions/runs/38933423125). See the [Phase 9 verification report](PHASE9_REMEDIATION_VERIFICATION_2026-10-16.md) and [CI closeout](../handoffs/2026-10-16_PHASE9_REMEDIATION_CI_CLOSEOUT.md) for the 1,285/1,077 local counts and separate **FAIL** research-quality gate. Live providers, screenshots and source-adjudicated accuracy replays remain outside hosted CI acceptance; no deployment is authorized.

| Active job | Interpreter | Actual gate |
|---|---|---|
| `code-quality` | Python 3.12 / Node 20 | Fatal lint scoped to `backend tests scripts`; every `tests/frontend/test_*.js`; pinned frozen benchmark hashes |
| `unit-and-chaos-matrix` | Python 3.11, 3.12, 3.13 | `pytest tests/unit tests/chaos tests/security -q` |
| `full-offline-regression` | Python 3.12 | `pytest tests/ -q`, isolated offline smoke, fresh-process persistence and historical-reader compatibility |

Each test job subsequently checks frozen dataset hashes and `git diff --exit-code -- tests/retrieval_benchmark artifacts research`, including after failures. Frozen hashes normalize only CRLF/LF so Git checkout on Windows cannot create a false mismatch. Changes to scenarios, candidates or labels remain prohibited.

The full suite includes integration, contracts, retrieval benchmarks, evaluation, performance benchmarks and root test modules. Counts change as regressions are added; use `pytest tests/ --collect-only -q` for the current inventory. Historical Phase 7.1 totals are not current acceptance evidence.

Current independent-review evidence is recorded in the [2026-10-14 CI closeout](../handoffs/2026-10-14_PHASE8_INDEPENDENT_CI_CLOSEOUT.md). Its 1,156/948 local counts and new negative controls are separate from historical branch evidence. Browser/live probes are local append-only observations, not hosted workflow coverage.

The historical exact-commit evidence for the earlier extraction branch is [run 38420523255](https://github.com/Shaunakrane914/Misinformation/actions/runs/38420523255)
at `e74b9847ab107e2793f69e2155914028f02391b6`: all five configured
jobs passed, including Python 3.11–3.13 fast suites and the full offline
regression. The 1,051/855 counts were historical local observations, superseded by the [dated current state](../CURRENT_STATE.md). The runner does not contain ignored historical dossier
JSON, so archive integrity and deployed rollback remain `NOT_VERIFIED`.
This workflow does not run live scraping, Playwright rendering, axe-core or
manual screen-reader checks. Earlier [Phase 7.4 run 38236691625](https://github.com/Shaunakrane914/Misinformation/actions/runs/38236691625)
is retained as a historical checkpoint, not current branch acceptance.

## Offline isolation

[`tests/conftest.py`](../../tests/conftest.py) sets test mode, temporary SQLite and dossier directories, blank provider credentials and disabled background RSS before importing the application. Every test resets claims, evidence, hash indexes, research, replay caches and runtime observations. Actual socket connections are blocked; the standard-library socketpair exemption exists only for Windows asyncio's internal self-pipe. Mocked transport contracts remain available.

The release smoke and rollback validators use new subprocesses and temporary persistence. They explicitly report `OFFLINE_REGRESSION`, not live scraping success or deployment readiness. Optional `--output` creates a new report exclusively and refuses to overwrite existing audit artifacts.

## Exclusions and limitations

- `tests/smoke_test_social_production.py` is a manually authorized live probe, not an offline test.
- Live scraping probes and staging load tests are not CI acceptance gates.
- A historical rollback reader uses the locally available baseline commit; an unavailable baseline is `NOT_VERIFIED`, never an assumed pass.
- A full deployed earlier-version rollback remains `NOT_VERIFIED` until exercised by the owner in staging.
- Workflow editing alone is not GitHub Actions evidence. Preserve the exact commit, run URL and job conclusions; the hosted Phase 7.4 evidence is linked above.
- The original local archive inventory found 55 malformed protected dossiers.
  Where those files are present, rollback validation must report their actual
  state and may exit nonzero. In isolated worktrees and hosted CI the ignored
  archive may be absent; a passing temporary-persistence check does not verify
  or repair it.
