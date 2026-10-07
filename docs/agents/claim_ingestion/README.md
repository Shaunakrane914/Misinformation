# AGENT 2: CLAIM INGESTION AGENT SPECIFICATION

**Agent:** Agent 2 — CLAIM INGESTION  
**Implementation:** [`backend/agents/claim_ingestion_agent.py`](file:///backend/agents/claim_ingestion_agent.py)  
**System:** Aegis Protocol

---

## 1. Architectural Mission & Identity

`ClaimIngestionAgent` is responsible for intake, claim parsing, normalization, and threat triage.

### Core Responsibilities
1. **Intake Processing**: Accept raw input strings, URLs, or news tickers submitted by users or upstream streaming feeds.
2. **Atomic Claim Decomposition**: Split compound claims into distinct, falsifiable atomic statements.
3. **Entity Extraction**: Identify core entities (companies, tickers, executives, products, public figures).
4. **Context Grounding**: Extract claim scope, geographical constraints, and temporal anchors.
5. **Initial Risk Scoring**: Assign priority and urgency ratings to guide downstream research depth.

---

## 2. Interface Contract

### Inputs
- `claim_text` (str): Raw claim or news report.
- `metadata` (dict): Source URL, submitter, timestamp, context tags.

### Outputs
- `ingested_claim`: Normalized claim object containing:
  - `claim_id`: Unique identifier.
  - `normalized_text`: Cleaned, unambiguous statement.
  - `atomic_claims`: List of atomic sub-claims.
  - `entities`: Extracted entities and financial tickers.
  - `priority`: Intake priority (`LOW`, `MEDIUM`, `HIGH`, `CRITICAL`).
