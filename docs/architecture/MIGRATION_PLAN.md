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
| **2** | **Build, Packaging & CI Test Suite Hygiene** | **P1** | Add `pyproject.toml`, lock dependency strategies, expand CI to 7 parallel jobs. | **PARTIALLY DELIVERED** (Packaging & CI template created; CI activation & lockfile pending) |
| **3** | **Shared Acquisition Runtime Refactor** | **P0** | Fix duplicate `retrieve()`, decompose 1,706-line `router.py` into modular adapters. | **DELIVERED + PHASE 3.5 CLOSEOUT** (Canonical infrastructure service, decomposed query dispatcher, compatibility shims, isolated test outputs, and 16-channel contracts) |
| **4** | **Research Pipeline Decomposition** | **P1** | Break 581-line `investigate()` into 10 composable pipeline stages. | **DELIVERED** (10 decoupled stages in `backend/application/research/`, `ResearchPipeline` coordinator, 12 golden characterization scenarios with bit-for-bit serialization equality, 628 passing tests) |
| **5** | **Domain Agent Modularization** | **P1** | Relocate agent-specific extraction from `agent_reach/` into owning agent packages. | **DELIVERED** (All 4 domain agents modularized: `brandshield`, `trending`, `personal_watch`, `scout`; 100% backward compatibility shims verified; 0 failures) |
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
- **Status:** **PARTIALLY DELIVERED**
  - **Delivered:** Authored PEP 517/518/621 `pyproject.toml` establishing standard project metadata, runtime dependencies, optional groups (`test`, `benchmarks`, `dev`), and `pytest` discovery. Created decoupled 7-job expanded CI matrix template at `docs/development/ci_matrix_expanded.yml`. The active three-job workflow now includes push coverage for `feat/retrieval-quality-benchmark` as well as `main`.
  - **Pending Activation:** The expanded seven-job matrix remains a template and has not replaced the active three-job workflow. A successful local YAML parse or a feature-branch trigger does not establish that the expanded matrix is active or that a remote GitHub Actions run passed.
  - **Pending Dependency Locking:** A dedicated pinned lockfile (`requirements-lock.txt` or constraints file) is pending evaluation to guarantee bit-for-bit reproducible installs without relying on open `>=` ranges.
- **Priority:** P1
- **Current State:** `.github/workflows/ci.yml` remains the active three-job workflow and is configured for `main` plus the Phase 3.5 feature branch. `docs/development/ci_matrix_expanded.yml` remains the proposed seven-job template. Dependency locking and expanded-matrix activation are still pending, so Phase 2 is not complete.
- **Target State (Upon Full Activation):**
  - `.github/workflows/ci.yml` executes the 7-job parallel matrix across Python 3.11, 3.12, 3.13:
    1. **`lint-format`**: Code style and static analysis on core packages (`flake8`).
    2. **`fast-unit-chaos`**: Fast offline tests (`tests/unit/`, `tests/chaos/`).
    3. **`security-invariants`**: Security, SSRF checks, and ledger integrity (`tests/security/`, `test_complete_retrieval_audit_integrity.py`).
    4. **`integration`**: API route and database integration tests (`tests/integration/`, `tests/contract/`, `test_api_endpoints.py`, `test_unified_report.py`).
    5. **`offline-retrieval-benchmark`**: All root benchmark and temporal guard suites (`test_retrieval_benchmark.py`, `test_retrieval_metrics.py`, `test_trending_temporal_guard.py`, `test_semantic_reranker.py`, `test_retrieval_quality_hardening.py`, `test_audit_synthetic_telemetry_negatives.py`, `test_research_performance.py`).
    6. **`docs-validation`**: Schema and offline ML baselines (`evaluate_dataset.py --mode reranker`, `evaluate_dataset.py --mode averitec_status`).
    7. **`live-retrieval-eval`** (*Manual `workflow_dispatch` / Nightly Cron only*): Runs `scripts/run_live_retrieval_quality_evaluation.py` with external network egress without blocking normal PR checks.
- **Files Affected:**
  - `pyproject.toml` (delivered), `docs/development/ci_matrix_expanded.yml` (delivered template), `.github/workflows/ci.yml` (pending activation).
- **Acceptance Criteria:** Full 530 regression test suite passes offline; package installs cleanly via PEP 517 standard.

---

### Phase 3: Shared Acquisition Runtime Refactor
- **Status:** **DELIVERED; PHASE 3.5 ARCHITECTURE CLOSEOUT IMPLEMENTED**
- **Priority:** P0 (Core Runtime Integrity)
- **Delivered Architecture:**
  - Reconciled `AgentReachService.retrieve` into a single polymorphic method supporting both `RetrievalRequest` instances and string queries; eliminated the shadowed method definition.
  - Moved the complete canonical `AgentReachService` implementation into `backend/infrastructure/acquisition/service.py`. The legacy module re-exports the exact same class and singleton objects; it no longer owns a duplicate implementation.
  - Decomposed 1,706-line monolithic `router.py` into decoupled platform adapters under `backend/infrastructure/acquisition/`:
    - `backend/infrastructure/acquisition/security/url_validator.py`: SSRF defense with private/loopback/cloud metadata IP validation and thread-safe DNS caching.
    - `backend/infrastructure/acquisition/adapters/base.py`: Abstract `PlatformAdapter` contract.
    - `backend/infrastructure/acquisition/adapters/social/reddit.py`: Arctic Shift REST query/comments/post read adapter with batching, cache injection, and normalizers.
    - `backend/infrastructure/acquisition/adapters/social/twitter.py`: FxTwitter REST status/profile lookup adapter with cache injection and normalizers.
    - `backend/infrastructure/acquisition/adapters/web/jina.py`: Web reading adapter with Scrapling HTTP primary, legacy fallback, and Jina tertiary readers.
    - `backend/infrastructure/acquisition/routing/channel_dispatcher.py`: Shared handler selection, error semantics, latency, and provenance defaults.
    - `backend/infrastructure/acquisition/routing/standard_handlers.py`: Native, feed, reader, credential-gated, and deterministic standard-channel fallbacks.
    - `backend/infrastructure/acquisition/routing/social_handlers.py`: Reddit/X direct-source retrieval, discovery, public-mirror acquisition, and honest search-index fallback.
    - `backend/infrastructure/acquisition/routing/router.py`: `NativeRouter` orchestration plus reusable read/search helpers and Policy D coordination. During Phase 3.5 it decreased from 1,446 to 815 physical lines, while `execute_channel_query()` decreased from 642 to 22 physical lines.
    - `backend/infrastructure/acquisition/service.py`: Canonical acquisition-service implementation.
  - Converted legacy import locations into 100% backward-compatible re-exporting shims:
    - `backend/services/agent_reach/adapter.py`
    - `backend/services/agent_reach/native/router.py`
    - `backend/services/url_validator.py`
    - `backend/services/agent_reach/native/adapters/base.py`
    - `backend/services/agent_reach/native/adapters/reddit.py`
    - `backend/services/agent_reach/native/adapters/twitter.py`
  - Isolated benchmark and agent-quality test output in pytest temporary directories so regression runs cannot overwrite tracked evaluation artifacts.
  - Added `docs/architecture/ACQUISITION_CHANNEL_COVERAGE.md` and executable contracts for all 16 advertised capabilities, including explicit credential-required and unsupported states.
- **Phase 3.5 Call Flow:**
  - Before: `AgentReachService -> NativeRouter.execute_channel_query()` contained platform selection, native calls, social discovery, fallbacks, normalization tags, errors, and telemetry in one 642-line method.
  - After: `AgentReachService -> NativeRouter -> ChannelQueryDispatcher -> StandardChannelHandlers | SocialChannelHandlers -> existing executor/adapters/normalizer`, with shared error, latency, and provenance finalization in the dispatcher.
- **Files Affected:**
  - `backend/infrastructure/acquisition/`, `backend/services/agent_reach/adapter.py`, `backend/services/agent_reach/native/router.py`, `backend/services/url_validator.py`, `backend/services/agent_reach/native/adapters/*`, `tests/unit/test_agent_reach_service.py`.
- **Tests Required:** Service identity and compatibility, acquisition fabric, all 16 channel contracts, zero-auth social retrieval/discovery, telemetry, provenance, SSRF/XSS security, chaos, API/contract integration, modular routers, and the complete offline pytest suite.
- **Acceptance Criteria:** All acquisition and regression tests pass; no method shadowing; legacy imports resolve to the canonical implementation; the query router contains no multi-platform mega-method; every advertised channel has an honest executable contract; tests do not mutate tracked benchmarks. Exact test evidence is recorded from the Phase 3.5 validation run rather than retained as a stale fixed count in this roadmap.
- **Phase 3.5 Validation (October 10, 2026):** 198 focused acquisition, compatibility, security, chaos, and API/contract tests passed in 74.97 seconds. The complete offline suite passed with 606 passed, 0 failed, 0 errors, 0 skipped, and no warning summary in 413.19 seconds (pytest exit code 0). Post-test Git hashes for the tracked retrieval benchmark summaries matched `HEAD`.

---

### Phase 4: Research Pipeline Decomposition
- **Status:** **DELIVERED**
- **Priority:** P1 (Core Investigative Architecture)
- **Delivered Architecture:**
  - Decomposed 756-line monolithic `backend/services/research/research_engine.py` into a modular application pipeline under `backend/application/research/`:
    - `backend/application/research/contracts.py`: Explicit typed hand-offs between stages (`QueryPlan`, `Discovery`, `RankedEvidence`, `AdaptiveEvidence`, `EscalatedEvidence`, `ReadEvidence`, `Analysis`, `AssembledResearch`).
    - `backend/application/research/pipeline.py`: `ResearchPipeline` coordinator executing stages cleanly without owning low-level retrieval or scoring logic.
    - `backend/application/research/acquisition.py`: `PlanningStage` (`QueryPlanningStage`), `DiscoveryStage` (`BroadDiscoveryStage`), `GatingStage` (`CandidateQualificationStage`), `RankingStage` (`IndependenceRankingStage`).
    - `backend/application/research/adaptive.py`: `AdaptiveDiscoveryCoordinator` (`AdaptiveExpansionStage`) orchestrating multi-round adaptive query expansion, dynamic replanning from discovered contradictions, and mathematical evidence novelty/saturation tracking (`EvidenceNoveltyTracker`).
    - `backend/application/research/reading.py`: `PrimaryEscalationStage` and `DeepReadingStage` with diversity-aware selection, budget enforcement, and acquisition attempt tracking.
    - `backend/application/research/synthesis.py`: `PassageExtractionStage` (`PassageAnalysisStage`), `SynthesisStage` (`GroundedSynthesisStage`), `GraphConstructionStage` (`EvidenceGraphStage`), and `synthesize_grounded_findings()` maintaining deterministic 6D quality tensor evaluation.
    - `backend/application/research/assembly.py`: `CorpusAssemblyStage`, `LedgerPersistenceStage` (`DossierRegistrationStage`), and `ResultPublicationStage` assembling funnel telemetry, persisting replay dossiers, and constructing `ResearchResult`.
  - Converted `backend/services/research/research_engine.py` into a lean 39-line orchestrator and compatibility shim preserving `ResearchEngine`, singleton `research_engine`, and helper `_synthesize_grounded_findings`.
  - Added 12 golden characterization scenarios in `tests/unit/test_research_pipeline_golden.py` validating bit-for-bit SHA-256 equivalence across `result_sha256`, `corpus_sha256`, `dossier_sha256`, candidate IDs, ranked IDs, rejected IDs, query execution statuses, finding IDs, candidate hashes, and lineage metrics against pre-refactor baselines.
  - Added unit test suite `tests/unit/test_research_pipeline_stages.py` exercising all 10 stages independently with normal and empty/edge inputs.
- **Files Affected:**
  - `backend/application/research/` (`__init__.py`, `pipeline.py`, `contracts.py`, `acquisition.py`, `adaptive.py`, `reading.py`, `synthesis.py`, `assembly.py`), `backend/services/research/research_engine.py`, `tests/unit/test_research_pipeline_golden.py`, `tests/unit/fixtures/research_phase4_golden.json`, `tests/unit/test_research_pipeline_stages.py`.
- **Tests Required:** `tests/unit/test_research_pipeline_stages.py`, `tests/unit/test_research_pipeline_golden.py`, `tests/integration/test_claim_pipeline.py`, `tests/benchmarks/test_research_performance.py`, `tests/contract/`, `tests/security/`, `tests/chaos/`, full regression suite.
- **Acceptance Criteria:** Bit-for-bit identical `TruthDossier` and `ReplayLedger` output across all 12 golden investigative scenarios; all 10 stages testable independently; full regression suite passes with 628 passed, 0 failed, 0 warnings.
- **Phase 4 Validation (October 10, 2026):** Full test suite executed with 628 passed, 0 failed, 0 errors, and 0 warnings. Golden characterization test passed with 100% hash and integrity parity.

---

### Phase 5: Domain Agent Modularization
- **Status:** **DELIVERED**
- **Priority:** P1 (Domain Agent Architecture & Ownership)
- **Delivered Architecture:**
  - Decomposed all four bloated monolithic domain agents into cohesive, single-responsibility domain packages under `backend/agents/`:
    1. **BrandShield** (`backend/agents/brandshield/`):
       - `models.py`: Domain entity models, brand catalogs (`KNOWN_BRAND_CATALOG`), threat taxonomy (`THREAT_TAXONOMY`), and typed extraction result schemas.
       - `planning.py`: Entity resolution (`resolve_brand_entity`), trademark variations, and specialized query planning.
       - `scanning.py`: Multi-channel evidence retrieval (`search_brand_evidence`) delegating purely to the Shared Acquisition Fabric.
       - `assessment.py`: Threat synthesis (`synthesize_brand_threats`, `heuristic_threat_synthesis`) and review anomaly detection (`screen_review_patterns`).
       - `dossier.py`: Forensic investigation dossier builder (`build_investigation_dossiers`).
       - `extraction.py`: Dedicated domain extractor (`BrandShieldExtractionEngine`, `brandshield_extractor`).
       - `agent.py`: `BrandShieldAgent` orchestrator coordinator and `brandshield_agent` singleton.
    2. **Trending** (`backend/agents/trending/`):
       - `models.py`: Trend records, narrative clusters, entity modes, and typed extraction results.
       - `temporal.py`: 48h temporal freshness filtering, source timestamp validation, and velocity decay.
       - `discovery.py`: Broad trend discovery and RSS/feed aggregation via Shared Acquisition Fabric.
       - `clustering.py`: Narrative clustering (`_heuristic_trend_clustering`) and syndication grouping.
       - `assessment.py`: Virality velocity tracking, anomaly scoring, and threat narrative evaluation.
       - `extraction.py`: Canonical extractor (`TrendingExtractionEngine`, `trending_extractor`).
       - `agent.py`: `TrendingAgent` orchestrator coordinator and `trending_agent` singleton.
    3. **Personal Watch** (`backend/agents/personal_watch/`):
       - `models.py`: Identity models, career timeline events, public statements, and threat records.
       - `identity.py`: Executive identity normalization, disambiguation, and target persona profiling.
       - `monitoring.py`: Omni-channel executive presence scanning via Shared Acquisition Fabric.
       - `assessment.py`: Impersonation detection, reputational threat synthesis, and consecutive-scan change detection.
       - `dossier.py`: Person of interest dossier construction.
       - `extraction.py`: Canonical extractor (`PersonalWatchExtractionEngine`, `personal_watch_extractor`).
       - `agent.py`: `PersonalWatchAgent` orchestrator coordinator and `personal_watch_agent` singleton.
    4. **Scout** (`backend/agents/scout/`):
       - `models.py`: Domain financial facts, corporate events, market catalysts, contradictions, and extraction results.
       - `financial.py`: Ticker entity resolution, historical/real-time stock chart retrieval, volatility Z-score modeling, and empirical impact forecasting.
       - `assessment.py`: Omni-channel social sentiment and short-attack correlation (`correlate_social_rumors`), plus evidence-grounded catalyst synthesis.
       - `extraction.py`: Dedicated financial extraction engine (`ScoutExtractionEngine`, `scout_extractor`).
       - `sources/`: Relocated Scout source orchestration and evidence production subsystem (`engine.py`, `models.py`, `discovery.py`, `ranking.py`, `deduplication.py`, `corroboration.py`, `transport.py`, `cache.py`, `telemetry.py`, `extraction/`, `adapters/`).
       - `agent.py`: `ScoutAgent` orchestrator coordinator, `scout_agent` singleton, and `process_scout_task`.
  - Maintained 100% backward-compatible shims with identical class and extractor identities (`is` check passed) at historical import paths:
    - `backend/agents/brandshield_agent.py` $\to$ `backend.agents.brandshield`
    - `backend/agents/trending_agent.py` $\to$ `backend.agents.trending`
    - `backend/agents/personal_agent.py` $\to$ `backend.agents.personal_watch`
    - `backend/agents/scout_agent.py` $\to$ `backend.agents.scout`
    - `backend/services/agent_reach/extraction/*` $\to$ `backend.agents.<name>.extraction`
    - `backend/services/agent_reach/scout/*` $\to$ `backend.agents.scout.sources.*`
  - Preserved critical architectural contracts:
    - `from backend.services.agent_reach import agent_reach_service` verbatim import in all agent shims.
    - Zero direct raw scraper imports (`DDGS`, `scrapers/`) in domain agents.
    - Explicit re-export of `agent_reach_service` in `backend.services.agent_reach.scout.engine` for unittest patch targets.
- **Files Affected:**
  - Added packages: `backend/agents/brandshield/`, `backend/agents/trending/`, `backend/agents/personal_watch/`, `backend/agents/scout/`.
  - Updated shims: `backend/agents/*_agent.py`, `backend/services/agent_reach/extraction/*`, `backend/services/agent_reach/scout/*`.
- **Tests Required:** `tests/unit/test_shared_acquisition_fabric.py`, `tests/unit/test_architecture_invariants.py`, `tests/integration/test_functional_agents_matrix.py`, `tests/unit/test_agent_prompts_contracts.py`, `tests/unit/test_scout_research_terminal.py`, `tests/unit/test_scout_source_engine.py`, `tests/integration/test_scout_2_workflow.py`, `tests/integration/test_brandshield_2_workflow.py`, `tests/integration/test_personal_watch_2_workflow.py`, `tests/integration/test_trending_2_workflow.py`, full regression suite.
- **Acceptance Criteria:** All domain agents independently testable; class identities preserved; backward compatibility 100% functional; 0 test regressions.
- **Phase 5 Validation (October 10, 2026):** All 477 unit/integration tests and 105 root suite tests passed with 0 failures, 0 errors. All agent contract and fabric tests passed. Benchmark datasets and frozen labels preserved bit-for-bit without modification.

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
