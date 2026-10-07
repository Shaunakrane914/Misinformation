# AGENT 5: COORDINATOR AGENT SPECIFICATION

**Agent:** Agent 5 — COORDINATOR  
**Implementation:** [`backend/agents/coordinator_agent.py`](file:///backend/agents/coordinator_agent.py)  
**System:** Aegis Protocol

---

## 1. Architectural Mission & Identity

`CoordinatorAgent` is the master orchestrator of the multi-agent Aegis Protocol.

### Core Responsibilities
1. **Pipeline Execution**: Route tasks across `ClaimIngestionAgent`, `ScoutAgent`, `ResearchAgent`, and `InvestigatorAgent`.
2. **Consensus Aggregation**: Reconcile outputs from multiple agents and ensure consensus validity.
3. **Unified Report Generation**: Produce standardized, audit-ready analytical reports according to the Aegis Unified Report Schema.
4. **Error Handling & Retries**: Monitor sub-agent timeouts, trigger adaptive fallback paths, and maintain pipeline resilience.

---

## 2. Interface Contract

### Inputs
- Task payload / verification request from API endpoints (`/api/claims`, `/api/analyze`, etc.).

### Outputs
- `UnifiedReport`: Standardized JSON/Markdown report containing:
  - Executive summary and final risk score.
  - Full source lineage and provenance trees.
  - Atomic claim verdicts and evidence citations.
  - Telemetry and performance benchmarks.
