# Aegis Protocol — Architecture Decision Records (ADR)

This directory contains Architecture Decision Records for the **Aegis Protocol** codebase.

Each record documents an architectural decision, its motivating context, evaluated alternatives, consequences, and current status following the standard lightweight ADR format.

> [!NOTE]
> ADRs 0001 through 0005 are currently **PROPOSED (Pending Review)**. They document architectural plans formulated in Phase 0 and will be marked as **ACCEPTED** only upon explicit review and approval as each refactoring milestone is executed.

---

## Index of Architecture Decision Records

| ADR | Title | Status | Date | Decision Summary |
| :--- | :--- | :--- | :--- | :--- |
| [ADR 0000](0000-template.md) | Architectural Decision Record Template | **Active** | 2026-10-09 | Standard template for proposing and recording architectural decisions. |
| [ADR 0001](0001-modular-monolith-boundaries.md) | Modular Monolith Layering & Architectural Boundaries | **PROPOSED (Pending Review)** | 2026-10-09 | Propose maintaining Aegis as a modular monolith with strict 4-tier layer isolation; avoid microservices and SPA frameworks. |
| [ADR 0002](0002-authoritative-acquisition-runtime.md) | Single Authoritative Acquisition Runtime & Deprecation of Shadow Scrapers | **PROPOSED (Pending Review)** | 2026-10-09 | Propose consolidating acquisition behind `AgentReachService` and splitting monolithic router into modular platform adapters. |
| [ADR 0003](0003-canonical-evidence-provenance-contracts.md) | Canonical Evidence Provenance, Lineage, and Replay Ledger Contracts | **PROPOSED (Pending Review)** | 2026-10-09 | Propose enforcing typed immutable `EvidenceItem` and `EvidenceFragment` contracts with hash-linked DAG auditability. |
| [ADR 0004](0004-llm-provider-configuration-boundaries.md) | Centralized LLM Provider Gateway and Validated Settings | **PROPOSED (Pending Review)** | 2026-10-09 | Propose unifying Gemini and multi-provider calls behind `LLMGateway` with centralized settings and deterministic offline mock injection. |
| [ADR 0005](0005-evaluation-fixture-artifact-retention.md) | Evaluation Benchmark Data Governance and Artifact Retention Policy | **PROPOSED (Pending Review)** | 2026-10-09 | Propose freezing 104-scenario / 416-candidate ground truth; classify retention across source, artifacts, and external archives. |

---

## ADR Lifecycle

1. **PROPOSED**: Under initial technical review and validation (current state for ADRs 0001–0005).
2. **ACCEPTED**: Approved by architecture review and actively guiding implementation.
3. **REJECTED**: Evaluated but not adopted (reasons preserved in context).
4. **SUPERSEDED**: Replaced by a subsequent ADR (links to superseding ADR).
5. **DEPRECATED**: Kept only for historical record; pattern no longer permissible.
