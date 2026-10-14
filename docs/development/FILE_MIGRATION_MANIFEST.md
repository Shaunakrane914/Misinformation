# Aegis Protocol — File Migration Manifest

**Phase:** 7.2 (Workspace Organization, Repository Hygiene & Safe Structural Consolidation)  
**Author:** Senior Software Architect & Repository Maintenance Engineer  
**Policy:** Non-Destructive Invariant Preservation  

---

## 1. Summary of Changes

To maintain strict scientific and operational reproducibility, Phase 7.2 avoided physical file renames of production modules or existing scripts. Instead, it:
1. Created missing canonical configuration and onboarding files (`LICENSE`, `AGENTS.md`).
2. Published directory-level catalogs (`scripts/README.md`) and indexes (`docs/development/SCRIPT_INDEX.md`).
3. Modernized root navigation (`README.md`, `CHANGELOG.md`, `docs/index.md`).
4. Corrected non-portable absolute file links across documentation.

---

## 2. File Action Manifest

| Original Path | New Path | Action / Change Reason | Existing Consumers | Compatibility Strategy | Verification Result |
| :--- | :--- | :--- | :--- | :--- | :---: |
| `LICENSE` | *(New File)* | Created standard MIT License matching `pyproject.toml`. Resolves broken link in `README.md`. | Developers, GitHub, packaging | Canonical text at root | **PASS** (Link verified) |
| `AGENTS.md` | *(New File)* | Created canonical AI coding agent orientation guide. | Autonomous agents (Codex, Antigravity, Claude) | Standard Markdown | **PASS** (Verified) |
| `scripts/README.md` | *(New File)* | Created in-folder development scripts catalog. | Developers inspecting `scripts/` | Standard Markdown | **PASS** (Verified) |
| `docs/development/WORKSPACE_INVENTORY.md` | *(New File)* | Complete directory-by-directory asset audit and classification. | Architects, release engineers | Standard Markdown | **PASS** (Verified) |
| `docs/architecture/PHASE7_2_WORKSPACE_STRUCTURE.md` | *(New File)* | Workspace architecture specification and structural consolidation policy. | Engineers, architects | Standard Markdown | **PASS** (Verified) |
| `docs/development/WORKSPACE_MAP.md` | *(New File)* | Quick-reference map for finding agent logic, routes, and verified commands. | Developers, AI agents | Standard Markdown | **PASS** (Verified) |
| `docs/development/SCRIPT_INDEX.md` | *(New File)* | Authoritative index and command guide for all 40 scripts. | Developers, release engineers | Standard Markdown | **PASS** (Verified) |
| `docs/development/CLEANUP_CANDIDATE_REGISTER.md` | *(New File)* | Formal register of non-essential files requiring future owner approval. | Repository owners | Standard Markdown | **PASS** (Verified) |
| `docs/testing/PHASE7_2_REGRESSION_REPORT.md` | *(New File)* | Full verification evidence for Phase 7.2. | Release QA gate | Standard Markdown | **PASS** (Verified) |
| `docs/architecture/PHASE7_2_WORKSPACE_ORGANIZATION_REPORT.md` | *(New File)* | Final executive deliverable for Phase 7.2. | Repository owners | Standard Markdown | **PASS** (Verified) |
| `README.md` | `README.md` | Updated test badge (787 tests), RC status, AGENTS.md link, quickstart commands. | All developers | In-place update | **PASS** (Verified) |
| `docs/index.md` | `docs/index.md` | Upgraded documentation portal to include all Phase 7/7.1/7.2 reports and guides. | All developers | In-place update | **PASS** (Verified) |
| `CHANGELOG.md` | `CHANGELOG.md` | Documented milestones from Phase 3.8 through Phase 4.2.0 (Phase 7.2). | Developers, release notes | In-place update | **PASS** (Verified) |
| `docs/**/*.md` (22 files) | `docs/**/*.md` | Converted hardcoded Windows-specific `file:///c:/Users/...` paths to relative links. | Cross-platform readers, CI | In-place update | **PASS** (Verified) |
| `scripts/*.py` (40 files) | `scripts/*.py` | **Preserved in place**. Categorized via `scripts/README.md` and `SCRIPT_INDEX.md`. | 5 test suites, CLI runners | 100% path preservation | **PASS** (Zero import breaks) |
| `backend/**/*` (226 files) | `backend/**/*` | **Preserved in place**. Core application, agents, routes, and dossiers. | FastAPI app, pytest | 100% path preservation | **PASS** (Zero import breaks) |
| `tests/**/*` (86 files) | `tests/**/*` | **Preserved in place**. All test files and frozen benchmark datasets. | `pytest`, CI runners | 100% path preservation | **PASS** (787/787 passing) |
| `artifacts/**/*` (111 files) | `artifacts/**/*` | **Preserved in place**. Historical audit evidence and benchmark metrics. | Audit reports | 100% path preservation | **PASS** (Immutable proof) |
| `research/**/*` (250 files) | `research/**/*` | **Preserved in place**. Research experiments and scraper bakeoffs. | Researchers | 100% path preservation | **PASS** (Protected data) |
| `scrapers/**/*` (18 files) | `scrapers/**/*` | **Preserved in place**. Standalone Scraper Laboratory framework. | `scraper.py` CLI | 100% path preservation | **PASS** (Protected tooling) |
