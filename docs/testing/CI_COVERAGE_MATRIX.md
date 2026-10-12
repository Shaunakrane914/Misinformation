# CI coverage and evidence

The authoritative executable configuration is [`.github/workflows/ci.yml`](../../.github/workflows/ci.yml), not a proposed workflow copied into documentation. It triggers for pushes and pull requests on all branches, plus manual dispatch. This document describes configured gates; it is not evidence that a remote run has passed.

| Active job | Interpreter | Actual gate |
|---|---|---|
| `code-quality` | Python 3.12 / Node 20 | Fatal lint scoped to `backend tests scripts`; every `tests/frontend/test_*.js`; pinned frozen benchmark hashes |
| `unit-and-chaos-matrix` | Python 3.11, 3.12, 3.13 | `pytest tests/unit tests/chaos tests/security -q` |
| `full-offline-regression` | Python 3.12 | `pytest tests/ -q`, isolated offline smoke, fresh-process persistence and historical-reader compatibility |

Each test job subsequently checks frozen dataset hashes and `git diff --exit-code -- tests/retrieval_benchmark artifacts research`, including after failures. Frozen hashes normalize only CRLF/LF so Git checkout on Windows cannot create a false mismatch. Changes to scenarios, candidates or labels remain prohibited.

The full suite includes integration, contracts, retrieval benchmarks, evaluation, performance benchmarks and root test modules. Counts change as regressions are added; use `pytest tests/ --collect-only -q` for the current inventory. Historical Phase 7.1 totals are not current acceptance evidence.

## Offline isolation

[`tests/conftest.py`](../../tests/conftest.py) sets test mode, temporary SQLite and dossier directories, blank provider credentials and disabled background RSS before importing the application. Every test resets claims, evidence, hash indexes, research, replay caches and runtime observations. Actual socket connections are blocked; the standard-library socketpair exemption exists only for Windows asyncio's internal self-pipe. Mocked transport contracts remain available.

The release smoke and rollback validators use new subprocesses and temporary persistence. They explicitly report `OFFLINE_REGRESSION`, not live scraping success or deployment readiness. Optional `--output` creates a new report exclusively and refuses to overwrite existing audit artifacts.

## Exclusions and limitations

- `tests/smoke_test_social_production.py` is a manually authorized live probe, not an offline test.
- Live scraping probes and staging load tests are not CI acceptance gates.
- A historical rollback reader uses the locally available baseline commit; an unavailable baseline is `NOT_VERIFIED`, never an assumed pass.
- A full deployed earlier-version rollback remains `NOT_VERIFIED` until exercised by the owner in staging.
- Workflow editing is local implementation, not a successful GitHub Actions run. Record the actual commit and run URL after pushing with appropriate credentials; no push is performed by these changes.
- The rollback command intentionally exits nonzero while the 55 protected malformed dossiers remain. A red hosted rollback gate is an honest release block, not a reason to skip the archive or weaken validation.
