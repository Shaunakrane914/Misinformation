# AGENT 3: RESEARCH AGENT SPECIFICATION

**Agent:** Agent 3 — RESEARCH  
**Implementation:** [`backend/agents/research_agent.py`](file:///backend/agents/research_agent.py) & [`backend/services/research/`](file:///backend/services/research/)  
**System:** Aegis Protocol

---

## 1. Architectural Mission & Identity

`ResearchAgent` orchestrates comprehensive multi-source investigation once claims have been normalized by `ClaimIngestionAgent` and initial source discovery has been coordinated with `ScoutAgent`.

### Core Responsibilities
1. **Multi-Channel Evidence Gathering**: Query web, news, and specialized databases using `ResearchEngine`.
2. **Relevance Gating**: Run `RelevanceGate` and `EvidenceGate` to filter out irrelevant, duplicate, or unverified snippets before synthesis.
3. **Deep-Read Budget Execution**: Dynamically allocate research queries based on claim complexity and confidence.
4. **Evidence Lineage & Provenance**: Preserve source URLs, retrieval channels, timestamps, and confidence scores for every finding.

---

## 2. Interface Contract

### Inputs
- `claim`: Normalized claim object from `ClaimIngestionAgent`.
- `scout_evidence`: Initial market/news signals from `ScoutAgent`.

### Outputs
- `research_report`: Comprehensive evidence dossier containing:
  - `evidence_items`: Ranked, vetted evidence fragments.
  - `source_lineage`: Detailed provenance mapping.
  - `coverage_assessment`: Metrics on evidence breadth and source authority.
