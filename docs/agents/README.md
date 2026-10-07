# AEGIS PROTOCOL: MULTI-AGENT SPECIFICATION ARCHITECTURE

This directory contains the formal architectural specifications, data contracts, and implementation guidelines for each agent within the **Aegis Protocol**.

---

## 1. Agent Directory Map

| Agent | Directory | Python Implementation | Core Responsibility |
|---|---|---|---|
| **Agent 1: SCOUT** | [`scout/`](file:///docs/agents/scout/) | [`ScoutAgent`](file:///backend/agents/scout_agent.py) | Trading & news intelligence, catalyst discovery, empirical zero-auth source acquisition, financial fact extraction. |
| **Agent 2: CLAIM INGESTION** | [`claim_ingestion/`](file:///docs/agents/claim_ingestion/) | [`ClaimIngestionAgent`](file:///backend/agents/claim_ingestion_agent.py) | Intake, claim normalization, atomic claim decomposition, deduplication, and initial threat scoring. |
| **Agent 3: RESEARCH** | [`research/`](file:///docs/agents/research/) | [`ResearchAgent`](file:///backend/agents/research_agent.py) | Multi-channel evidence gathering, deep-read budget execution, relevance gating, and research synthesis. |
| **Agent 4: INVESTIGATOR** | [`investigator/`](file:///docs/agents/investigator/) | [`InvestigatorAgent`](file:///backend/agents/investigator_agent.py) | Adversarial cross-examination, investigative verification, logical consistency checking, and verdict assignment. |
| **Agent 5: COORDINATOR** | [`coordinator/`](file:///docs/agents/coordinator/) | [`CoordinatorAgent`](file:///backend/agents/coordinator_agent.py) | Workflow orchestration, inter-agent message passing, task routing, and unified report compilation. |
| **Specialist: TRENDING** | [`trending/`](file:///docs/agents/trending/) | [`TrendingAgent`](file:///backend/agents/trending_agent.py) | Real-time social anomaly detection, viral claim tracking, velocity calculation, and trend monitoring. |
| **Specialist: BRANDSHIELD**| [`brandshield/`](file:///docs/agents/brandshield/) | [`BrandshieldAgent`](file:///backend/agents/brandshield_agent.py) | Corporate reputation protection, impersonation detection, trademark infringement, and executive threat analysis. |
| **Specialist: PERSONAL** | [`personal/`](file:///docs/agents/personal/) | [`PersonalAgent`](file:///backend/agents/personal_agent.py) | Individual executive defense, doxxing detection, targeted harassment mitigation, and VIP threat intelligence. |

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
