# Aegis Protocol — Complete Workspace Inventory Report

**Phase:** 7.2 (Workspace Organization, Repository Hygiene & Safe Structural Consolidation)  
**Role:** Senior Software Architect, Repository Maintenance Engineer, Developer Experience Engineer  
**Baseline Commit:** `a72ae74a739c2ee568f7a8398cd8ec1159a9a1ff`  
**Branch:** `feat/phase7-2-workspace-organization`  
**Date:** 2026-10-11  

---

## 1. Executive Summary

This inventory provides an authoritative, evidence-grounded classification of all Git-tracked and local assets in the Aegis Protocol repository. As of Phase 7.1, the repository contains **943 Git-tracked files** across 12 top-level directories, plus localized scratch notes, caches, and test artifacts.

The objective of Phase 7.2 is to establish clear boundaries, predictable discovery, and developer navigation **without breaking any of the 787 verified offline regression tests, 16 recovered acquisition operations, 4 production agents, or historical benchmark fixtures**.

```
Tracked Files by Major Directory (Total = 943 files):
├── research/      : 250 files  (Historical benchmark runs, scraper bakeoffs, test datasets)
├── backend/       : 226 files  (Production application, 4 agents, native router, core infrastructure)
├── docs/          : 138 files  (Architecture specifications, operational runbooks, phase reports)
├── artifacts/     : 111 files  (Empirical audit outputs, benchmark JSONL data, replay evidence)
├── tests/         :  86 files  (Unit, integration, contract, chaos, security, benchmarks, frontend)
├── scripts/       :  40 files  (Validation, benchmarks, evaluations, diagnostics, audits)
├── frontend/      :  33 files  (Production workbenches, shared styles, operation-health logic)
├── <root>/        :  21 files  (Configuration, CLI launchers, documentation entrypoints)
├── scrapers/      :  18 files  (Standalone scraper laboratory testing framework)
├── brag-output/   :  17 files  (Launch video composition assets and media)
├── .github/       :   1 files  (GitHub Actions workflow definitions)
├── .gemini/       :   1 files  (IDE integration metadata)
└── tools/         :   1 files  (Visual audit documentation generator)
```

---

## 2. Directory-by-Directory Detailed Inventory

### 2.1. Repository Root (`<root>/`)

- **Primary Purpose**: Project entrypoints, dependency definitions, container/deployment manifests, and top-level documentation.
- **Tracked Files (21)**:
  - Configuration: `.dockerignore`, `.editorconfig`, `.env.example`, `.gitignore`, `pyproject.toml`, `pytest.ini`, `requirements.txt`, `skills-lock.json`.
  - Deployment: `Dockerfile`, `docker-compose.yml`, `netlify.toml`, `render.yaml`.
  - Application Launchers: `main.py` (FastAPI runner with port discovery), `scraper.py` (Scraper Laboratory CLI).
  - Documentation: `README.md`, `CHANGELOG.md`, `ARCHITECTURE.md`, `ENDPOINTS_MAP.md`, `ENV_SETUP.md`.
  - External Portfolio Rubrics: `Gemini_rubrics.md`, `Rubrics.docx`.
- **Local Untracked / Ignored Files**:
  - `accounts.db`, `aegis_local.db` (Local SQLite run databases; in `.gitignore`).
  - `port.txt` (Written by `main.py` on startup; in `.gitignore`).
  - `.scraper_health_history.json` (Written by `scraper.py`; in `.gitignore`).
  - `final_report_prompt.txt`, `found_questions.txt`, `full_mission_mandate.txt`, `questions_full.txt`, `temp_user_prompts.txt` (Local research scratchpads; in `.gitignore`).
  - `.agent/`, `.agents/`, `.gemini/`, `.vscode/`, `.wrangler/`, `venv/`, `aegis_protocol.egg-info/`.
- **Current Consumers**:
  - Developers, Docker builds, Netlify/Render deployment pipelines, `pytest`, `pip install`.
- **Problems Identified**:
  - Root clutter: `Gemini_rubrics.md` and `Rubrics.docx` are career/market rubric assets checked in at root without clear connection to Aegis Protocol architecture.
  - Duplication: `ARCHITECTURE.md` exists at both root and `docs/ARCHITECTURE.md`.
  - Missing License: `README.md` linked to `[LICENSE](LICENSE)`, but no `LICENSE` file was present.
- **Recommended Action**:
  - Add canonical MIT `LICENSE` matching `pyproject.toml` (Safe, fixes broken link).
  - Retain `main.py` and `scraper.py` as primary executable entry points.
  - Document `Gemini_rubrics.md` and `Rubrics.docx` in the Cleanup-Candidate Register for owner review.
- **Safety Assessment**: Safe. No root entrypoint deletions.

---

### 2.2. Backend (`backend/`)

- **Primary Purpose**: Production Python application core, API gateway, multi-agent fleet, native acquisition layer, source planning engine, and data storage.
- **Important Files & Subdirectories (226 files)**:
  - `backend/main.py`: Primary FastAPI application entrypoint with route mounting, CORS, middleware, static files.
  - `backend/agents/`: Scout, Trending, BrandShield, Personal Watch, and Claim Ingestion agents.
  - `backend/api/`: FastAPI routers (`/api/claims`, `/api/scout`, `/api/trending`, `/api/brandshield`, `/api/personal-watch`, `/api/agent-reach`, `/api/healthz`, `/api/readyz`, `/api/replay`).
  - `backend/infrastructure/`: Acquisition router (`NativeRouter`), LLM gateway (`CentralizedLLMGateway`), rate limiters, SSRF security firewall.
  - `backend/services/agent_reach/`: Source planning engine (`SourcePlanningEngine`), capability registry (`RuntimeOperationCapabilities`), platform adapters.
  - `backend/core/`: Configuration settings (`Settings`), telemetry logging, error definitions.
  - `backend/data/`: `WELFake_Dataset.xlsx` (benchmark), `backend/data/dossiers/` (2,312 historical investigation dossiers).
  - `backend/db/`: Database connectivity and schema initialization (`setup_aegis_db.sql`).
- **Current Consumers**:
  - FastAPI web server, CLI agents, all integration and contract tests.
- **Problems Identified**:
  - High complexity in `NativeRouter` (1,700+ lines), though thoroughly stabilized and hardened in Phase 7.
- **Recommended Action**:
  - Preserve exact layout. Zero directory renames or module moving inside `backend/` to protect existing imports.
  - Protect all 2,312 dossiers in `backend/data/dossiers/` as immutable.
- **Safety Assessment**: High stability required. Modifying `backend/` structure carries extreme regression risk.

---

### 2.3. Frontend (`frontend/`)

- **Primary Purpose**: Browser consoles and workbenches for human analysts across all four agents.
- **Important Files (33 files)**:
  - Agent Consoles: `scout-agent.html`, `trending-agent.html`, `brandshield-agent.html`, `personal-watch-agent.html`.
  - System Portals: `index.html`, `dashboard.html`, `submit.html`, `status.html`, `about.html`, `benchmark.html`, `lab.html`, `changelog.html`.
  - Client Logic: `operation-health.js` (freshness-managed capability health), `aegis-nav.js` (navigation bar), `aegis-theme.css` (design system tokens).
- **Current Consumers**:
  - Browser analysts, `backend/main.py` static server, frontend contract tests (`test_frontend_operation_health_contract.py`).
- **Problems Identified**:
  - All pages reside directly in `frontend/` without subfolders.
- **Recommended Action**:
  - Keep flat structure intact because `backend/main.py` mounts `/static` and binds direct route endpoints (`/`, `/dashboard`, `/scout-agent`, etc.) directly to `frontend/<page>.html`. Moving them would break URL routing.
- **Safety Assessment**: Safe. No modifications needed beyond keeping asset integrity.

---

### 2.4. Tests (`tests/`)

- **Primary Purpose**: Complete automated regression verification suite (787 collected tests).
- **Structure & File Counts (86 files)**:
  - `tests/unit/`: Fast, deterministic isolated tests (591 passed).
  - `tests/integration/`: Multi-component and pipeline integration (FastAPI TestClient).
  - `tests/contract/`: Public API and 16 recovered operations contract invariants.
  - `tests/security/`: SSRF, XSS, and static path traversal guards.
  - `tests/chaos/`: Transient network failure and retry recovery behavior.
  - `tests/benchmarks/`: Learned reranker and performance regression checks.
  - `tests/evaluation/`: ML and forensic scoring evaluation.
  - `tests/frontend/`: Pure Node.js unit tests for `operation-health.js`.
  - `tests/retrieval_benchmark/`: Frozen Cranfield benchmark datasets (`candidates.jsonl`, `labels.jsonl`, `scenarios.jsonl`).
  - Root test files (10 files): `test_api_endpoints.py`, `test_retrieval_benchmark.py`, `test_trending_temporal_guard.py`, etc.
- **Current Consumers**:
  - `pytest`, GitHub Actions CI, local verification runners.
- **Problems Identified**:
  - Mix of directory tests and root-level `tests/test_*.py` files.
- **Recommended Action**:
  - Preserve all test file locations. Pytest discovers all 787 tests via `pytest.ini` (`testpaths = tests`). Moving root test files would alter relative fixture paths (e.g. `tests/retrieval_benchmark/scenarios.jsonl`) and risk breaking tests.
- **Safety Assessment**: Safe. Do not reorganize test file paths.

---

### 2.5. Development & Audit Scripts (`scripts/`)

- **Primary Purpose**: Validation runners, live acquisition audits, benchmark harnesses, diagnostics.
- **Important Files (40 files)**:
  - Release Validation: `validate_release_candidate_smoke.py`, `validate_rollback_compatibility.py`, `live_agent_smoke_test.py`.
  - Benchmark Runners: `scripts/benchmarks/run_retrieval_benchmark.py`, `run_retrieval_quality_benchmark.py`, `validate_retrieval_benchmark.py`.
  - Evaluation CLI: `evaluate_dataset.py`, `evaluate_all_agents.py`.
  - Historical Audits: `run_phase6_...`, `run_phase6_7_...`, `run_phase6_8_...`, `run_pre_phase7_...`.
- **Current Consumers**:
  - 5 test files (`test_live_smoke_harness.py`, `test_retrieval_benchmark.py`, `test_complete_retrieval_audit_integrity.py`, `test_agent_quality_evaluation.py`, `test_benchmark_schema.py`) import directly from `scripts.<module>`.
  - Developer CLI invocations (`python scripts/evaluate_dataset.py`, `python scripts/validate_release_candidate_smoke.py`).
- **Problems Identified**:
  - Flat 40-file listing makes it difficult for new engineers to locate the relevant script.
- **Recommended Action**:
  - Create a structured `scripts/README.md` and `docs/development/SCRIPT_INDEX.md` categorizing all 40 scripts into 6 functional groups (Validation, Audits, Benchmarks, Evaluation, Diagnostics, Development).
  - Preserve all 40 scripts at their current entry points to ensure zero import regressions.
- **Safety Assessment**: Completely safe with zero risk of breaking existing callers.

---

### 2.6. Documentation (`docs/`)

- **Primary Purpose**: Architecture specifications, developer guides, API references, security guides, operational runbooks, and milestone audit reports.
- **Structure (138 files)**:
  - Top-level guides: `ARCHITECTURE.md`, `EVALUATION.md`, `FEATURE_STATUS.md`, `OPERATIONS.md`, `SECURITY.md`, `TESTING.md`, `index.md`.
  - Subdirectories: `agents/`, `api/`, `architecture/`, `archive/`, `audit/`, `ci/`, `development/`, `evaluation/`, `operations/`, `security/`, `testing/`, `visual-audit/`.
- **Problems Identified**:
  - Outdated test counts (citing 530 tests instead of 787).
  - Hardcoded Windows file links (`file:///c:/Users/Shaunak%20Rane/...`) in several older architecture files.
  - Broken links in `docs/agents/README.md` using `../../backend/agents/...`.
  - Missing developer workspace map and coding-agent guide (`AGENTS.md`).
- **Recommended Action**:
  - Modernize `docs/index.md` to serve as the unified documentation portal linking all Phase 7 and 7.1 artifacts.
  - Convert hardcoded Windows paths to cross-platform relative links.
  - Create `docs/development/WORKSPACE_MAP.md`, `docs/development/SCRIPT_INDEX.md`, and `docs/development/CLEANUP_CANDIDATE_REGISTER.md`.
- **Safety Assessment**: High value, zero runtime code risk.

---

### 2.7. Research & Experiments (`research/`)

- **Primary Purpose**: Historical benchmark evaluations, zero-auth acquisition research, scraper bakeoffs.
- **File Count (250 files)**:
  - Subdirectories: `full_noauth_benchmark_...`, `semantic_retrieval_...`, `social_noauth_benchmark/`, `scraper_bakeoff/`, etc.
- **Problems Identified**:
  - Untracked empty directory `research/research/scraper_bakeoff/`.
  - External cloned repositories in `research/scraper_bakeoff/repos/` (already ignored by `.gitignore`).
- **Recommended Action**:
  - Preserve `research/` entirely. As mandated by preservation rules: "Do not delete the research/ directory."
- **Safety Assessment**: Protected research assets.

---

### 2.8. Historical Audit Artifacts (`artifacts/`)

- **Primary Purpose**: Empirical audit logs, benchmark summaries, live smoke test outputs.
- **File Count (111 files)**:
  - Includes `phase7_1_smoke_validation_results.json`, `retrieval_benchmark/`, `live_retrieval_evaluation/`, etc.
- **Recommended Action**:
  - Treat all artifacts as immutable historical proof. Zero deletions.
- **Safety Assessment**: Protected data.

---

### 2.9. Scraper Laboratory Framework (`scrapers/` & `tools/`)

- **Primary Purpose**: Standalone laboratory canary and schema-drift detection suite.
- **Structure**:
  - `scraper.py` (CLI entrypoint at root).
  - `scrapers/`: `runner.py`, `registry.py`, `reporters.py`, `websites/` (11 platform canaries), `fixtures/`.
  - `tools/make_audit_readme.py`: Utility generating `docs/visual-audit/README.md`.
- **Recommended Action**:
  - Keep intact as an isolated laboratory tool. It is strictly isolated from production runtime.
- **Safety Assessment**: Fully stable.

---

### 2.10. Video & Composition (`brag-output/`)

- **Primary Purpose**: Automated launch video recording, composition HTML, and demo assets.
- **Structure (17 files)**:
  - `brag.mp4` (ignored in `.gitignore`), `brag.png`, `brag-plan.md`, `composition/index.html`.
- **Current Consumers**:
  - Tested by `scripts/test_launch_video_integrity.py`.
- **Recommended Action**:
  - Preserve intact.

---

## 3. Summary of Identified Problems & Planned Mitigations

| Problem | Location | Severity | Phase 7.2 Resolution |
| :--- | :--- | :---: | :--- |
| **Missing LICENSE file** | Root (`README.md` links to it) | Medium | Created canonical MIT `LICENSE` matching `pyproject.toml`. |
| **Hardcoded Windows Links** | `docs/` (`file:///c:/Users/...`) | Medium | Replaced with relative cross-platform links. |
| **Outdated Test Counts** | `README.md`, `docs/index.md` (530 tests) | Low | Updated to reflect the complete 787-test offline gate. |
| **Undiscoverable Scripts** | `scripts/` (40 flat files) | Medium | Created `scripts/README.md` and `docs/development/SCRIPT_INDEX.md`. |
| **Missing Coding Agent Orientation** | Root | High | Created authoritative `AGENTS.md` orientation guide. |
| **Root Clutter (Career Rubrics)** | Root (`Gemini_rubrics.md`, `Rubrics.docx`) | Low | Registered in `CLEANUP_CANDIDATE_REGISTER.md` for owner decision. |
| **Stale Changelog** | Root (`CHANGELOG.md`) | Low | Documented milestones from Phase 6.0 through Phase 7.2. |
| **Unlinked Phase 7 & 7.1 Reports** | `docs/index.md` | Medium | Integrated all current Phase 7 & 7.1 reports into canonical index. |
