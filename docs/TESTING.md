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
│   ├── test_agent_reach_service.py        # Domain retrieval planning, URL dedup, syndication clustering, SSRF
│   ├── test_trending_2.py                 # Trending 2.0 query classes, entity resolution, velocity, clustering
│   ├── test_personal_watch_2.py           # Personal Watch 2.0 VIP queries, deepfake classification, alert dedup
│   ├── test_brandshield_2.py              # BrandShield 2.0 threat taxonomy, query classes, claim/threat separation
│   ├── test_scout_research_terminal.py    # Financial query resolution, primary source tagging, deduplication
│   └── test_database_persistence.py       # SQLite relational mapping, status transitions, evidence joins
├── security/
│   └── test_security_ssrf_xss.py          # SSRF private IP blocking, protocol enforcement, XSS HTML escaping
└── integration/
    ├── test_claim_pipeline.py             # Full FastAPI HTTP lifecycle (submit, background worker, poll, threat lab)
    ├── test_agent_reach_api.py            # Agent Reach API endpoints (/capabilities, /health, /omni-scan, /read)
    ├── test_trending_2_workflow.py        # Trending 2.0 end-to-end HTTP pipeline and telemetry validation
    ├── test_personal_watch_2_workflow.py  # Personal Watch 2.0 end-to-end HTTP pipeline and alert triggers
    ├── test_brandshield_2_workflow.py     # BrandShield 2.0 end-to-end HTTP pipeline, dossiers, and taxonomy
    └── test_modular_routers.py            # Modular router verification for all sentinel agents
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

### Run Flake8 Code Quality Linting
```bash
flake8 . --count --select=E9,F63,F7,F82 --show-source --statistics
```

---

## 3. Verified Test Results (v3.6.0 Unified Sentinel Overhaul)

```
============================= test session starts =============================
platform win32 -- Python 3.13.5, pytest-8.4.2, pluggy-1.6.0
rootdir: C:\Users\Shaunak Rane\Desktop\Projects\Misinformation
configfile: pytest.ini
collected 99 items

tests/integration/test_agent_reach_api.py (5 tests) PASSED
tests/integration/test_brandshield_2_workflow.py (4 tests) PASSED
tests/integration/test_claim_pipeline.py (4 tests) PASSED
tests/integration/test_modular_routers.py (6 tests) PASSED
tests/integration/test_personal_watch_2_workflow.py (4 tests) PASSED
tests/integration/test_trending_2_workflow.py (4 tests) PASSED
tests/security/test_security_ssrf_xss.py (12 tests) PASSED
tests/unit/test_agent_reach_service.py (10 tests) PASSED
tests/unit/test_brandshield_2.py (6 tests) PASSED
tests/unit/test_capability_registry.py (6 tests) PASSED
tests/unit/test_database_persistence.py (3 tests) PASSED
tests/unit/test_normalization_and_dedup.py (5 tests) PASSED
tests/unit/test_personal_watch_2.py (9 tests) PASSED
tests/unit/test_scout_research_terminal.py (6 tests) PASSED
tests/unit/test_threat_instruments.py (5 tests) PASSED
tests/unit/test_trending_2.py (10 tests) PASSED

============================= 99 passed in 170.18s ============================
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
