# Aegis Protocol Documentation Portal

Welcome to the canonical documentation tree for **Aegis Protocol**, an autonomous enterprise intelligence and misinformation deconstruction system.

---

## 🏛️ Architecture & Engineering Blueprint

- **[Codebase Inventory & Audit](architecture/CODEBASE_INVENTORY.md)**: Authoritative catalog of all modules, lines of code, entrypoints, dependencies, and identified defects.
- **[Target Architecture Specification](architecture/TARGET_ARCHITECTURE.md)**: Target modular monolith architecture, layering topology, and boundary rules.
- **[Dependency Map & Import Graph](architecture/DEPENDENCY_MAP.md)**: Concrete import relationships, singleton state, and transitional compatibility shims.
- **[Phased Migration Plan](architecture/MIGRATION_PLAN.md)**: Phased engineering roadmap (Phases 0 through 7) with explicit acceptance gates.
- **[Architecture Decision Records (ADRs)](architecture/adr/README.md)**: Accepted architectural records governing modularity, acquisition, evidence contracts, and data retention.

---

## 📚 Canonical Topic Directories

- **[Development & Runtime Guide](development/README.md)**: Local developer setup, virtual environments, runtime commands, coding standards, and branch workflow.
- **[REST API Reference](api/README.md)**: 7 modular FastAPI routers (`/api/claims`, `/api/scout`, `/api/trending`, `/api/brandshield`, `/api/personal`, `/api/replay`, `/api/healthz`), request/response schemas, error handling.
- **[Autonomous Sentinel Fleet](agents/README.md)**: Sentinel specifications for Scout 2.0, Trending 2.0, BrandShield 2.0, Personal Watch 2.0, and Investigator/Research engines.
- **[Operations & Deployment](operations/README.md)**: Deployment topology, containerization, `.dockerignore` containment policy, health probes, environment variable matrix.
- **[Security Architecture](security/README.md)**: SSRF defense firewall, prompt injection encapsulation, cryptographic Replay Ledger, XSS protection.
- **[Testing & Quality Assurance](testing/README.md)**: Test hierarchy, 530 passing automated tests, chaos fault injection, and zero-regression standards.
- **[Evaluation & Scientific Baselines](evaluation/README.md)**: 104-scenario Cranfield retrieval benchmark, WELFake classical ML baseline (88.50%), and learned reranker evaluation.

---

## 🔬 Core System Guides & Specifications

- **[System Architecture Overview](ARCHITECTURE.md)**: System topology, multi-agent fabric, and 3-tier progressive disclosure UI.
- **[Feature Status & Truth Matrix](FEATURE_STATUS.md)**: Current operational status across intelligence sentinels and acquisition channels (verified against 530 tests).
- **[Testing Runbook](TESTING.md)**: Pytest execution runbook and directory breakdown.
- **[Scientific Evaluation Report](EVALUATION.md)**: Mathematical formulations, calibration diagrams, ablation results, and leakage elimination.
- **[Operational Runbook](OPERATIONS.md)**: Step-by-step local setup, Docker build guide, and health telemetry.
- **[Security Hardening Guide](SECURITY.md)**: SSRF IP blocking ranges, URL sanitization rules, and threat models.

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
