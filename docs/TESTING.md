# Aegis Protocol — Testing & Quality Assurance Guide
**Framework**: Pytest 8.4.2  
**Test Suite Path**: `tests/`  
**Execution Environment**: Python 3.11+ (Windows / Linux / macOS)

---

## 1. Test Architecture

The Aegis Protocol test framework is structured into three distinct layers to ensure rapid developer iteration and zero-cost offline validation:

```
tests/
├── conftest.py                             # Global fixtures, TestClient, in-memory DB reset, mock LLM setup
├── unit/
│   ├── test_normalization_and_dedup.py     # Unicode NFC normalization, SHA-256 hashing, idempotency
│   ├── test_threat_instruments.py         # Mandelbrot regression, Hawkes point-process, consensus arbitrament
│   ├── test_capability_registry.py        # 14-channel capability registry, status transitions, health discovery
│   └── test_agent_reach_service.py        # Domain retrieval planning, URL dedup, syndication clustering, SSRF
├── security/
│   └── test_security_ssrf_xss.py          # SSRF private IP blocking, protocol enforcement, XSS HTML escaping
└── integration/
    ├── test_claim_pipeline.py             # Full FastAPI HTTP lifecycle (submit, background worker, poll, threat lab)
    └── test_agent_reach_api.py            # Agent Reach API endpoints (/capabilities, /health, /omni-scan, /read)
```

---

## 2. Running Automated Tests

### Run Full Test Suite
```bash
python -m pytest tests/ -v
```

### Run Unit Tests Only
```bash
python -m pytest tests/unit/ -v -m unit
```

### Run Security Regression Tests
```bash
python -m pytest tests/security/ -v -m security
```

### Run Integration Tests
```bash
python -m pytest tests/integration/ -v -m integration
```

---

## 3. Verified Test Results (v3.6.0 Agent Reach Upgrade)

```
============================= test session starts =============================
platform win32 -- Python 3.13.5, pytest-8.4.2, pluggy-1.6.0
rootdir: C:\Users\Shaunak Rane\Desktop\Projects\Misinformation
configfile: pytest.ini
collected 47 items

tests/integration/test_agent_reach_api.py::test_api_agent_reach_capabilities PASSED [  2%]
tests/integration/test_agent_reach_api.py::test_api_agent_reach_health_and_doctor PASSED [  4%]
tests/integration/test_agent_reach_api.py::test_api_agent_reach_omni_scan PASSED [  6%]
tests/integration/test_agent_reach_api.py::test_api_agent_reach_read_ssrf_blocked PASSED [  8%]
tests/integration/test_agent_reach_api.py::test_api_agent_reach_scan PASSED [ 10%]
tests/integration/test_claim_pipeline.py::test_submit_claim_and_retrieve_verdict PASSED [ 12%]
tests/integration/test_claim_pipeline.py::test_submit_empty_claim_fails PASSED [ 14%]
tests/integration/test_claim_pipeline.py::test_duplicate_claim_submission PASSED [ 17%]
tests/integration/test_claim_pipeline.py::test_threat_lab_api_endpoints PASSED [ 19%]
tests/security/test_security_ssrf_xss.py::test_ssrf_prevention[http://127.0.0.1:8000/api/claims] PASSED [ 21%]
tests/security/test_security_ssrf_xss.py::test_ssrf_prevention[http://localhost:3000/] PASSED [ 23%]
tests/security/test_security_ssrf_xss.py::test_ssrf_prevention[http://169.254.169.254/latest/meta-data/] PASSED [ 25%]
tests/security/test_security_ssrf_xss.py::test_ssrf_prevention[http://10.0.0.1/admin] PASSED [ 27%]
tests/security/test_security_ssrf_xss.py::test_ssrf_prevention[http://192.168.1.1/router] PASSED [ 29%]
tests/security/test_security_ssrf_xss.py::test_ssrf_prevention[http://172.16.0.1/secret] PASSED [ 31%]
tests/security/test_security_ssrf_xss.py::test_ssrf_prevention[file:///etc/passwd] PASSED [ 34%]
tests/security/test_security_ssrf_xss.py::test_ssrf_prevention[gopher://evil.com/] PASSED [ 36%]
tests/security/test_security_ssrf_xss.py::test_ssrf_prevention[ftp://internal.server/data] PASSED [ 38%]
tests/security/test_security_ssrf_xss.py::test_ssrf_prevention[http://0.0.0.0/] PASSED [ 40%]
tests/security/test_security_ssrf_xss.py::test_public_safe_urls_allowed PASSED [ 42%]
tests/security/test_security_ssrf_xss.py::test_html_xss_escaping_logic PASSED [ 44%]
tests/unit/test_agent_reach_service.py::test_retrieval_planner_financial_domain PASSED [ 46%]
tests/unit/test_agent_reach_service.py::test_retrieval_planner_technical_domain PASSED [ 48%]
tests/unit/test_agent_reach_service.py::test_retrieval_planner_keyword_extraction PASSED [ 51%]
tests/unit/test_agent_reach_service.py::test_url_normalization PASSED    [ 53%]
tests/unit/test_agent_reach_service.py::test_fragment_deduplication PASSED [ 55%]
tests/unit/test_agent_reach_service.py::test_source_independence_syndication_clustering PASSED [ 57%]
tests/unit/test_agent_reach_service.py::test_source_role_attribution PASSED [ 59%]
tests/unit/test_agent_reach_service.py::test_ssrf_protection_in_read PASSED [ 61%]
tests/unit/test_agent_reach_service.py::test_retrieve_partial_failure_resilience PASSED [ 63%]
tests/unit/test_agent_reach_service.py::test_backward_compatibility_interfaces PASSED [ 65%]
tests/unit/test_capability_registry.py::test_registry_registration_and_lifecycle PASSED [ 68%]
tests/unit/test_capability_registry.py::test_registry_status_transitions PASSED [ 70%]
tests/unit/test_capability_registry.py::test_registry_discovery_probing PASSED [ 72%]
tests/unit/test_capability_registry.py::test_registry_routing_with_platform_filter PASSED [ 74%]
tests/unit/test_capability_registry.py::test_capability_map_structure PASSED [ 76%]
tests/unit/test_capability_registry.py::test_optional_authenticated_channel_status PASSED [ 78%]
tests/unit/test_normalization_and_dedup.py::test_unicode_nfc_normalization PASSED [ 80%]
tests/unit/test_normalization_and_dedup.py::test_whitespace_and_punctuation_collapsing PASSED [ 82%]
tests/unit/test_normalization_and_dedup.py::test_deterministic_sha256_hash PASSED [ 85%]
tests/unit/test_normalization_and_dedup.py::test_claim_ingestion_idempotency PASSED [ 87%]
tests/unit/test_normalization_and_dedup.py::test_empty_and_whitespace_claim_rejection PASSED [ 89%]
tests/unit/test_threat_instruments.py::test_mandelbrot_insufficient_sample PASSED [ 91%]
tests/unit/test_threat_instruments.py::test_mandelbrot_valid_text PASSED [ 93%]
tests/unit/test_threat_instruments.py::test_hawkes_point_process_simulation PASSED [ 95%]
tests/unit/test_threat_instruments.py::test_hawkes_empty_input_validation PASSED [ 97%]
tests/unit/test_threat_instruments.py::test_ensemble_consensus_majority_and_outlier PASSED [100%]

============================= 47 passed in 17.41s =============================
```


---

## 4. Benchmark Evaluation
In addition to unit and integration tests, evaluate empirical model metrics against the WELFake news corpus:
```bash
python scripts/evaluate_dataset.py --sample 60 --seed 42
```
Outputs:
- Machine-readable metrics: `docs/audit/evaluation_results.json`
- Scientific report: `docs/EVALUATION.md`
