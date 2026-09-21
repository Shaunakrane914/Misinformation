# Aegis Protocol — Master Improvement Plan (Phases 0 - 8)
**Branch**: `aegis/full-project-improvement`  
**Execution Horizon**: Phased Full-Repository Transformation

---

## Phase Overview

### Phase 0: Discovery & Baseline Audit (COMPLETED)
- [x] Create dedicated branch `aegis/full-project-improvement`.
- [x] Perform full repository code audit across backend, agents, scrapers, models, databases, frontends, and configuration.
- [x] Create initial audit artifacts in `docs/audit/`.

### Phase 1: Critical Correctness & Security
- [ ] Fix configuration credential drift in `backend/config.py` (`SUPABASE_SERVICE_ROLE_KEY` support).
- [ ] Implement robust SSRF protection module `backend/services/url_validator.py` to sanitize all external URLs.
- [ ] Add DDL definitions for `claims` and `evidence` in `backend/setup_aegis_db.sql`.
- [ ] Implement HTML escaping utility in frontend scripts to eliminate XSS vectors.

### Phase 2: Evidence-Grounded Verification Pipeline
- [ ] Upgrade `ClaimIngestionAgent` with Unicode NFC normalization, whitespace collapsing, length limits, and deterministic ID generation.
- [ ] Expand Pydantic schemas in `backend/schemas/claim_schemas.py` to support 6-state taxonomy (`True`, `False`, `Misleading`, `Partially True`, `Unverified`, `Insufficient Evidence`) with structured evidence citations, provenance, and timestamps.
- [ ] Centralize Gemini client logic in `backend/services/gemini_service.py` with exponential backoff, jitter, and mock provider support.
- [ ] Harden prompt templates in `ResearchAgent` and `InvestigatorAgent` with strict `<untrusted_evidence>` container tags against prompt injection.

### Phase 3: Testing & Evaluation Framework
- [ ] Setup `pytest.ini` and scaffold `tests/unit/`, `tests/integration/`, `tests/security/`.
- [ ] Write unit tests for normalization, schemas, instruments, and error paths.
- [ ] Write integration tests for API endpoints using FastAPI TestClient and mock LLM provider.
- [ ] Implement reproducible ML evaluation harness `scripts/evaluate_dataset.py` running against `backend/data/WELFake_Dataset.xlsx` (computing Accuracy, Precision, Recall, Macro-F1, and Confusion Matrix).

### Phase 4: Agent & Model Reliability
- [ ] Refactor Threat Lab instruments (`Mandelbrot`, `Hawkes`, `Consensus`) into `backend/services/threat_instruments.py` with rigorous mathematical handling and explicit experimental labeling for simulations.
- [ ] Implement real ensemble voting with outlier trimming for consensus arbitration.
- [ ] Add timeout and failure isolation to agent orchestration in `backend/main.py`.

### Phase 5: Data, API, and Frontend Quality
- [ ] Update frontend truth dossier display in `frontend/submit.html` to render structured supporting/refuting citations and evidence limitations.
- [ ] Ensure all frontend dashboards safely handle loading, empty, and error states without crashing.

### Phase 6: Observability & Operational Readiness
- [ ] Add structured request timing and correlation IDs (`X-Request-ID`).
- [ ] Verify local startup command `uvicorn main:app --reload` and environment reproducibility.

### Phase 7: Documentation & Portfolio
- [ ] Create `docs/TESTING.md`, `docs/EVALUATION.md`, `docs/SECURITY.md`, `docs/OPERATIONS.md`, `docs/FEATURE_STATUS.md`.
- [ ] Synchronize `README.md` and `ARCHITECTURE.md` with verified implementation reality.

### Phase 8: Final Regression & Rubric Scoring
- [ ] Run complete test suite and capture test results.
- [ ] Score repository against 100-point rubric with concrete code and test citations.
- [ ] Produce final engineering report.
