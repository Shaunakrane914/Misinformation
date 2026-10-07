# AGENT 4: INVESTIGATOR AGENT SPECIFICATION

**Agent:** Agent 4 — INVESTIGATOR  
**Implementation:** [`backend/agents/investigator_agent.py`](file:///backend/agents/investigator_agent.py)  
**System:** Aegis Protocol

---

## 1. Architectural Mission & Identity

`InvestigatorAgent` is the truth-verification and cross-examination core of the Aegis Protocol.

### Core Responsibilities
1. **Adversarial Verification**: Challenge claims and evidence against contrarian hypotheses.
2. **Fact Consistency Analysis**: Detect internal contradictions between claims and source excerpts.
3. **Epistemic Classification**: Categorize claims into explicit states (`CONFIRMED`, `UNCONFIRMED`, `DEBUNKED`, `CONTRADICTED`, `FABRICATED`).
4. **Confidence Calibration**: Compute mathematical confidence intervals based on evidence quality, source diversity, and corroboration strength.

---

## 2. Interface Contract

### Inputs
- `claim`: Target claim statement.
- `evidence_dossier`: Evidence gathered by `ResearchAgent` and `ScoutAgent`.

### Outputs
- `investigation_verdict`:
  - `status`: Definitive verdict (`TRUE`, `FALSE`, `MISLEADING`, `UNVERIFIED`).
  - `confidence`: Calibrated confidence score (0.0 to 1.0).
  - `justification`: Structured explanation citing specific verified evidence IDs.
  - `contradictions`: Explicit list of identified contradictions.
