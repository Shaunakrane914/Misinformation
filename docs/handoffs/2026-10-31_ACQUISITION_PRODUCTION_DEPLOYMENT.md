# Production Acquisition Deployment — 2026-10-31

**Production integration of validated acquisition repairs directly onto canonical `main` (`ced963e`).**

## 1. Verified Architecture & Safe Scope

Following forensic verification against current `main`, 5 of 8 proposed regression fixes were established as ALREADY_FIXED_ON_MAIN (REG-01, REG-07, REG-08), POLICY_UNSAFE (REG-03 header spoofing), or DUPLICATE_IMPLEMENTATION (REG-04 secondary adapter bypass). The unproven 29.89× improvement factor and 100% full-text extraction claims were formally retracted in compliance with Aegis telemetry rules.

The 3 genuine, non-duplicative, policy-safe enhancements were ported to clean `main`:

1. **Foreign ADR SEC EDGAR Planning** (`backend/services/agent_reach/source_planner.py`):
   - Dual-listed ADR entities (e.g., Infosys `INFY` / `0001065837`, Tata Motors `TTM` / `0000926042`) now evaluate `resolve_cik(target)` during planning.
   - Prevents `_looks_indian(target)` from blanket-blocking SEC EDGAR regulatory filing retrieval for foreign issuers dual-listed on US exchanges.
2. **Native Spoken YouTube Transcript Enrichment** (`backend/infrastructure/acquisition/routing/router.py`):
   - Enriches `NativeRouter.execute_channel_read()` for YouTube URLs by dispatching to `self.executor.execute_youtube_transcript()`.
   - Replaces metadata-only summaries (title + short description) with actual spoken dialogue when available, falling back safely to description if transcript extraction is unavailable or uncaptioned.
3. **Technical Domain GitHub Retention** (`backend/services/agent_reach/source_planner.py`):
   - Retains `github` channel in planned actions for technical targets (queries mentioning code, repo, framework, library, sdk, commit, release).
   - Prevents `QueryPlanningStage` in `backend/services/acquisition.py` from dropping repository-oriented technical queries.

## 2. Empirical Verification & Evidence

All validations executed in an isolated worktree tracking `origin/main` (`ced963e`):

- **Dedicated Regression Suite**: `tests/unit/test_regression_fixes_20261031.py` created with 3 unit tests verifying ADR SEC planning, technical GitHub retention, and YouTube transcript enrichment: **3/3 passed** (0.50s).
- **Core Unit Suites**: `tests/unit/test_source_planning_engine.py`, `tests/unit/test_phase8d_source_expansion.py`, `tests/unit/test_recovered_operation_routes.py`: **64/64 passed** (2.70s).
- **Chaos & Security Suites**: `tests/chaos` and `tests/security`: **100/100 passed** (2.59s).
- **Release-Candidate Smoke**: `scripts/validate_release_candidate_smoke.py`: **OFFLINE_SMOKE_PASS** (zero errors).
- **Rollback Compatibility**: `scripts/validate_rollback_compatibility.py`: **OFFLINE_PERSISTENCE_PASS**.
- **Static Analysis**: `flake8` zero errors (`--select=E9,F63,F7,F82`).
- **Data Invariants**: Frozen retrieval benchmarks (`tests/retrieval_benchmark/*`) and historical dossiers (`backend/data/dossiers/*`) preserved completely unmodified.

## 3. Publication

- Base commit: `ced963e00cf76dca3378fbdf39e5b2259eb2cfbe` (`origin/main`)
- Pushed directly to `origin/main` to trigger production deployment.
