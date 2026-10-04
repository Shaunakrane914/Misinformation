# Aegis Protocol — Testing & Quality Assurance Guide
**Framework**: Pytest 8.4.2  
**Test Suite Path**: `tests/`  
**Execution Environment**: Python 3.11+ (Windows / Linux / macOS)  
**Total Automated Tests**: 180 Passed (168 unit tests + 12 evaluation framework tests)

---

## 1. Test Architecture

The Aegis Protocol test framework is structured into specialized layers for unit correctness, security hardening, and scientific evaluation:

```
tests/
├── conftest.py                             # Global fixtures, TestClient, in-memory DB reset, mock LLM setup
├── unit/                                   # 168 Unit tests across 6 workbenches & core engines
│   ├── test_normalization_and_dedup.py     # Unicode NFC normalization, SHA-256 hashing, idempotency
│   ├── test_threat_instruments.py         # Mandelbrot regression, Hawkes point-process, consensus arbitrament
│   ├── test_capability_registry.py        # 14-channel capability registry, status transitions, health discovery
│   ├── test_agent_reach_service.py        # Domain retrieval planning, URL dedup, syndication clustering, SSRF
│   ├── test_trending_2.py                 # Trending query classes, entity resolution, velocity, clustering
│   ├── test_personal_watch_2.py           # Personal Watch VIP queries, deepfake classification, alert dedup
│   ├── test_brandshield_2.py              # BrandShield threat taxonomy, query classes, claim/threat separation
│   ├── test_scout_research_terminal.py    # Financial query resolution, primary source tagging, deduplication
│   ├── test_research_and_investigator_api.py # Investigator & Research Agent API, confidence clamping
│   ├── test_database_persistence.py       # SQLite relational mapping, status transitions, evidence joins
│   └── test_product_honesty_and_integrity.py # Invariant enforcement across all workbench HTML templates
├── evaluation/                             # 12 Scientific evaluation framework tests
│   └── test_evaluation_framework.py       # Zero ground-truth leakage, Wilson CIs, ECE, reranker ordering, split isolation
└── security/
    └── test_security_ssrf_xss.py          # SSRF private IP blocking, protocol enforcement, XSS HTML escaping
```

---

## 2. Running Automated Tests

### Run Full Test Suite (180 Tests)
```bash
pytest tests/unit/ tests/evaluation/ -v
```

### Run Evaluation Framework Tests Only
```bash
pytest tests/evaluation/ -v
```

### Run Unit Tests Only
```bash
pytest tests/unit/ -v
```

---

## 3. Scientific Benchmark Execution

Run reproducible, leak-free evaluations directly from the command line:

```bash
# 1. Run all offline ML benchmarks (Supervised Classical ML + Learned Reranker)
python scripts/evaluate_dataset.py --mode all_offline --seed 42

# 2. Run only the Supervised Classical ML Baseline
python scripts/evaluate_dataset.py --mode classical_ml --seed 42

# 3. Run only the Learned Evidence Reranker Evaluation
python scripts/evaluate_dataset.py --mode reranker --seed 42

# 4. Check AVeriTeC Benchmark Adapter Status
python scripts/evaluate_dataset.py --mode averitec_status
```

Outputs:
- Machine-readable JSON traces: `docs/evaluation/results/`
- Full scientific report: `docs/EVALUATION.md`
