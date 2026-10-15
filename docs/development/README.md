# Local development and runtime guide

Maintained against `abe547f` on 2026-10-14. Start with [current state](../CURRENT_STATE.md), [latest handoff](../handoffs/README.md) and the [system guide](../SYSTEM_GUIDE.md). Phase 8 is not fully accepted or authorized for deployment.

## Select the correct checkout

Run these before installation or editing:

```text
git status --short --branch
git rev-parse HEAD
git worktree list
```

The original IDE checkout may be older than the independent-review worktree. Do not reset it, switch another agent's branch, or copy implementation files between worktrees. An editable Python install can point at a different checkout; run commands from the intended repository root and use its virtual environment. Tests set the repository import path; live audit runners also verify their source checkout.

## Install

[pyproject.toml](../../pyproject.toml) declares Python >=3.11; [.python-version](../../.python-version) selects 3.11 and [CI](../../.github/workflows/ci.yml) tests 3.11/3.12/3.13. Use an interpreter compatible with the actual dependency set, not a claim that every future Python version is supported. Node is needed for frontend regression scripts, not a frontend build. Git is required by the pinned upstream dependency.

```text
python -m venv .venv
```

Activate with `./.venv/Scripts/Activate.ps1` in PowerShell or `source .venv/bin/activate` in POSIX shells. Then:

```text
python -m pip install -r requirements.txt
python -m pip install -e ".[test]"
```

Dependencies mostly have minimum-version constraints, not a complete lockfile. The Agent Reach dependency is pinned to a Git commit. Installing successfully does not prove optional tools, providers, or model identifiers are available.

## Configuration

Use [environment setup](ENV_SETUP.md) and the [configuration matrix](../operations/PRODUCTION_CONFIGURATION_MATRIX.md). Copy `.env.example` to `.env` only if the destination does not already exist; preserve existing settings and never print keys.

No Supabase server credentials selects **persistent file-backed SQLite**, not an in-memory demonstration store. Missing LLM credentials do **not** automatically authorize synthetic outputs. Tests explicitly isolate persistence/network and authorize mocks. `ENVIRONMENT=production` forbids `AEGIS_MOCK_LLM=true`.

For experimental local runs, point `SQLITE_DB_PATH` and `AEGIS_DOSSIER_DIR` to new scratch locations and disable background RSS if it is not needed. Never use protected historical dossiers as test output.

## Start locally

From this worktree root:

```text
python -m uvicorn backend.main:app --host 127.0.0.1 --port 8000 --reload
```

This serves both API and frontend. Open `http://127.0.0.1:8000/`, `/docs`, `/openapi.json`, `/api/healthz` and `/api/readyz`. The [current route map](../api/CURRENT_ENDPOINTS.md) lists specialist endpoints.

The compatibility entrypoint `python main.py` also starts the application, may choose an alternate port, writes `port.txt`, and binds to all interfaces. Prefer the explicit loopback command for local-only development. Uvicorn command-line host/port settings are explicit; do not assume arbitrary `HOST` or `PORT` environment variables override them.

A standalone `python -m http.server --directory frontend` serves static assets only. Its `/api` requests cannot validate backend integration. Browser result replays are a separately labeled test mode.

## Validate and change safely

Follow the [testing runbook](../testing/README.md). Full suite, fast suite, fatal lint, seven current Node scripts, frozen hashes, smoke and rollback readers have different scopes. Counts are discovered, not fixed to 530 or another old milestone.

Canonical acquisition lives in `backend/infrastructure/acquisition/`; research orchestration in `backend/application/research/`; specialist implementations in `backend/agents/<agent>/`. Old facades are compatibility contracts, not disposable duplicates. See [current code map](CURRENT_CODE_MAP.md).

Use a dedicated branch/worktree; inspect the relevant diff, preserve unrelated work, add regression evidence, and leave a dated handoff. Do not commit or push another agent's changes. No merge or deployment is implied by a local change.

## CI

The active [workflow](../../.github/workflows/ci.yml) runs on pushes and pull requests across branches plus manual dispatch: fatal lint/frontend/frozen checks, three fast-suite Python jobs, and one full-suite/persistence/smoke job. The old seven-job YAML under this documentation tree is **not** the active workflow; do not copy it over production CI.

[CI coverage](../testing/CI_COVERAGE_MATRIX.md) and [exact checked CI](../handoffs/2026-10-14_PHASE8_INDEPENDENT_CI_CLOSEOUT.md) separate configuration from observed outcomes. CI does not run live-provider, browser or screen-reader acceptance.
