# Aegis Protocol Documentation Portal

Welcome to the canonical documentation tree for **Aegis Protocol**, an autonomous enterprise intelligence and misinformation deconstruction system.

---

## Architecture & Engineering Blueprint

- **[Codebase Inventory & Audit](architecture/CODEBASE_INVENTORY.md)**: Authoritative catalog of all modules, lines of code, entrypoints, dependencies, and identified defects.
- **[Target Architecture Specification](architecture/TARGET_ARCHITECTURE.md)**: Target modular monolith architecture, layering topology, and boundary rules.
- **[Dependency Map & Import Graph](architecture/DEPENDENCY_MAP.md)**: Concrete import relationships, singleton state, and transitional compatibility shims.
- **[Phased Migration Plan](architecture/MIGRATION_PLAN.md)**: Phased engineering roadmap (Phases 0 through 7) with explicit acceptance gates.
- **[Architecture Decision Records (ADRs)](architecture/adr/README.md)**: Accepted architectural records governing modularity, acquisition, evidence contracts, and data retention.

---

## Core System Documentation

- **[System Architecture](ARCHITECTURE.md)**: System topology, multi-agent fleet overview, and progressive disclosure UI.
- **[Feature Status & Capabilities](FEATURE_STATUS.md)**: Current operational status across intelligence sentinels and acquisition channels.
- **[Testing & Verification Guide](TESTING.md)**: Test execution instructions, regression test baseline (**530 passing tests**), and chaos fault injection.
- **[Evaluation & Benchmarks](EVALUATION.md)**: 104-scenario / 416-candidate frozen retrieval benchmark and Cranfield metrics.
- **[Operational Runbook](OPERATIONS.md)**: Deployment instructions, health probes, Docker setup, and environment variables.
- **[Security Policy & SSRF Defense](SECURITY.md)**: Network isolation, URL validation, and cryptographic hash verification.

---

## Historical & Audit Archive

> [!NOTE]
> Documents under `docs/audit/` represent historical project review snapshots from earlier milestones and are preserved for audit context:
> - [`docs/audit/ARCHITECTURE_REVIEW.md`](audit/ARCHITECTURE_REVIEW.md) (`[SUPERSEDED]` — reflects earlier monolithic `main.py` state).
> - [`docs/audit/IMPROVEMENT_PLAN.md`](audit/IMPROVEMENT_PLAN.md) (`[SUPERSEDED]` — succeeded by Phase 0 `MIGRATION_PLAN.md`).
