# Aegis Protocol — Architecture Decision Records (ADR)

This directory contains the authoritative Architecture Decision Records for the **Aegis Protocol** codebase.

Each record documents an architectural decision, its motivating context, evaluated alternatives, consequences, and current status following the standard lightweight ADR format.

---

## Index of Architecture Decision Records

| ADR | Title | Status | Date | Decision Summary |
| :--- | :--- | :--- | :--- | :--- |
| [ADR 0000](0000-template.md) | Architectural Decision Record Template | **Active** | 2026-10-09 | Standard template for proposing and recording architectural decisions. |
| [ADR 0001](0001-modular-monolith-boundaries.md) | Modular Monolith Layering & Architectural Boundaries | **Accepted** | 2026-10-09 | Maintain Aegis as a modular monolith with strict 4-tier layer isolation; avoid microservices and SPA frameworks. |
| [ADR 0002](0002-authoritative-acquisition-runtime.md) | Single Authoritative Acquisition Runtime & Deprecation of Shadow Scrapers | **Accepted** | 2026-10-09 | Consolidate acquisition behind `AgentReachService` and split monolithic router into modular platform adapters. |
| [ADR 0003](0003-canonical-evidence-provenance-contracts.md) | Canonical Evidence Provenance, Lineage, and Replay Ledger Contracts | **Accepted** | 2026-10-09 | Enforce typed immutable `EvidenceItem` and `EvidenceFragment` contracts with hash-linked DAG auditability. |
| [ADR 0004](0004-llm-provider-configuration-boundaries.md) | Centralized LLM Provider Gateway and Validated Settings | **Accepted** | 2026-10-09 | Unify Gemini and multi-provider calls behind `LLMGateway` with centralized settings and deterministic offline mock injection. |
| [ADR 0005](0005-evaluation-fixture-artifact-retention.md) | Evaluation Benchmark Data Governance and Artifact Retention Policy | **Accepted** | 2026-10-09 | Freeze 104-scenario / 416-candidate ground truth; classify retention across source, artifacts, and external archives. |

---

## ADR Lifecycle

1. **PROPOSED**: Under initial technical review and validation.
2. **ACCEPTED**: Approved by architecture review and actively guiding implementation.
3. **REJECTED**: Evaluated but not adopted (reasons preserved in context).
4. **SUPERSEDED**: Replaced by a subsequent ADR (links to superseding ADR).
5. **DEPRECATED**: Kept only for historical record; pattern no longer permissible.
