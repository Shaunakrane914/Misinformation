# Aegis Protocol — Feature Status & Implementation Matrix

**Document Version**: 4.1.0 (Phase 1 Canonical Architecture Baseline)  
**Verification Baseline**: Automated Test Suite (`pytest -v` [530 passed: unit, contract, integration, chaos, security, and Cranfield benchmarks]) + Supervised ML Benchmark Execution  
**Audit Status**: Ground-truth leakage eliminated; prior 93.33% synthetic metric formally retired.

---

## Standard Taxonomy

- **Production / Implemented**: Code exists, is tested with real data/contracts, and executes deterministically in runtime.
- **Tested**: Verified with automated unit, integration, or property-based tests in CI.
- **Simulated**: Algorithmic or mathematical demonstrations (e.g. point processes, synthetic power-law distributions); explicitly returns `is_simulation: True`.
- **Experimental**: Functional research prototype; subject to ongoing calibration or optional external API keys.
- **Research / Ready**: Standardized evaluation adapters (e.g., AVeriTeC) waiting for local data download; honestly reports `NOT RUN`.
- **Planned**: Roadmap initiative; not claimed as active production capability.

---

## Comprehensive Implementation Matrix

| Subsystem / Feature | Taxonomy Tier | Verified Evidence | Limitations & Technical Boundaries |
| :--- | :--- | :--- | :--- |
| **Claim Ingestion & Normalization** | **Production / Tested** | `backend/agents/claim_ingestion_agent.py`, `tests/unit/test_normalization_and_dedup.py` | Full Unicode NFC normalization, whitespace collapsing, length enforcement. |
| **Database-Backed Deduplication** | **Production / Tested** | `backend/db/database.py`, `ClaimIngestionAgent.ingest()` | SHA-256 hash idempotency checks prevent duplicate investigations. |
| **6-Verdict Classification Taxonomy** | **Production / Tested** | `backend/schemas/claim_schemas.py`, `InvestigatorAgent` | `True`, `False`, `Misleading`, `Partially True`, `Unverified`, `Insufficient Evidence`. |
| **Learned Evidence Reranker** | **Production / Tested** | `backend/evaluation/reranker.py`, `tests/evaluation/test_evaluation_framework.py` | 7-feature linear model trained via pairwise cross-entropy on train pairs, evaluated on held-out test queries (MRR 0.20 → 1.00, 0.26ms p50 latency). |
| **Supervised Classical ML Baseline** | **Production / Tested** | `backend/evaluation/baselines.py`, `tests/evaluation/test_evaluation_framework.py` | Deduplicated TF-IDF (10k) + L2 Logistic Regression on held-out WELFake split: 88.50% accuracy, 0.8850 F1 ($N=2,948$; 800 duplicate titles removed pre-split; 0 duplicate content across train/val/test). |
| **Agent Reach Capability Layer** | **Production / Tested** | `backend/services/agent_reach_scraper.py`, `backend/services/research/` | 14-channel capability router with RFC 3986 URL parsing and wire syndication clustering. |
| **SSRF Defense & URL Validator** | **Production / Tested** | `backend/services/url_validator.py`, `tests/security/` | Pre-fetch DNS resolution blocks private RFC1918, loopback, and cloud metadata (169.254.169.254). |
| **XSS Sanitization** | **Production / Tested** | `frontend/aegis-nav.js` | Global `escapeHtml` utility applied to dynamic DOM elements across all dashboards. |
| **Centralized Gemini Service** | **Production / Tested** | `backend/services/gemini_service.py` | Multi-key rotation, jittered exponential backoff. Scientific mode cleanly blocks rather than falling back to mock. |
| **India Multilingual Track** | **Research / Prototype** | `backend/evaluation/datasets/india_track.py` | Curated gold prototype across English, Hindi, Marathi, and Hinglish (14 claims across 5 civic domains with accredited institutional provenance). |
| **Investigator Agent** | **Production / Tested** | `backend/agents/investigator_agent.py`, `frontend/investigator-agent.html` | Forensic case dossiers, timeline reconstructor, contradiction matrix, and verdict synthesis. |
| **Research Agent** | **Production / Tested** | `backend/agents/research_agent.py`, `frontend/research-agent.html` | Multi-source investigation, primary source escalation, corroboration scoring, and reading list. |
| **Scout Financial Workbench** | **Production / Tested** | `backend/agents/scout_agent.py`, `frontend/scout-agent.html` | Yahoo Finance real-time price feeds, volume z-scores, event-clustered news correlation. |
| **Trending Viral Workbench** | **Production / Tested** | `backend/agents/trending_agent.py`, `frontend/trending-agent.html` | Multi-channel RSS discovery, velocity estimation, narrative summary dossiers. |
| **BrandShield Defense Workbench** | **Production / Tested** | `backend/agents/brandshield_agent.py`, `frontend/brandshield-agent.html` | Brand threat cards, suspicious listing audit, coordinated astroturfing heuristic. |
| **Personal Watch Workbench** | **Production / Tested** | `backend/agents/personal_agent.py`, `frontend/personal-watch-agent.html` | Executive & public figure monitoring across news and web channels with severity triage. |
| **Hawkes Point-Process Blast Radius** | **Simulated / Demo** | `backend/services/threat_instruments.py`, `tests/unit/test_threat_instruments.py` | Point-process self-excitation simulation ($\lambda(t) = \mu + \sum \alpha e^{-\beta(t-t_i)}$), $R_0$ velocity. Explicitly returns `is_simulation: True`. |
| **Zipf-Mandelbrot Detector** | **Simulated / Demo** | `backend/services/threat_instruments.py`, `tests/unit/test_threat_instruments.py` | Power-law token-rank regression ($R^2$), Shannon entropy, and TTR for synthetic text distributions. |
| **Byzantine Swarm Consensus** | **Simulated / Demo** | `backend/services/threat_instruments.py`, `tests/unit/test_threat_instruments.py` | Multi-agent adversarial evaluation with Weighted Mean Subsequence Reduction (W-MSR) outlier pruning. |
| **AVeriTeC Adapter** | **Research / Ready** | `backend/evaluation/datasets/averitec.py` | Open-domain web claim verification loader. Correctly reports `NOT RUN` when local ~1.2 GB corpus is absent. |
| **Dense Neural CrossEncoder Reranking** | **Evaluated / Disabled** | ADR-0003, `artifacts/retrieval_benchmark/retrieval_quality_report.md` | Neural CrossEncoder evaluated across 832 query-candidate pairs; degraded entity precision (94.23% → 86.54%) and increased latency ~100x. Retained 7-feature learned linear ranker + BM25 lexical ranker in production. |
| **Dense Neural Bi-Encoder Retrieval** | **Planned** | Roadmap Item | Dense semantic vector indexing; pending architectural review in Phase 6. |
