# Aegis Protocol Documentation Portal

Welcome to the canonical documentation tree for **Aegis Protocol**, an autonomous enterprise intelligence and misinformation deconstruction system.

---

## 🏛️ System Architecture & Engineering Blueprints

- **[System Architecture Overview](architecture/OVERVIEW.md)**: High-level architectural topology, layers, and domain boundaries.
- **[Target Architecture Specification](architecture/TARGET_ARCHITECTURE.md)**: Modular monolith architecture, layering topology, and boundary rules.
- **[Codebase Inventory & Audit](architecture/CODEBASE_INVENTORY.md)**: Catalog of modules, lines of code, entrypoints, and dependencies.
- **[Dependency Map & Import Graph](architecture/DEPENDENCY_MAP.md)**: Import relationships, singleton state, and transitional compatibility shims.
- **[Phase 7 Architecture Consolidation Report](architecture/PHASE7_ARCHITECTURE_CONSOLIDATION_REPORT.md)**: Production architecture consolidation, route restoration, and hardening.
- **[Phase 7 Protected Integration Matrix](architecture/PHASE7_PROTECTED_INTEGRATION_MATRIX.md)**: Matrix preserving all 4 agents and 16 recovered operations.
- **[Phase 7.1 Release Candidate Report](architecture/PHASE7_1_RELEASE_CANDIDATE_REPORT.md)**: Release candidate validation, deployment readiness, and verification evidence.
- **[Phase 7.2 Workspace Structure Guide](architecture/PHASE7_2_WORKSPACE_STRUCTURE.md)**: Workspace organization, folder responsibilities, and structural consolidation policy.
- **[Architecture Decision Records (ADRs)](architecture/adr/README.md)**: Formal architecture decision records (ADRs 0001–0005) governing modularity, acquisition, and evidence retention.

---

## 💻 Developer Experience & Workspace Navigation

- **[Coding Agent Orientation (`AGENTS.md`)](../AGENTS.md)**: Canonical orientation guide for AI coding assistants and developers.
- **[Developer Workspace Map](development/WORKSPACE_MAP.md)**: Quick-reference map for finding agent logic, routes, tests, and running common commands.
- **[Script Index & Catalog](development/SCRIPT_INDEX.md)**: Authoritative index of all 40 development, benchmark, evaluation, and validation scripts.
- **[Workspace Inventory Report](development/WORKSPACE_INVENTORY.md)**: Directory-by-directory audit and classification of all tracked repository assets.
- **[Cleanup-Candidate Register](development/CLEANUP_CANDIDATE_REGISTER.md)**: Register of redundant, superseded, or owner-approval files.
- **[Environment Setup Guide](development/ENV_SETUP.md)**: Setup guide for API keys, provider credentials, and environment variables.
- **[Local Development & Runtime Guide](development/README.md)**: Virtual environments, runtime commands, coding standards, and branch workflow.

---

## 🚀 Operations, Configuration & Rollback

- **[Production Configuration Matrix](operations/PRODUCTION_CONFIGURATION_MATRIX.md)**: Required, feature-dependent, optional, and forbidden environment variables.
- **[V1 Operations Runbook](operations/V1_OPERATIONS_RUNBOOK.md)**: Comprehensive guide for startup, monitoring, maintenance, and failure recovery.
- **[Rollback Verification](operations/ROLLBACK_VERIFICATION.md)**: Automated validation of schema backward compatibility and preservation of 2,312 dossiers.
- **[Operations & Deployment Topology](operations/README.md)**: Containerization, `.dockerignore` containment policy, and health probes.

---

## 🛡️ Security Architecture & Reliability

- **[V1 Security & Operations Report](security/V1_SECURITY_AND_OPERATIONS_REPORT.md)**: Security review, SSRF defenses, static path traversal hardening, and telemetry redaction.
- **[Security Architecture Guide](security/README.md)**: Threat modeling, SSRF IP blocking ranges, URL sanitization rules, and prompt injection guards.
- **[Frontend Health Refresh Report](architecture/FRONTEND_HEALTH_REFRESH_REPORT.md)**: TTL-bounded (45s) capability caching, in-flight deduplication, and visibility revalidation.

---

## 🧪 Testing, CI Coverage & Benchmarks

- **[CI Coverage Matrix](testing/CI_COVERAGE_MATRIX.md)**: Comprehensive mapping of all 787 tests to CI jobs, plus full offline matrix specification.
- **[Isolated Smoke Test Report](testing/ISOLATED_SMOKE_TEST_REPORT.md)**: Isolated staging-like smoke validation across all 4 agents and 11 verification gates.
- **[Full CI Workflow Specification](ci/FULL_CI_WORKFLOW.yml)**: Complete, reproducible multi-Python CI workflow definition.
- **[Testing Runbook](TESTING.md)**: Pytest execution runbook and directory breakdown (787 tests).
- **[Scientific Evaluation Report](EVALUATION.md)**: WELFake classical ML baseline (88.50%), learned evidence reranker (MRR: 0.20 → 1.00), and Cranfield retrieval metrics.

---

## 🤖 Autonomous Sentinel Fleet & API Contracts

- **[REST API Reference](api/README.md)**: 7 modular FastAPI routers (`/api/claims`, `/api/scout`, `/api/trending`, `/api/brandshield`, `/api/personal-watch`, `/api/replay`, `/api/healthz`).
- **[API & Endpoint Route Map](api/ENDPOINTS_MAP.md)**: Complete route map for all FastAPI endpoints and frontend consoles.
- **[Autonomous Sentinel Fleet](agents/README.md)**: Specifications for Scout, Trending, BrandShield, Personal Watch, and Truth Tribunal.

---

## 🗄️ Historical & Audit Archive

- **[Audit Archive Index](archive/README.md)**: Authoritative index of historical project reviews, legacy roadmaps, and superseded milestone snapshots.
  - [`docs/audit/ARCHITECTURE_REVIEW.md`](audit/ARCHITECTURE_REVIEW.md) (`[SUPERSEDED]` — reflects earlier monolithic `main.py` state).
  - [`docs/audit/IMPROVEMENT_PLAN.md`](audit/IMPROVEMENT_PLAN.md) (`[SUPERSEDED]` — succeeded by Phase 0 `MIGRATION_PLAN.md`).
  - [`docs/audit/BASELINE_AUDIT.md`](audit/BASELINE_AUDIT.md) (`[SUPERSEDED]` — September 2026 discovery audit).
  - [`docs/audit/TESTING_BASELINE.md`](audit/TESTING_BASELINE.md) (`[SUPERSEDED]` — legacy 180-test audit).
  - [`docs/audit/FEATURE_VERIFICATION_MATRIX.md`](audit/FEATURE_VERIFICATION_MATRIX.md) (`[SUPERSEDED]` — preliminary matrix).
  - [`docs/audit/PROGRESS.md`](audit/PROGRESS.md) (`[SUPERSEDED]` — legacy sprint tracker).
  - [`docs/audit/SECURITY_FINDINGS.md`](audit/SECURITY_FINDINGS.md) (`[SUPERSEDED]` — preliminary vulnerability audit).
