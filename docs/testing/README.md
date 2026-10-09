# Aegis Protocol — Testing & Quality Assurance Reference

**Document Version**: 4.1.0  
**Framework**: Pytest 8.4.2  
**Test Suite Path**: `tests/`  
**Total Automated Tests**: **530 Passed, 0 Failed, 0 Warnings**

---

## 1. Testing Philosophy & Guarantees

Aegis Protocol maintains an ironclad testing culture:
1. **Zero Silent Regressions**: The entire 530-test suite must pass with 0 failures and 0 warnings before any commit or merge.
2. **Offline Hermetic Execution**: The default test suite does not require external API keys, database servers, or live internet connectivity.
3. **Bit-for-Bit Fixture Immutability**: Golden retrieval benchmarks in `tests/retrieval_benchmark/` are frozen and immutable.
4. **Adversarial Resilience**: Chaos tests inject simulated network latency, packet loss, and rate limits to guarantee graceful degradation.

---

## 2. Test Suite Directory Structure

```
tests/
├── conftest.py                             # Global fixtures, mock LLMs, in-memory DB setups
├── unit/                                   # Domain unit tests across sentinels and core engines
│   ├── test_normalization_and_dedup.py     # Unicode NFC, SHA-256 deduplication
│   ├── test_threat_instruments.py         # Mandelbrot, Hawkes process, consensus
│   ├── test_capability_registry.py        # 14-channel capability transitions
│   ├── test_agent_reach_service.py        # Domain retrieval, URL dedup, syndication
│   ├── test_trending_2.py                 # Trending topics, entity velocity, clustering
│   ├── test_personal_watch_2.py           # VIP profile scanning, identity diffs
│   ├── test_brandshield_2.py              # Brand threat cards, astroturfing audit
│   ├── test_scout_research_terminal.py    # Financial query resolution, tickers
│   ├── test_research_and_investigator_api.py # Investigator & Research API
│   ├── test_database_persistence.py       # Relational mapping, status transitions
│   ├── test_product_honesty_and_integrity.py # Template invariant enforcement
│   ├── test_scraper_laboratory.py         # Scraper canaries and schema drift detection
│   ├── test_shared_acquisition_fabric.py  # Acquisition routing policies, Playwright rescue
│   ├── test_zero_auth_social_retrieval.py # Zero-auth social adapters (Arctic Shift, fxTwitter)
│   ├── test_zero_auth_source_discovery.py # Discovery URL permalinks and platform rejects
│   ├── test_adversarial_retrieval_traps.py# Hard-negative traps (tickers, handles, homographs)
│   └── test_unified_report_schema.py      # UnifiedReport v3.8.0 schema validation
├── contract/                               # Boundary and upstream schema contract enforcement
│   └── test_upstream_fixtures.py          # Canary fixtures and upstream parser contracts
├── integration/                            # Inter-service investigation pipeline tests
├── chaos/                                  # Fault injection & rate limit resilience tests
├── security/                               # SSRF defenses, URL sanitization, XSS checks
├── evaluation/                             # Scientific metrics & leakage prevention tests
├── benchmarks/                             # Latency profiles and memory limits
├── retrieval_benchmark/                    # 104-scenario Cranfield frozen corpus
├── test_api_endpoints.py                   # FastAPI REST router validation (530 test baseline)
├── test_trending_temporal_guard.py         # 48-hour freshness window and timestamp decoupling
├── test_retrieval_benchmark.py             # Cranfield benchmark execution
├── test_retrieval_metrics.py               # MRR, NDCG@5, Precision@1, entity match metrics
├── test_retrieval_quality_hardening.py     # Hard-negative rejection & monotonicity
├── test_semantic_reranker.py               # 7-feature linear reranker model tests
├── test_unified_report.py                  # End-to-end report generation across sentinels
└── test_complete_retrieval_audit_integrity.py # Cross-validation of benchmark metrics and invariants
```

---

## 3. Test Execution Runbook

### Run the Complete Test Suite
```bash
pytest
```
*Expected: 530 passed in ~12-14 minutes.*

### Run Specific Test Suites
```bash
# Unit suite only
pytest tests/unit/

# Contract & API endpoint suite
pytest tests/contract/ tests/test_api_endpoints.py

# Chaos & resilience suite
pytest tests/chaos/

# Security suite
pytest tests/security/

# Cranfield retrieval benchmarks
pytest tests/test_retrieval_benchmark.py tests/test_retrieval_metrics.py tests/test_retrieval_quality_hardening.py
```

For more detailed information, see [`docs/TESTING.md`](../TESTING.md).
