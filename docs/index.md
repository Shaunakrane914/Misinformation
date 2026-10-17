# Aegis Protocol Documentation Portal

Welcome to the canonical documentation tree for **Aegis Protocol**, an autonomous enterprise intelligence and misinformation deconstruction system.

## Next coding agent: start here

Current development checkpoint: [source-text pipeline handoff](handoffs/2026-10-17_SOURCE_TEXT_PIPELINE.md), [52-operation review](testing/SOURCE_TEXT_PIPELINE_REVIEW_2026-10-17.md) and [actual evidence](testing/evidence/2026-10-17_source_text_pipeline/README.md). Local 1,309 full / 1,101 fast cases pass; eight of twelve native entity inputs still acquire no records. This dedicated branch is not merged/deployed or a completed Phase 9. [Previous remediation evidence](testing/PHASE9_REMEDIATION_VERIFICATION_2026-10-16.md) remains historical context.

Next-phase proposal: [Phase 9 — Evidence Depth & Strategic Investigation Workbench](architecture/PHASE9_EVIDENCE_DEPTH_AND_STRATEGIC_WORKBENCH_PLAN.md), dated 2026-10-15. This is a plan, not implemented capability or Phase 8 acceptance.

Latest implementation: [Phase 9 acquisition checkpoint](handoffs/2026-10-15_PHASE9_ACQUISITION_DEPTH.md), [source extraction runbook](operations/PHASE9_EXTRACTION_RUNBOOK.md), [system guide](SYSTEM_GUIDE.md) and [current code map](development/CURRENT_CODE_MAP.md). This bounded implementation does not accept the entire Phase 9 plan.

Start with the [dated current state](CURRENT_STATE.md) and [agent handoff
index](handoffs/README.md), then inspect the checked-out branch and commit.
Phase 8A has bounded live proof; 8B–8F remain partial and release acceptance
is not established. Read the [independent review](architecture/PHASE8_INDEPENDENT_REVIEW_2026-10-14.md). Historical phase reports below remain snapshots rather than current
release or deployment approval.

---

## 🏛️ System Architecture & Engineering Blueprints

- **[System Architecture Overview](architecture/OVERVIEW.md)**: High-level architectural topology, layers, and domain boundaries.
- **[Target Architecture Specification](architecture/TARGET_ARCHITECTURE.md)**: Modular monolith architecture, layering topology, and boundary rules.
- **[Codebase Inventory & Audit](architecture/CODEBASE_INVENTORY.md)**: Catalog of modules, lines of code, entrypoints, and dependencies.
- **[Dependency Map & Import Graph](architecture/DEPENDENCY_MAP.md)**: Import relationships, singleton state, and transitional compatibility shims.
- **[Phase 7 Architecture Consolidation Report](architecture/PHASE7_ARCHITECTURE_CONSOLIDATION_REPORT.md)**: Production architecture consolidation, route restoration, and hardening.
- **[2026-10-12 Architecture Review Remediation](architecture/ARCHITECTURE_REVIEW_REMEDIATION_2026-10-12.md)**: Current local fixes, verification evidence, compatibility changes and remaining limitations.
- **[Phase 7.4 Remediation Verification](architecture/PHASE7_4_REMEDIATION_VERIFICATION.md)**: Security closeout, protected dossier inventory and hosted-CI evidence boundary.
- **[Phase 8 Investigation Path Trace](architecture/PHASE8_INVESTIGATION_PATH_TRACE.md)**: Executed claim-to-frontend path, ownership boundaries and remaining risks.
- **[Phase 8A Real Acquisition Verification](architecture/PHASE8A_REAL_ACQUISITION_VERIFICATION.md)**: Live proof and honest depth classifications for all 16 protected operations.
- **[Phase 7 Protected Integration Matrix](architecture/PHASE7_PROTECTED_INTEGRATION_MATRIX.md)**: Matrix preserving all 4 agents and 16 recovered operations.
- **[Phase 7.1 Release Candidate Report](architecture/PHASE7_1_RELEASE_CANDIDATE_REPORT.md)**: Release candidate validation, deployment readiness, and verification evidence.
- **[Phase 7.2 Workspace Structure Guide](architecture/PHASE7_2_WORKSPACE_STRUCTURE.md)**: Workspace organization, folder responsibilities, and structural consolidation policy.
- **[Architecture Decision Records (ADRs)](architecture/adr/README.md)**: Formal architecture decision records (ADRs 0001–0005) governing modularity, acquisition, and evidence retention.

---

## 💻 Developer Experience & Workspace Navigation

- **[Coding Agent Orientation (`AGENTS.md`)](../AGENTS.md)**: Canonical orientation guide for AI coding assistants and developers.
- **[Developer Workspace Map](development/WORKSPACE_MAP.md)**: Quick-reference map for finding agent logic, routes, tests, and running common commands.
- **[Script Index & Catalog](development/SCRIPT_INDEX.md)**: Maintained command index; its Phase 7.2 script count is explicitly historical.
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
- **[Production Teaser Plan](showcase/brag-plan.md)**: Historical film specification, not current product acceptance evidence.


---

## 🤖 Autonomous Sentinel Fleet & API Contracts

- **[Current API Route Map](api/CURRENT_ENDPOINTS.md)**: Decorator-backed routes and contract boundaries for this branch; runtime OpenAPI is exhaustive.
- **[Historical API Reference](api/README.md)** and **[proposed endpoint map](api/ENDPOINTS_MAP.md)**: Retained snapshots that include unregistered routes; do not implement clients from them.
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
