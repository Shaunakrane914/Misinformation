# Aegis Protocol — Phased Architectural Refactoring & Migration Plan

**Status:** Authoritative Migration Roadmap (Phase 0)  
**Date:** October 9, 2026  
**Audited Baseline Commit:** `b441250f65c77256fad0dc222fc02ad55fdc9995`  
**Repository Scope:** `ShaunakRane914/Misinformation`

---

## 1. Migration Overview & Operating Rules

This document details the multi-phase engineering plan to transform Aegis Protocol into a robust, maintainable modular monolith.

### Non-Negotiable Operating Invariants
1. **Never Move Hundreds of Files in One Commit**: Each phase has an isolated commit boundary, focused pull request, and independent test gate.
2. **Preserve Public API Contracts**: All existing REST routes (`/api/claims`, `/api/agents/*`, `/api/healthz`, `/api/replay/*`), response schemas, and evidence provenance fields must remain backwards-compatible.
3. **No Synthetic Mock Shortcuts**: Benchmark datasets (`tests/retrieval_benchmark/`) and evaluation metrics must never be altered to fake compliance.
4. **Behavioral Regression Gate**: Every refactoring change must pass the full 528-test suite before merging.
5. **Fail-Safe Rollback**: Every phase includes an explicit rollback procedure.

---

## 2. Phased Migration Execution Matrix

| Phase | Title | Priority | Core Objective | Acceptance Gate |
| :---: | :--- | :---: | :--- | :--- |
| **0** | **Baseline, Containment & Architecture Blueprints** | **P0** | Add `.dockerignore`, author ADRs, map dependencies, freeze baseline test metrics. | **DELIVERED** (Commit `47ac9d1`) |
| **1** | **Documentation Source of Truth & Drift Reconciliation** | **P1** | Consolidate `docs/`, reconcile test counts (530 tests), archive stale audit plans. | **DELIVERED** (Commit `ba210c3`) |
| **2** | **Build, Packaging & CI Test Suite Hygiene** | **P1** | Add `pyproject.toml`, lock dependency strategies, expand CI to 7 parallel jobs. | **DELIVERED** |
| **3** | **Shared Acquisition Runtime Refactor** | **P0** | Fix duplicate `retrieve()`, decompose 1,706-line `router.py` into modular adapters. | `agent_reach_service` contract tests pass; all 14 channel adapters verified. |
| **4** | **Research Pipeline Decomposition** | **P1** | Break 581-line `investigate()` into 10 composable pipeline stages. | Investigation pipeline passes with bit-for-bit dossier equality. |
| **5** | **Domain Agent Modularization** | **P1** | Relocate agent-specific extraction from `agent_reach/` into owning agent packages. | BrandShield, Trending, Scout, Personal Watch contract tests pass. |
| **6** | **Centralized LLM Gateway & Validated Settings** | **P2** | Unify Gemini/mock LLM calls behind `LLMGateway`; adopt Pydantic `BaseSettings`. | Zero ad-hoc `os.getenv` in business logic; 100% deterministic offline mock tests. |
| **7** | **Legacy Deprecation & Final Cleanup** | **P2** | Retire compatibility shims, archive dead code, verify final clean directory tree. | Zero unused shims; clean build context; 100% regression pass. |

---

## 3. Detailed Phase Specifications

### Phase 0: Baseline, Containment & Architecture Blueprints (Current Phase)
- **Status:** **IN PROGRESS (DELIVERED)**
- **Priority:** P0 (Critical Security & Architecture Hygiene)
- **Files Affected:**
  - Added: [`.dockerignore`](file:///c:/Users/Shaunak%20Rane/Desktop/Projects/Misinformation/.dockerignore)
  - Added: [`docs/architecture/CODEBASE_INVENTORY.md`](file:///c:/Users/Shaunak%20Rane/Desktop/Projects/Misinformation/docs/architecture/CODEBASE_INVENTORY.md)
  - Added: [`docs/architecture/TARGET_ARCHITECTURE.md`](file:///c:/Users/Shaunak%20Rane/Desktop/Projects/Misinformation/docs/architecture/TARGET_ARCHITECTURE.md)
  - Added: [`docs/architecture/DEPENDENCY_MAP.md`](file:///c:/Users/Shaunak%20Rane/Desktop/Projects/Misinformation/docs/architecture/DEPENDENCY_MAP.md)
  - Added: [`docs/architecture/MIGRATION_PLAN.md`](file:///c:/Users/Shaunak%20Rane/Desktop/Projects/Misinformation/docs/architecture/MIGRATION_PLAN.md)
  - Added: [`docs/architecture/adr/`](file:///c:/Users/Shaunak%20Rane/Desktop/Projects/Misinformation/docs/architecture/adr/) (ADRs 0000 through 0005)
  - Added: [`scripts/run_live_retrieval_quality_evaluation.py`](file:///c:/Users/Shaunak%20Rane/Desktop/Projects/Misinformation/scripts/run_live_retrieval_quality_evaluation.py)
  - Updated: [`artifacts/retrieval_benchmark/retrieval_quality_report.md`](file:///c:/Users/Shaunak%20Rane/Desktop/Projects/Misinformation/artifacts/retrieval_benchmark/retrieval_quality_report.md)
- **Acceptance Criteria:**
  1. Docker build context ignores `.env`, `research/` (338 MB), `docs/visual-audit/` (31 MB), and `aegis_local.db` (17.6 MB).
  2. Full test suite independently verified at 528 passed tests.
  3. Historical 141-label narrative count mathematically corrected.
  4. ADRs 0001–0005 accepted and committed.
- **Rollback:** `git checkout HEAD~1 -- .dockerignore docs/architecture/`

---

### Phase 1: Documentation Source of Truth & Drift Reconciliation
- **Status:** **DELIVERED** (Commit `ba210c3`)
- **Priority:** P1
- **Current State:** Competing architecture documents (`ARCHITECTURE.md` vs `docs/ARCHITECTURE.md` vs `docs/audit/ARCHITECTURE_REVIEW.md`). Stale references claim `main.py` is >2,100 lines (now 308) and test count is 180 (now 530).
- **Target State:**
  - Root `README.md` becomes a lean entrypoint pointing to canonical documentation in `docs/`.
  - Stale audit documents in `docs/audit/` marked with `[SUPERSEDED]` headers.
  - Root `ARCHITECTURE.md` symlinked or consolidated into `docs/architecture/TARGET_ARCHITECTURE.md`.
- **Files Affected:**
  - `README.md`, `ARCHITECTURE.md`, `docs/ARCHITECTURE.md`, `docs/TESTING.md`, `docs/FEATURE_STATUS.md`, `docs/audit/*`.
- **Tests Required:** Markdown link validator (`pytest tests/test_unified_report.py`).
- **Acceptance Criteria:** Zero conflicting metrics; documentation accurately reflects measured 530 passing tests and current codebase topology.

---

### Phase 2: Build, Packaging & CI Test Suite Hygiene
- **Status:** **DELIVERED**
- **Priority:** P1
- **Current State:** `.github/workflows/ci.yml` runs only a subset of tests, executing `pytest tests/unit/ tests/chaos/ tests/security/` and 2 integration files. It completely skips the 6 critical root-level benchmark and verification suites:
  1. `tests/test_retrieval_benchmark.py` (104 scenario benchmark evaluation)
  2. `tests/test_retrieval_metrics.py` (MRR, nDCG@5, Precision@3, Hard-negative avoidance math)
  3. `tests/test_trending_temporal_guard.py` (48-hour freshness & timestamp decoupling)
  4. `tests/test_semantic_reranker.py` (Deterministic linear vs CrossEncoder benchmark)
  5. `tests/test_retrieval_quality_hardening.py` (Adversarial distractor & edge case suite)
  6. `tests/test_complete_retrieval_audit_integrity.py` (Audit schema & provenance invariant tests)
  Additionally, dependencies in `requirements.txt` use unpinned `>=` versions with no `pyproject.toml` or committed lockfile.
- **Target State:**
  - Add root `pyproject.toml` establishing standard packaging metadata and optional dependency groups (`test`, `evaluation`, `dev`).
  - Restructure `.github/workflows/ci.yml` into 7 small, independent, parallelized jobs:
    1. **`lint-format`**: Code style and static analysis (`ruff` / `flake8`).
    2. **`fast-unit-chaos`**: Fast offline tests (`tests/unit/`, `tests/chaos/`).
    3. **`security-invariants`**: Security, SSRF checks, and ledger integrity (`tests/security/`, `test_complete_retrieval_audit_integrity.py`).
    4. **`integration`**: API route and database integration tests (`tests/integration/`).
    5. **`offline-retrieval-benchmark`**: All 6 root benchmark and temporal guard suites.
    6. **`docs-validation`**: Markdown link consistency and OpenAPI schema generation test.
    7. **`live-retrieval-eval`** (*Manual `workflow_dispatch` / Nightly Cron only*): Runs `scripts/run_live_retrieval_quality_evaluation.py` with external network egress without blocking normal PR checks.
- **Files Affected:**
  - `pyproject.toml` (new), `.github/workflows/ci.yml`.
- **Acceptance Criteria:** CI matrix passes across all 528 regression tests without silent omissions; reproducible dependency locks.

---

### Phase 3: Shared Acquisition Runtime Refactor
- **Priority:** P0 (Core Runtime Integrity)
- **Current State:** `AgentReachService` has duplicate `retrieve` method definitions. `router.py` is 1,706 lines long, mixing social API clients, Jina fetching, search dispatch, and fallback chains.
- **Target State:**
  - Reconcile `AgentReachService.retrieve` to cleanly handle both `RetrievalRequest` and keyword parameters.
  - Decompose `router.py` into modular platform adapters:
    - `backend/infrastructure/acquisition/routing/router.py` (~250 lines)
    - `backend/infrastructure/acquisition/adapters/social/reddit.py` (~200 lines)
    - `backend/infrastructure/acquisition/adapters/social/twitter.py` (~150 lines)
    - `backend/infrastructure/acquisition/adapters/web/jina.py` (~150 lines)
    - `backend/infrastructure/acquisition/security/url_validator.py` (~120 lines)
  - Keep `backend/services/agent_reach/adapter.py` as a re-exporting compatibility shim.
- **Files Affected:**
  - `backend/services/agent_reach/adapter.py`, `backend/services/agent_reach/native/router.py`, new adapter modules under `backend/infrastructure/acquisition/`.
- **Tests Required:** `tests/unit/test_agent_reach_service.py`, `tests/chaos/test_agent_reach_chaos.py`, `tests/unit/test_shared_acquisition_fabric.py`.
- **Acceptance Criteria:** All acquisition tests pass; no method shadowing; all channel adapters functional.

---

### Phase 4: Research Pipeline Decomposition
- **Priority:** P1
- **Current State:** `ResearchEngine.investigate()` is a single 581-line monolithic method coordinating 10 stages sequentially.
- **Target State:**
  - Decompose `investigate()` into discrete, testable stage handlers with typed inputs and outputs:
    1. `PlanningStage`
    2. `DiscoveryStage`
    3. `GatingStage` (`RelevanceGate` + `TemporalGuard`)
    4. `PrimaryEscalationStage`
    5. `RankingStage`
    6. `DeepReadingStage`
    7. `PassageExtractionStage`
    8. `GraphConstructionStage`
    9. `SynthesisStage`
    10. `LedgerPersistenceStage`
  - `ResearchEngine` acts as a clean pipeline coordinator.
- **Files Affected:**
  - `backend/services/research/research_engine.py`, new stage modules in `backend/application/research/`.
- **Tests Required:** `tests/integration/test_claim_pipeline.py`, `tests/benchmarks/test_research_performance.py`.
- **Acceptance Criteria:** Bit-for-bit identical `TruthDossier` and `ReplayLedger` output on benchmark claims.

---

### Phase 5: Domain Agent Modularization
- **Priority:** P1
- **Current State:** Domain extraction logic is misplaced in `backend/services/agent_reach/extraction/` (1,093 lines) and financial logic in `agent_reach/scout/` (2,106 lines). Domain agents are bloated (1,120–1,353 lines each).
- **Target State:**
  - Move `brandshield_extraction.py` $\to$ `backend/agents/brandshield/extraction.py`.
  - Move `trending_extraction.py` $\to$ `backend/agents/trending/extraction.py`.
  - Move `scout_extraction.py` and `scout/engine.py` $\to$ `backend/agents/scout/`.
  - Move `personal_extraction.py` $\to$ `backend/agents/personal_watch/extraction.py`.
  - Decompose large agent classes into query generation, scanning, and threat assessment.
- **Files Affected:**
  - `backend/agents/*`, `backend/services/agent_reach/extraction/*`, `backend/services/agent_reach/scout/*`.
- **Tests Required:** `tests/unit/test_brandshield_agent.py`, `tests/unit/test_trending_agent.py`, `tests/unit/test_scout_agent.py`, `tests/unit/test_personal_agent.py`.
- **Acceptance Criteria:** All agent scan tests pass; domain agents own their extraction rules.

---

### Phase 6: Centralized LLM Gateway & Validated Settings
- **Priority:** P2
- **Current State:** Dispersed `os.getenv` reads for LLM keys and configuration; direct `requests.post` to Gemini in agents.
- **Target State:**
  - Centralize settings in `backend/core/settings.py` via Pydantic `BaseSettings`.
  - Implement `LLMGateway` protocol in `backend/infrastructure/llm/gateway.py` with `GeminiProvider` and `MockLLMProvider`.
  - Domain agents call `llm_gateway.generate_structured(...)`.
- **Files Affected:**
  - `backend/config.py`, `backend/services/gemini_service.py`, `backend/services/intelligence.py`, all domain agents.
- **Tests Required:** `tests/unit/test_gemini_service.py`, full suite with `AEGIS_MOCK_LLM=true`.
- **Acceptance Criteria:** Zero direct `os.getenv("GEMINI_*")` calls in agents; deterministic offline test execution.

---

### Phase 7: Legacy Deprecation & Final Cleanup
- **Priority:** P2
- **Current State:** Re-exporting import shims and legacy fallback scrapers remain from earlier migration phases.
- **Target State:**
  - Audit all internal callers; eliminate transitional shims in `backend/services/`.
  - Archive `backend/services/agent_reach_scraper.py` if native adapters achieve 100% reliability.
  - Final tree audit and verification.
- **Acceptance Criteria:** Zero deprecated shims; clean build context; 100% full regression suite passes.

---

## 4. Protected Code & Invariant Exclusions (DO NOT REMOVE)

The following components are core intellectual property or frozen benchmarks and **must not be deleted, stripped, or degraded**:
1. `tests/retrieval_benchmark/`: Frozen golden dataset (`scenarios.jsonl`, `candidates.jsonl`, `labels.jsonl`).
2. `artifacts/live_retrieval_evaluation/`: Golden audit deliverables and failure catalogs.
3. `backend/services/research/temporal_guard.py`: 48-hour freshness window and timestamp decoupling.
4. `backend/services/research/entity_resolver.py`: Named entity resolution, homograph defense, and action verb filters.
5. `backend/services/research/replay_ledger.py`: SHA-256 cryptographic provenance chain.
6. `frontend/`: Vanilla HTML/JS analyst consoles (`index.html`, `about.html`, `investigate.html`, etc.).
