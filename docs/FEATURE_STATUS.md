# Aegis Protocol — Feature Status & Implementation Matrix

**Document origin:** Phase 1 architecture baseline (530-test snapshot).  
**Current status:** [Phase 8 dated acceptance matrix](CURRENT_STATE.md); 1,051 local offline tests and exact-commit hosted CI are documented there.  
**Scientific status:** The prior 93.33% mock-circular metric remains retired. Historical ML/reranking scores below are not live verdict accuracy.

> This matrix originated in an earlier phase. The 530-test baseline and
> production labels below are historical, not current live-provider or UI
> acceptance evidence. Consult the [latest handoff](handoffs/README.md) and
> [Phase 8 acquisition matrix](architecture/PHASE8B_MAXIMUM_EXTRACTION_SCHEMA_MATRIX.md)
> for dated status. The research and investigator rows below were corrected
> after removing their unsupported browser-side dossier paths.

---

## Standard Taxonomy

- **Production / Implemented**: Code exists, is tested with real data/contracts, and executes deterministically in runtime.
- **Tested**: Verified with automated unit, integration, or property-based tests in CI.
- **Simulated**: Algorithmic or mathematical demonstrations (e.g. point processes, synthetic power-law distributions); explicitly returns `is_simulation: True`.
- **Experimental**: Functional research prototype; subject to ongoing calibration or optional external API keys.
- **Research / Ready**: Standardized evaluation adapters (e.g., AVeriTeC) waiting for local data download; honestly reports `NOT RUN`.
- **Planned**: Roadmap initiative; not claimed as active production capability.

---

## Historical implementation matrix

The rows below describe code presence and older offline tests, not current
live-provider health, security accreditation, frontend acceptance or release
readiness. For current 8A–8F gate outcomes and limitations, use
[Current State](CURRENT_STATE.md). In particular, “production/tested” in an
older row must not be read as a deployment claim.

| Subsystem / Feature | Taxonomy Tier | Verified Evidence | Limitations & Technical Boundaries |
| :--- | :--- | :--- | :--- |
| **Claim Ingestion & Normalization** | **Production / Tested** | `backend/agents/claim_ingestion_agent.py`, `tests/unit/test_normalization_and_dedup.py` | Full Unicode NFC normalization, whitespace collapsing, length enforcement. |
| **Database-Backed Deduplication** | **Production / Tested** | `backend/db/database.py`, `ClaimIngestionAgent.ingest()` | SHA-256 hash idempotency checks prevent duplicate investigations. |
| **6-Verdict Classification Taxonomy** | **Production / Tested** | `backend/schemas/claim_schemas.py`, `InvestigatorAgent` | `True`, `False`, `Misleading`, `Partially True`, `Unverified`, `Insufficient Evidence`. |
| **Learned Evidence Reranker** | **Production / Tested** | `backend/evaluation/reranker.py`, `tests/evaluation/test_evaluation_framework.py` | 7-feature linear model trained via pairwise cross-entropy on train pairs, evaluated on held-out test queries (MRR 0.20 → 1.00, 0.26ms p50 latency). |
| **Supervised Classical ML Baseline** | **Production / Tested** | `backend/evaluation/baselines.py`, `tests/evaluation/test_evaluation_framework.py` | Deduplicated TF-IDF (10k) + L2 Logistic Regression on held-out WELFake split: 88.50% accuracy, 0.8850 F1 ($N=2,948$; 800 duplicate titles removed pre-split; 0 duplicate content across train/val/test). |
| **Agent Reach Capability Layer** | **Implemented / sampled live proof** | `backend/infrastructure/acquisition/`, `tests/unit/test_recovered_operation_routes.py` | Sixteen protected routes plus auxiliary channels; coverage and content depth vary. See the [8B field matrix](architecture/PHASE8B_MAXIMUM_EXTRACTION_SCHEMA_MATRIX.md). |
| **SSRF Defense & URL Validator** | **Production / Tested** | `backend/services/url_validator.py`, `tests/security/` | Pre-fetch DNS resolution blocks private RFC1918, loopback, and cloud metadata (169.254.169.254). |
| **Frontend source-display guards** | **Implemented / partially verified** | `frontend/safe-source-url.js`, `tests/frontend/` | Agent pages escape dynamic text and block unsafe display URLs. This is not a global guarantee for every historical page or a substitute for backend SSRF checks. |
| **Centralized Gemini Service** | **Production / Tested** | `backend/services/gemini_service.py` | Multi-key rotation, jittered exponential backoff. Scientific mode cleanly blocks rather than falling back to mock. |
| **India Multilingual Track** | **Research / Prototype** | `backend/evaluation/datasets/india_track.py` | Curated gold prototype across English, Hindi, Marathi, and Hinglish (14 claims across 5 civic domains with accredited institutional provenance). |
| **Investigator component** | **Integrated / Partially Verified** | `backend/agents/investigator_agent.py`, `frontend/investigator-agent.html` | Runs within claim verification; browser page is an entry gateway, not an independently verified dossier generator. Verdict quality needs evidence-entailment evaluation. |
| **Research component** | **Integrated / Partially Verified** | `backend/agents/research_agent.py`, `frontend/research-agent.html` | Runs within claim verification; browser page is an entry gateway. No standalone `/api/research/query` exists. Source-linked extraction and reading-list claims need evaluation. |
| **Scout Financial Workbench** | **Implemented / offline-tested** | `backend/agents/scout_agent.py`, `frontend/scout-agent.html` | Market and disclosure signals depend on actual available sources; no guaranteed real-time quote feed. |
| **Trending Viral Workbench** | **Implemented / offline-tested** | `backend/agents/trending_agent.py`, `frontend/trending-agent.html` | Sampled multi-channel observations are not platform-wide velocity or claim truth. |
| **BrandShield Defense Workbench** | **Implemented / offline-tested** | `backend/agents/brandshield_agent.py`, `frontend/brandshield-agent.html` | Missing threat records do not establish no impersonation or coordination. |
| **Personal Watch Workbench** | **Implemented / offline-tested** | `backend/agents/personal_agent.py`, `frontend/personal-watch-agent.html` | Catalog-listed identity is not live authenticated; user-entered handles are candidate hints. |
| **Hawkes Point-Process Blast Radius** | **Simulated / Demo** | `backend/services/threat_instruments.py`, `tests/unit/test_threat_instruments.py` | Point-process self-excitation simulation ($\lambda(t) = \mu + \sum \alpha e^{-\beta(t-t_i)}$), $R_0$ velocity. Explicitly returns `is_simulation: True`. |
| **Zipf-Mandelbrot Detector** | **Simulated / Demo** | `backend/services/threat_instruments.py`, `tests/unit/test_threat_instruments.py` | Power-law token-rank regression ($R^2$), Shannon entropy, and TTR for synthetic text distributions. |
| **Byzantine Swarm Consensus** | **Simulated / Demo** | `backend/services/threat_instruments.py`, `tests/unit/test_threat_instruments.py` | Multi-agent adversarial evaluation with Weighted Mean Subsequence Reduction (W-MSR) outlier pruning. |
| **AVeriTeC Adapter** | **Research / Ready** | `backend/evaluation/datasets/averitec.py` | Open-domain web claim verification loader. Correctly reports `NOT RUN` when local ~1.2 GB corpus is absent. |
| **Dense Neural CrossEncoder Reranking** | **Evaluated / Disabled** | ADR-0003, `artifacts/retrieval_benchmark/retrieval_quality_report.md` | Neural CrossEncoder evaluated across 832 query-candidate pairs; degraded entity precision (94.23% → 86.54%) and increased latency ~100x. Retained 7-feature learned linear ranker + BM25 lexical ranker in production. |
| **Dense Neural Bi-Encoder Retrieval** | **Planned** | Roadmap Item | Dense semantic vector indexing; pending architectural review in Phase 6. |
