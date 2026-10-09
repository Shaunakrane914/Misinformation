# Aegis Protocol — Testing & Quality Assurance Guide
**Framework**: Pytest 8.4.2  
**Test Suite Path**: `tests/`  
**Execution Environment**: Python 3.11+ (Windows / Linux / macOS)  
**Total Automated Tests**: **530 Passed, 0 Failed, 0 Warnings** (Unit, Contract, Integration, Chaos, Security, Cranfield Benchmark)

---

## 1. Test Architecture

The Aegis Protocol test framework is structured into specialized layers for unit correctness, structural contracts, fault tolerance, security hardening, and scientific evaluation:

```
tests/
├── conftest.py                             # Global fixtures, TestClient, in-memory DB reset, mock LLM setup
├── unit/                                   # Unit tests across sentinels, normalization, and core engines
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
│   ├── test_product_honesty_and_integrity.py # Invariant enforcement across all workbench HTML templates
│   ├── test_scraper_laboratory.py         # Scraper canary contracts and drift detection
│   ├── test_shared_acquisition_fabric.py  # Acquisition routing policies, Playwright rescue, source gates
│   ├── test_zero_auth_social_retrieval.py # Zero-auth social adapters (Arctic Shift, fxTwitter)
│   ├── test_zero_auth_source_discovery.py # Discovery URL permalink parsers and platform rejectors
│   ├── test_adversarial_retrieval_traps.py# Hard-negative traps (lookalike tickers, parody handles, homographs)
│   └── test_unified_report_schema.py      # UnifiedReport v3.8.0 schema and ReportBuilder validation
├── contract/                               # Boundary and upstream schema contract enforcement
│   └── test_upstream_fixtures.py          # Canary fixtures and upstream parser contracts
├── integration/                            # Inter-service and database integration tests
│   └── test_claim_pipeline.py             # End-to-end ingestion -> retrieval -> ranking -> verdict pipeline
├── chaos/                                  # Fault injection and resilience tests
│   └── test_agent_reach_chaos.py          # Latency injection, socket timeouts, rate limits, network partitions
├── security/                               # Security regression suite
│   └── test_security_ssrf_xss.py          # SSRF private IP blocking, protocol enforcement, XSS HTML escaping
├── evaluation/                             # Scientific evaluation framework tests
│   └── test_evaluation_framework.py       # Zero ground-truth leakage, Wilson CIs, ECE, reranker ordering, split isolation
├── benchmarks/                             # Performance and latency benchmark tests
│   └── test_research_performance.py       # Investigation latency profiles and memory bounds
├── retrieval_benchmark/                    # Frozen 104-scenario Cranfield benchmark corpus
│   ├── scenarios.jsonl                    # 104 frozen evaluation scenarios
│   ├── candidates.jsonl                   # 416 frozen candidate documents
│   └── labels.jsonl                       # Curated relevance annotations
├── test_api_endpoints.py                   # FastAPI REST router validation (including zero-variance regression)
├── test_trending_temporal_guard.py         # 48-hour freshness window and timestamp decoupling tests
├── test_retrieval_benchmark.py             # Cranfield evaluation execution and golden assertions
├── test_retrieval_metrics.py               # MRR, NDCG@5, Precision@1, entity match metric tests
├── test_retrieval_quality_hardening.py     # Hard-negative rejection and ranking monotonicity tests
├── test_semantic_reranker.py               # 7-feature linear reranker model tests
├── test_unified_report.py                  # End-to-end report generation across sentinels
└── test_complete_retrieval_audit_integrity.py # Cross-validation of benchmark metrics and invariants
```

---

## 2. Running Automated Tests

### Run Full Test Suite (530 Tests)
```bash
pytest
```

### Run Fast Unit Suite Only
```bash
pytest tests/unit/
```

### Run Security & SSRF Protection Tests
```bash
pytest tests/security/
```

### Run Retrieval Benchmark & Quality Hardening Tests
```bash
pytest tests/test_retrieval_benchmark.py tests/test_retrieval_metrics.py tests/test_retrieval_quality_hardening.py
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
