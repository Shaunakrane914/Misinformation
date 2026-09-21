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
│   └── test_threat_instruments.py         # Mandelbrot regression, Hawkes point-process, consensus arbitrament
├── security/
│   └── test_security_ssrf_xss.py          # SSRF private IP blocking, protocol enforcement, XSS HTML escaping
└── integration/
    └── test_claim_pipeline.py             # Full FastAPI HTTP lifecycle (submit, background worker, poll, threat lab)
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

## 3. Verified Test Results (Phase 8 Baseline)

```
============================= test session starts =============================
platform win32 -- Python 3.13.5, pytest-8.4.2, pluggy-1.6.0
rootdir: C:\Users\Shaunak Rane\Desktop\Projects\Misinformation
configfile: pytest.ini
collected 26 items

tests/integration/test_claim_pipeline.py::test_submit_claim_and_retrieve_verdict PASSED [  3%]
tests/integration/test_claim_pipeline.py::test_submit_empty_claim_fails PASSED [  7%]
tests/integration/test_claim_pipeline.py::test_duplicate_claim_submission PASSED [ 11%]
tests/integration/test_claim_pipeline.py::test_threat_lab_api_endpoints PASSED [ 15%]
tests/security/test_security_ssrf_xss.py::test_ssrf_prevention[http://127.0.0.1:8000/api/claims] PASSED [ 19%]
tests/security/test_security_ssrf_xss.py::test_ssrf_prevention[http://localhost:3000/] PASSED [ 23%]
tests/security/test_security_ssrf_xss.py::test_ssrf_prevention[http://169.254.169.254/latest/meta-data/] PASSED [ 26%]
tests/security/test_security_ssrf_xss.py::test_ssrf_prevention[http://10.0.0.1/admin] PASSED [ 30%]
tests/security/test_security_ssrf_xss.py::test_ssrf_prevention[http://192.168.1.1/router] PASSED [ 34%]
tests/security/test_security_ssrf_xss.py::test_ssrf_prevention[http://172.16.0.1/secret] PASSED [ 38%]
tests/security/test_security_ssrf_xss.py::test_ssrf_prevention[file:///etc/passwd] PASSED [ 42%]
tests/security/test_security_ssrf_xss.py::test_ssrf_prevention[gopher://evil.com/] PASSED [ 46%]
tests/security/test_security_ssrf_xss.py::test_ssrf_prevention[ftp://internal.server/data] PASSED [ 50%]
tests/security/test_security_ssrf_xss.py::test_ssrf_prevention[http://0.0.0.0/] PASSED [ 53%]
tests/security/test_security_ssrf_xss.py::test_public_safe_urls_allowed PASSED [ 57%]
tests/security/test_security_ssrf_xss.py::test_html_xss_escaping_logic PASSED [ 61%]
tests/unit/test_normalization_and_dedup.py::test_unicode_nfc_normalization PASSED [ 65%]
tests/unit/test_normalization_and_dedup.py::test_whitespace_and_punctuation_collapsing PASSED [ 69%]
tests/unit/test_normalization_and_dedup.py::test_deterministic_sha256_hash PASSED [ 73%]
tests/unit/test_normalization_and_dedup.py::test_claim_ingestion_idempotency PASSED [ 76%]
tests/unit/test_normalization_and_dedup.py::test_empty_and_whitespace_claim_rejection PASSED [ 80%]
tests/unit/test_threat_instruments.py::test_mandelbrot_insufficient_sample PASSED [ 84%]
tests/unit/test_threat_instruments.py::test_mandelbrot_valid_text PASSED [ 88%]
tests/unit/test_threat_instruments.py::test_hawkes_point_process_simulation PASSED [ 92%]
tests/unit/test_threat_instruments.py::test_hawkes_empty_input_validation PASSED [ 96%]
tests/unit/test_threat_instruments.py::test_ensemble_consensus_majority_and_outlier PASSED [100%]

============================= 26 passed in 14.96s =============================
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
