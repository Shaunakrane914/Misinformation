# AEGIS PROTOCOL: MULTI-AGENT SPECIFICATION ARCHITECTURE

This directory contains the formal architectural specifications, data contracts, and implementation guidelines for each agent within the **Aegis Protocol**.

These per-agent specifications include historical and aspirational designs.
For the currently executed claim path, four specialist scan contracts and
Phase 8 acceptance boundaries, use [Current State](../CURRENT_STATE.md),
the [production-path trace](../architecture/PHASE8_INVESTIGATION_PATH_TRACE.md)
and the [current API map](../api/CURRENT_ENDPOINTS.md). A listed source or
agent role below is not proof that it ran in a given investigation.

---

## 1. Agent Directory Map

| Agent | Directory | Python Implementation | Core Responsibility |
|---|---|---|---|
| **Agent 1: SCOUT** | [`scout/`](../../docs/agents/scout/) | [`ScoutAgent`](../../backend/agents/scout_agent.py) | Trading & news intelligence, catalyst discovery, empirical zero-auth source acquisition, financial fact extraction. |
| **Agent 2: CLAIM INGESTION** | [`claim_ingestion/`](../../docs/agents/claim_ingestion/) | [`ClaimIngestionAgent`](../../backend/agents/claim_ingestion_agent.py) | Intake, claim normalization, atomic claim decomposition, deduplication, and initial threat scoring. |
| **Agent 3: RESEARCH** | [`research/`](../../docs/agents/research/) | [`ResearchAgent`](../../backend/agents/research_agent.py) | Multi-channel evidence gathering, deep-read budget execution, relevance gating, and research synthesis. |
| **Agent 4: INVESTIGATOR** | [`investigator/`](../../docs/agents/investigator/) | [`InvestigatorAgent`](../../backend/agents/investigator_agent.py) | Adversarial cross-examination, investigative verification, logical consistency checking, and verdict assignment. |
| **Agent 5: COORDINATOR** | [`coordinator/`](../../docs/agents/coordinator/) | [`CoordinatorAgent`](../../backend/agents/coordinator_agent.py) | Workflow orchestration, inter-agent message passing, task routing, and unified report compilation. |
| **Specialist: TRENDING** | [`trending/`](../../docs/agents/trending/) | [`TrendingAgent`](../../backend/agents/trending_agent.py) | Real-time social anomaly detection, viral claim tracking, velocity calculation, and trend monitoring. |
| **Specialist: BRANDSHIELD**| [`brandshield/`](../../docs/agents/brandshield/) | [`BrandshieldAgent`](../../backend/agents/brandshield_agent.py) | Corporate reputation protection, impersonation detection, trademark infringement, and executive threat analysis. |
| **Specialist: PERSONAL** | [`personal/`](../../docs/agents/personal/) | [`PersonalAgent`](../../backend/agents/personal_agent.py) | Individual executive defense, doxxing detection, targeted harassment mitigation, and VIP threat intelligence. |

---

## 2. Multi-Agent Pipeline & Data Flow

```text
                           USER / STREAM INGESTION
                                      │
                                      ▼
                           [ClaimIngestionAgent]
                         (Decompose & Normalize)
                                      │
                                      ▼
                        [ScoutAgent] (Agent 1)
                     Market Discovery & Acquisition
                    (Proprietary ScoutSourceEngine)
                                      │
                                      ▼
                               [ResearchAgent]
                    Multi-Source Evidence Synthesis
                                      │
                                      ▼
                            [InvestigatorAgent]
                    Adversarial Cross-Examination
                                      │
                                      ▼
                            [CoordinatorAgent]
                      Final Consensus & Unified Report
```

---

## 3. Strict Boundary Rules

1. **Scout does not verify claims**: Scout detects catalysts, discovers sources, and extracts financial facts. Verification is reserved for `InvestigatorAgent`.
2. **Scout is not a generic crawler**: Scout uses its internal `ScoutSourceEngine` designed around the empirical zero-auth transport and semantic correctness audits.
3. **Evidence Integrity**: All evidence collected across agents must preserve provenance, timestamps, retrieval modes, and zero-auth status (`authenticated = False`).
