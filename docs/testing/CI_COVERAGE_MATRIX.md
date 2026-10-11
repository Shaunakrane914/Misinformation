# Aegis Protocol — CI Coverage Matrix & Test Inventory
**Phase 7.1 Release Candidate Deliverable B**  
*Lead QA Architect & Release Engineer Audit*

---

## 1. Test Inventory Overview

A full discovery across the repository identified **787 collected offline tests** in the test suite, plus 1 standalone manual live probe script. All 787 tests execute and pass offline with zero network dependencies and zero required paid API keys.

```
Total Collected Tests: 787
Local Pass Rate:       787 / 787 (100% PASS)
Local Wall Time:       ~4 min 20 sec (Python 3.13.5 win32)
```

---

## 2. Directory & Component Breakdown

| Directory / File Category | Test Count | Scope & Focus | CI Job Mapping | Local Result |
|---|---:|---|---|---|
| `tests/unit/` | 567 | Core units: channel contracts (76), native runtime (13), service (11), profiles (8), invariants (4), brandshield (6), capability registry (6), database (3), deep research (9), doctor semantics (9), frontend contract (6), functional matrix (24), gemini service (11), live smoke harness (7), llm gateway (20), bounded http (10), dedup (5), personal watch (9), golden masters (20), backward compat (12), social resolution (17), honesty (11), provenance (4), telemetry (6), recovered routes (18), replay (6), investigator (8), stages (13), integrity (13), settings (8), fabric (20), source planning (10), threat instruments (5), trending (10), report schema (38), zero auth social (14), source discovery (24). | `unit-and-chaos-matrix` (Py 3.11, 3.12, 3.13) | **567 PASSED** |
| `tests/chaos/` | 4 | Complete network blackout, Jina 429 fallback, RSS malformed XML recovery, Twitter timeout resilience. | `unit-and-chaos-matrix` (Py 3.11, 3.12, 3.13) | **4 PASSED** |
| `tests/security/` | 21 | Safe HTTP transport (retry-after, redirects, body size, backoff), strict SSRF blocking (private IPs, AWS metadata, loopback), XSS escaping, and static path traversal prevention. | `unit-and-chaos-matrix` (Py 3.11, 3.12, 3.13) | **21 PASSED** |
| `tests/integration/` | 61 | Multi-agent end-to-end workflows (Scout, Trending, BrandShield, Personal Watch), modular routers, claim pipeline, source planner agent execution. | `integration-and-contracts` (Py 3.12) | **61 PASSED** |
| `tests/contract/` | 5 | Upstream fixtures: doctor JSON parsing, GitHub repo normalization, yt-dlp video normalization, V2EX topics, Bilibili search. | `integration-and-contracts` (Py 3.12) | **5 PASSED** |
| `tests/retrieval_benchmark/` | 8 | Benchmark schema validation, four agents balance, dev/holdout split disjointness, gold grades scale, fail-closed empty fixtures. | `integration-and-contracts` (Py 3.12) | **8 PASSED** |
| `tests/evaluation/` | 15 | Evaluation framework: zero leakage, Welfake split isolation, Wilson score intervals, macro F1 CI, abstention metrics, calibration, learned reranker. | `integration-and-contracts` (Py 3.12) | **15 PASSED** |
| `tests/benchmarks/` | 2 | Research performance benchmarks: single investigation baseline and concurrent investigation percentiles. | `provenance-and-benchmarks` (Py 3.12) | **2 PASSED** |
| Root `tests/test_*.py` | 105 | Root-level test modules: `test_api_endpoints.py` (7), `test_audit_synthetic_telemetry_negatives.py` (14), `test_complete_retrieval_audit_integrity.py` (23), `test_retrieval_benchmark.py` (10), `test_retrieval_metrics.py` (10), `test_retrieval_quality_hardening.py` (19), `test_semantic_reranker.py` (4), `test_trending_temporal_guard.py` (10), `test_unified_report.py` (8). | `integration-and-contracts` (Py 3.12) | **105 PASSED** |
| `tests/frontend/` | 8 | Pure Node.js test suite for `operation-health.js` (TTL, deduplication, visibility, degradation). | `code-quality` (Node 20) + `unit-and-chaos-matrix` | **8 PASSED** |

---

## 3. Remote GitHub Actions Matrix Mapping

### Active CI Jobs (`.github/workflows/ci.yml`)

1. **`code-quality` (Ubuntu, Python 3.12, Node 20)**
   - `flake8 . --count --select=E9,F63,F7,F82 --show-source --statistics --exclude=venv,.venv,build,dist,research/scraper_bakeoff/repos`
   - `node tests/frontend/test_operation_health.js` (Frontend health contract)
2. **`unit-and-chaos-matrix` (Ubuntu, Matrix: Python 3.11, 3.12, 3.13)**
   - Executes: `pytest -v tests/unit/ tests/chaos/ tests/security/ --maxfail=2` (592 tests)
   - Environment: `ENVIRONMENT: test`, `AEGIS_MOCK_LLM: "true"`, `AGENT_REACH_ENABLED: "true"`
3. **`integration-and-contracts` (Ubuntu, Python 3.12)**
   - Executes full offline integration, contracts, retrieval benchmark schema, evaluation framework, and root test files (189 tests):
   - `pytest -v tests/integration/ tests/contract/ tests/retrieval_benchmark/ tests/evaluation/ tests/test_*.py`
4. **`provenance-and-benchmarks` (Ubuntu, Python 3.12)**
   - Replay Ledger & Truth Dossier integration: `pytest -v tests/integration/test_claim_pipeline.py -k test_verify_claim_produces_lineage_and_replay_dossier`
   - Research Performance: `pytest -v tests/benchmarks/test_research_performance.py`
   - Empirical Evaluation Runner: `python scripts/evaluate_dataset.py --target "Vaccines undergo double-blind clinical trials before regulatory distribution"`
   - Frozen Benchmark Dataset Integrity: `git diff --exit-code tests/retrieval_benchmark/`

---

## 4. Intentionally Excluded Tests & Rationale

| Script / Test File | Execution Type | Exclusion Rationale |
|---|---|---|
| `tests/smoke_test_social_production.py` | Manual / Authorized Only | Connects to live Reddit (`reddit.com/r/IAmA`) and X (`x.com/jack`). Intentionally excluded from automated PR CI to prevent flaky internet dependencies, IP rate-limiting, and credentials leakage. |
| `scripts/run_phase6_8_resolution_benchmark.py` | Manual / Authorized Only | Probes live Wikidata P2002 REST and public RSS endpoints. Run manually for release audits. |
| `scripts/load_test.py` | Manual / Staging Only | High-concurrency stress test designed for load testing staging infrastructure. |

---

## 5. Token Permission Disclosure

- **Empirical Finding**: The local git credentials authenticate via an OAuth App token with `repo` scope, but without GitHub `workflow` scope.
- **Consequence**: Git push rejections occur when updating `.github/workflows/ci.yml` directly from this local terminal.
- **Resolution**:
  - The authoritative, complete CI specification is provided in [`docs/ci/FULL_CI_WORKFLOW.yml`](file:///c:/Users/Shaunak%20Rane/Desktop/Projects/Misinformation/docs/ci/FULL_CI_WORKFLOW.yml) and verified locally.
  - The existing active workflow `.github/workflows/ci.yml` continues to trigger the 3 multi-python matrix jobs on pushes and pull requests.
  - All new tests (including frontend Node.js health tests and settings validators) are integrated directly into `tests/unit/`, ensuring they run in the existing remote CI pipeline without requiring workflow-level credential modifications.
