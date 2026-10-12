# Aegis Protocol Documentation Portal

Welcome to the canonical documentation tree for **Aegis Protocol**, an autonomous enterprise intelligence and misinformation deconstruction system.

## Next coding agent: start here

Read the [agent handoff index](handoffs/README.md) before continuing the uncommitted architecture-remediation work. It links the implementation map, decision rationale, recorded execution work log, exact test commands and known blockers. Historical phase reports below remain snapshots; they do not override newer code or validation evidence.

Current verification milestone: [Phase 7.4 remediation verification and recovery assessment](architecture/PHASE7_4_REMEDIATION_VERIFICATION.md).

---

## 🏛️ System Architecture & Engineering Blueprints

- **[System Architecture Overview](architecture/OVERVIEW.md)**: High-level architectural topology, layers, and domain boundaries.
- **[Target Architecture Specification](architecture/TARGET_ARCHITECTURE.md)**: Modular monolith architecture, layering topology, and boundary rules.
- **[Codebase Inventory & Audit](architecture/CODEBASE_INVENTORY.md)**: Catalog of modules, lines of code, entrypoints, and dependencies.
- **[Dependency Map & Import Graph](architecture/DEPENDENCY_MAP.md)**: Import relationships, singleton state, and transitional compatibility shims.
- **[Phase 7 Architecture Consolidation Report](architecture/PHASE7_ARCHITECTURE_CONSOLIDATION_REPORT.md)**: Production architecture consolidation, route restoration, and hardening.
- **[2026-10-12 Architecture Review Remediation](architecture/ARCHITECTURE_REVIEW_REMEDIATION_2026-10-12.md)**: Current local fixes, verification evidence, compatibility changes and remaining limitations.
- **[Phase 7.4 Remediation Verification](architecture/PHASE7_4_REMEDIATION_VERIFICATION.md)**: Security closeout, protected dossier inventory and hosted-CI evidence boundary.
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
- **[Rollback Verification](operations/ROLLBACK_VERIFICATION.md)**: Fresh-process persistence and historical-reader checks, with explicit protected-archive integrity failures.
- **[Operations & Deployment Topology](operations/README.md)**: Containerization, `.dockerignore` containment policy, and health probes.

---

## 🛡️ Security Architecture & Reliability

- **[V1 Security & Operations Report](security/V1_SECURITY_AND_OPERATIONS_REPORT.md)**: Security review, SSRF defenses, static path traversal hardening, and telemetry redaction.
- **[Security Architecture Guide](security/README.md)**: Threat modeling, SSRF IP blocking ranges, URL sanitization rules, and prompt injection guards.
- **[Frontend Health Refresh Report](architecture/FRONTEND_HEALTH_REFRESH_REPORT.md)**: TTL-bounded (45s) capability caching, in-flight deduplication, and visibility revalidation.

---

## 🧪 Testing, CI Coverage & Benchmarks

- **[Research & Evaluation Artifacts Catalog](../artifacts/README.md)**: Authoritative index of all 17 milestone audit suites and benchmark evidence files.
- **[CI Coverage Matrix](testing/CI_COVERAGE_MATRIX.md)**: Configured offline/frontend/frozen-data CI gates and their evidence limitations; counts are discovered dynamically.
- **[Isolated Smoke Test Report](testing/ISOLATED_SMOKE_TEST_REPORT.md)**: Isolated staging-like smoke validation across all 4 agents and 11 verification gates.
- **[CI Workflow Pointer](ci/FULL_CI_WORKFLOW.yml)**: Retired duplicate specification; points to the active workflow.
- **[Testing Runbook](TESTING.md)**: General pytest runbook; use the dated handoff for current remediation commands and observed results.
- **[Scientific Evaluation Report](EVALUATION.md)**: WELFake classical ML baseline (88.50%), learned evidence reranker (MRR: 0.20 → 1.00), and Cranfield retrieval metrics.

---

## 🎬 Project Showcase & Launch Teaser

- **[Showcase Brief & Storyboard](showcase/composition-brief.md)**: Storyboard scenes, soundtrack attribution, and composition design.
- **[Launch Copy Studio](showcase/share-copy.md)**: Omnichannel launch copy for 𝕏/Twitter, LinkedIn, Discord, and Reddit.
- **[Production Teaser Plan](showcase/brag-plan.md)**: 20-second cinematic film specification and render parameters.


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
