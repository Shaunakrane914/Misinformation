# Aegis Protocol — Target Workspace Structure Specification

**Phase:** 7.2 (Workspace Organization, Repository Hygiene & Safe Structural Consolidation)  
**Author:** Senior Software Architect, Repository Maintenance Engineer, Developer Experience Engineer  
**Status:** Canonical Architectural Decision & Workspace Specification  
**Date:** 2026-10-11  

---

## 1. Architectural Motivation & Guiding Principles

Aegis Protocol is an evidence-first multi-agent intelligence and misinformation research platform. Over successive development milestones (Phases 0 through 7.1), the codebase evolved into a highly capable system featuring:
- 4 production agents (Scout, Trending, BrandShield, Personal Watch)
- 16 recovered acquisition operations across GitHub, YouTube, V2EX, Xiaoyuzhou, Web, and RSS
- Centralized LLM Gateway with deterministic fallback
- Runtime-aware capability tracking and bounded frontend health caching
- 787 verified offline regression tests

However, rapid engineering accumulated navigational complexity:
1. Flat script proliferation in `scripts/` (40 files serving disparate functions).
2. Outdated documentation claiming 530 tests, linking to obsolete architecture sketches, and using Windows-specific absolute file links.
3. Miscellaneous portfolio rubrics and untracked prompt scratchpads at root.
4. Absence of a concise, canonical onboarding guide for AI coding assistants (`AGENTS.md`).

### Non-Destructive Consolidation Policy
Rather than conducting risky, cosmetic mass moves that invalidate Python imports, relative test fixtures, and Git commit histories, Phase 7.2 enforces a **Safe Structural Consolidation Policy**:
- **Preserve Source Code Paths**: Zero module moves inside `backend/`, `frontend/`, `scrapers/`, or `tests/`.
- **Preserve Established Script Entry Points**: Keep all 40 scripts accessible via their established CLI paths (`python scripts/<script>.py`) and import paths (`from scripts.<script> import ...`), while providing categorized discovery manifests.
- **Modernize Documentation & Navigation**: Centralize documentation navigation in `docs/index.md`, update `README.md`, fix broken cross-references, and create `AGENTS.md`.
- **Register Cleanup Candidates**: Safely document non-essential files in a formal register for repository owner action rather than performing unauthorized mass deletions.

---

## 2. Target Workspace Topology

```text
Misinformation/
├── AGENTS.md                          # [NEW] Canonical orientation for AI coding agents & engineers
├── LICENSE                            # [FIX] MIT License (resolves broken README link)
├── README.md                          # [UPDATED] Production entrypoint, 787 tests, quickstart
├── CHANGELOG.md                       # [UPDATED] Authoritative milestone changelog (v3.5 -> v4.1/Phase 7.2)
├── ARCHITECTURE.md                    # Root architecture entrypoint
├── ENDPOINTS_MAP.md                   # Canonical REST API and frontend route manifest
├── ENV_SETUP.md                       # API keys and environment configuration guide
├── Dockerfile                         # Production container definition
├── docker-compose.yml                 # Local container orchestration
├── pyproject.toml                     # Python package metadata (v4.1.0)
├── pytest.ini                         # Pytest configuration (testpaths = tests)
├── requirements.txt                   # Pinned dependency manifest
├── main.py                            # Convenience development launcher with port discovery
├── scraper.py                         # Standalone Scraper Laboratory CLI
│
├── backend/                           # PRODUCTION APPLICATION (PRESERVED)
│   ├── main.py                        # FastAPI entrypoint, routes, middleware, static server
│   ├── agents/                        # 4 Domain Agents (Scout, Trending, BrandShield, Personal Watch)
│   ├── api/                           # FastAPI routers (/claims, /scout, /trending, /brandshield, etc.)
│   ├── application/                   # Research pipelines & coordination workflows
│   ├── core/                          # Settings, security guards, error handling, structured logging
│   ├── data/                          # Runtime data stores & protected dossier archive
│   │   ├── WELFake_Dataset.xlsx       # Benchmark dataset
│   │   └── dossiers/                  # 2,312 immutable forensic investigation dossiers (PROTECTED)
│   ├── db/                            # SQLite / Supabase database client and schema
│   ├── evaluation/                    # ML and Cranfield retrieval evaluation metrics
│   ├── infrastructure/                # Acquisition router (NativeRouter), LLM Gateway, cache
│   ├── schemas/                       # Pydantic request/response data contracts
│   ├── services/                      # Source planning, capability health, identity resolution
│   └── workers/                       # Asynchronous background tasks
│
├── frontend/                          # ANALYST WORKBENCHES & ASSETS (PRESERVED)
│   ├── index.html                     # Landing portal & multi-intent investigation launcher
│   ├── scout-agent.html               # Scout Sentinel (Financial market anomaly console)
│   ├── trending-agent.html            # Trending Sentinel (Viral claim velocity console)
│   ├── brandshield-agent.html         # BrandShield Sentinel (Brand defense console)
│   ├── personal-watch-agent.html      # Personal Watch Sentinel (VIP protection console)
│   ├── operation-health.js            # TTL-bounded health polling with stale badge support
│   └── aegis-theme.css                # Aegis design system tokens
│
├── tests/                             # 787-TEST AUTOMATED REGRESSION SUITE (PRESERVED)
│   ├── unit/                          # 591 deterministic unit tests (0 network, 0 external I/O)
│   ├── integration/                   # Full FastAPI TestClient integration tests
│   ├── contract/                      # 16 recovered operations & public API contracts
│   ├── security/                      # SSRF, XSS, static path traversal security tests
│   ├── chaos/                         # Network timeout, retry bound, and error recovery tests
│   ├── benchmarks/                    # Learned reranker and performance regression tests
│   ├── evaluation/                    # Supervised baseline and Cranfield evaluation tests
│   ├── frontend/                      # Pure Node.js unit tests for operation-health.js
│   ├── retrieval_benchmark/           # Frozen Cranfield benchmark datasets (JSONL) (PROTECTED)
│   └── conftest.py                    # Pytest shared fixtures
│
├── scripts/                           # VALIDATION, EVALUATION & AUDIT RUNNERS (INDEXED)
│   ├── README.md                      # [NEW] Script taxonomy, usage guide, and categorization
│   ├── validate_release_candidate_smoke.py  # Phase 7.1 automated smoke validation (11 gates)
│   ├── validate_rollback_compatibility.py   # Database & dossier rollback verification
│   ├── evaluate_dataset.py            # Scientific benchmark CLI (WELFake & Reranker)
│   ├── evaluate_all_agents.py         # 4-Agent adversarial evaluation harness
│   ├── live_agent_smoke_test.py       # Live agent smoke harness (imported by tests)
│   ├── run_retrieval_quality_benchmark.py   # Retrieval benchmark runner (imported by tests)
│   └── ... (34 additional audit and diagnostic scripts)
│
├── docs/                              # DOCUMENTATION PORTAL & SYSTEM BLUEPRINTS (ORGANIZED)
│   ├── index.md                       # [UPDATED] Canonical documentation index
│   ├── ARCHITECTURE.md                # System topology and multi-agent fabric
│   ├── TESTING.md                     # Pytest testing runbook (787 tests)
│   ├── OPERATIONS.md                  # Operational runbook
│   ├── SECURITY.md                    # Security threat model and defense rules
│   ├── EVALUATION.md                  # Scientific evaluation methodology
│   ├── FEATURE_STATUS.md              # Feature status matrix
│   ├── agents/                        # Detailed specifications per agent
│   ├── api/                           # OpenAPI references and contract schemas
│   ├── architecture/                  # Architectural specs, ADRs, and Phase 6-7 reports
│   ├── development/                   # [EXPANDED] Developer guides, workspace map, script index
│   │   ├── WORKSPACE_INVENTORY.md     # Authoritative file inventory
│   │   ├── WORKSPACE_MAP.md           # Developer navigation and command reference
│   │   ├── SCRIPT_INDEX.md            # Comprehensive script catalog
│   │   ├── CLEANUP_CANDIDATE_REGISTER.md # Redundant/superseded file register
│   │   └── FILE_MIGRATION_MANIFEST.md # Manifest of updated/added files
│   ├── operations/                    # Deployment matrix, rollback guide, production runbook
│   ├── security/                      # Security reports and SSRF defense specifications
│   ├── testing/                       # CI coverage matrix, smoke test reports
│   └── archive/                       # Historical and superseded audit snapshots
│
├── research/                          # RESEARCH EXPERIMENTS & DATASETS (PROTECTED)
│   └── (250 files: historical benchmark logs, scraper bakeoffs, test datasets)
│
├── artifacts/                         # EMPIRICAL AUDIT EVIDENCE (PROTECTED)
│   └── (111 files: live audit logs, benchmark metrics, replay evidence)
│
└── scrapers/                          # STANDALONE SCRAPER LAB FRAMEWORK (PRESERVED)
    └── (18 files: laboratory canaries, schema drift detectors)
```

---

## 3. Structural Decisions & Component Lifecycle

### 3.1. What Stays Where It Is
- **`backend/` and `frontend/`**: Zero structural modifications. Both packages are tightly coupled to FastAPI routing, import graphs, and static serving.
- **`tests/`**: All test files and frozen benchmarks (`tests/retrieval_benchmark/*.jsonl`) remain strictly in place to prevent breaking test discovery or relative fixture loading.
- **`research/` and `artifacts/`**: Retained in full to preserve scientific provenance and audit trail.
- **`backend/data/dossiers/`**: Retained in full (contains 2,312 historical investigation dossiers).
- **`scrapers/`**: Retained as an isolated testing tool.

### 3.2. What Was Reorganized & Enhanced
- **`docs/index.md` & Root `README.md`**: Upgraded to reflect current Phase 7.1/7.2 reality: 787 tests, 16 recovered operations, Centralized LLM Gateway, Native Router, and Release Candidate validation.
- **`scripts/`**: Retained all 40 scripts at existing entry points to preserve import and CLI compatibility, while publishing a complete categorization guide in `scripts/README.md` and `docs/development/SCRIPT_INDEX.md`.
- **Cross-Platform Links**: All hardcoded Windows paths (`file:///c:/Users/Shaunak%20Rane/...`) in documentation converted to portable relative paths.
- **Developer Onboarding**: Added `AGENTS.md` and `docs/development/WORKSPACE_MAP.md` providing instant orientation for human and AI engineers.

### 3.3. What Remains for Backward Compatibility
- **`main.py` at root**: Serves as a convenient development launcher with dynamic port binding.
- **`scraper.py` at root**: CLI interface for the `scrapers/` laboratory framework.
- **`ARCHITECTURE.md`, `ENDPOINTS_MAP.md`, `ENV_SETUP.md` at root**: Preserved as quick-reference files at the repository root while being cross-linked from `docs/`.

### 3.4. What Is Classified for Future Owner Cleanup
- **`Gemini_rubrics.md` & `Rubrics.docx`**: Identified as career/market analysis rubrics rather than project code. Cataloged in `CLEANUP_CANDIDATE_REGISTER.md` for owner archiving.
- **Untracked Scratchpads**: `.txt` files at root (`final_report_prompt.txt`, `found_questions.txt`, `full_mission_mandate.txt`, `questions_full.txt`, `temp_user_prompts.txt`) are already ignored by `.gitignore`.
