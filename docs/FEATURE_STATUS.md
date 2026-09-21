# Aegis Protocol — Feature Status & Verification Matrix
**Document Version**: 3.5.1  
**Audit Reference**: Part 15 / Part 18 Master Transformation Matrix  
**Verification Baseline**: Automated Test Suite (`pytest -v` [26 passed]) + WELFake Benchmark Execution

---

## Standard Taxonomy
- **Implemented**: Code exists and is active in backend/frontend.
- **Tested**: Verified with automated unit, integration, or security tests.
- **Experimental**: Functional research prototype; subject to ongoing calibration.
- **Simulated**: Physics-grounded mathematical or synthetic agent demonstration; explicitly labelled as simulated telemetry.
- **Planned**: Roadmap initiative; not claimed as active production capability.

---

## Feature Matrix

| Subsystem / Feature | Classification | Verified Evidence | Limitations / Production Notes |
| :--- | :--- | :--- | :--- |
| **Claim Ingestion & Normalization** | **Tested** | `backend/agents/claim_ingestion_agent.py`, `tests/unit/test_normalization_and_dedup.py` | Full Unicode NFC normalization, whitespace collapsing, length enforcement. |
| **Database-Backed Deduplication** | **Tested** | `backend/db/database.py`, `ClaimIngestionAgent.ingest()` | SHA-256 hash idempotency checks prevent duplicate investigations. |
| **6-Verdict Classification Taxonomy** | **Tested** | `backend/schemas/claim_schemas.py`, `InvestigatorAgent` | `True`, `False`, `Misleading`, `Partially True`, `Unverified`, `Insufficient Evidence`. |
| **Centralized Gemini LLM Service** | **Tested** | `backend/services/gemini_service.py` | Multi-key rotation, jittered exponential backoff, auto-fallback to `MockGeminiProvider`. |
| **Server-Side Request Forgery (SSRF) Defense** | **Tested** | `backend/services/url_validator.py`, `tests/security/test_security_ssrf_xss.py` | Pre-fetch DNS resolution blocks private RFC1918, loopback, and cloud metadata (169.254.169.254). |
| **Cross-Site Scripting (XSS) Sanitization** | **Tested** | `frontend/aegis-nav.js`, `tests/security/test_security_ssrf_xss.py` | Global `escapeHtml` utility applied to dynamic DOM elements in HTML dashboards. |
| **Zipf-Mandelbrot Synthetic Text Detector** | **Tested** | `backend/services/threat_instruments.py`, `tests/unit/test_threat_instruments.py` | Power-law token rank frequency regression, $R^2$, Shannon entropy, TTR calculation. |
| **Hawkes Point-Process Contagion Simulator** | **Simulated** | `backend/services/threat_instruments.py`, `tests/unit/test_threat_instruments.py` | Physics-grounded self-exciting point process simulation; returns explicit `is_simulation: True`. |
| **Ensemble Quorum & Outlier Detection** | **Tested** | `backend/services/threat_instruments.py`, `tests/unit/test_threat_instruments.py` | Majority consensus with statistical $2\sigma$ outlier detection. |
| **WELFake Dataset Evaluation Harness** | **Tested** | `scripts/evaluate_dataset.py`, `docs/EVALUATION.md` | Reproducible benchmark evaluation on 23,100-article dataset with confusion matrices. |
| **Personal Watch VIP Monitoring** | **Implemented** | `backend/agents/personal_agent.py`, `frontend/personal-watch-agent.html` | Keyword and persona scanning across public news feeds. |
| **BrandShield Defense** | **Implemented** | `backend/agents/brandshield_agent.py`, `frontend/brandshield-agent.html` | Review anomaly detection and brand sentiment scanning. |
| **Scout Market Volatility Agent** | **Experimental** | `backend/agents/scout_agent.py`, `frontend/scout-agent.html` | Yahoo Finance scraper requires optional `YF_API_KEY` for live production quotes. |
| **Twitter/X Native Stream Ingestion** | **Planned** | Configured via Apify connector | Requires paid `APIFY_TOKEN`; falls back gracefully to public news RSS. |
