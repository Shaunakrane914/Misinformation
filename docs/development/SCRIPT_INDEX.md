# Aegis Protocol — Authoritative Development Script Index

**Phase:** 7.2 (Workspace Organization, Repository Hygiene & Safe Structural Consolidation)  
**Status:** Authoritative Script Catalog & Usage Guide  
**Total Tracked Scripts:** 40  

---

## 1. Overview & Script Taxonomy

All executable scripts in `scripts/` are organized into six distinct functional categories. To guarantee zero regressions in existing CI workflows, developer runbooks, and test suites that import directly from `scripts.<module>`, all scripts remain accessible at their canonical `scripts/<name>.py` paths.

```text
scripts/
├── [1. Validation]    : Release-candidate gates, rollback verification, smoke harnesses
├── [2. Audits]        : Historical & live acquisition audits, single case-study runners
├── [3. Benchmarks]    : Cranfield retrieval benchmarks, fixture builders, load testing
├── [4. Evaluation]    : WELFake classical ML baseline, learned reranker, agent quality
├── [5. Diagnostics]   : Live provider health probes, endpoint checks, credential tests
└── [6. Development]   : Helper scripts for prompt extraction and developer tooling
```

---

## 2. Categorized Script Directory

### Category 1: Release Validation & Smoke Testing (`validation/`)

Scripts that prove deployment readiness, rollback safety, and runtime operational health.

| Script File | Primary Purpose | Verified Execution Command | Key Dependencies & Consumers |
| :--- | :--- | :--- | :--- |
| [`scripts/validate_release_candidate_smoke.py`](../../scripts/validate_release_candidate_smoke.py) | **Phase 7.1 Isolated Smoke Validation**: Executes 11 automated verification gates across all 4 agents, healthz, readyz, capabilities, and zero-evidence guard. | `python scripts/validate_release_candidate_smoke.py` | FastAPI TestClient; outputs `artifacts/phase7_1_smoke_validation_results.json`. Referenced in Phase 7.1 RC report. |
| [`scripts/validate_rollback_compatibility.py`](../../scripts/validate_rollback_compatibility.py) | **Phase 7.1 Rollback Compatibility**: Validates database schema backward compatibility and preservation of all 2,312 investigation dossiers. | `python scripts/validate_rollback_compatibility.py` | SQLite DB, `backend/data/dossiers/`. Referenced in `ROLLBACK_VERIFICATION.md`. |
| [`scripts/live_agent_smoke_test.py`](../../scripts/live_agent_smoke_test.py) | **Live Agent Smoke Verification Suite**: Multi-agent live test with secret sanitization and artifact output. | `python scripts/live_agent_smoke_test.py` | **Directly imported** by `tests/unit/test_live_smoke_harness.py`. Outputs `artifacts/live_agent_smoke_result.json`. |
| [`scripts/test_launch_video_integrity.py`](../../scripts/test_launch_video_integrity.py) | **Launch Video Integrity**: Automated verification of launch video asset resolution, aspect ratio, and codec. | `python scripts/test_launch_video_integrity.py` | Validates `brag-output/brag.mp4`. Referenced in `docs/audit/TESTING_BASELINE.md`. |

---

### Category 2: Empirical Audits (`audits/`)

Scripts that conduct structured evidence acquisition audits, reality checks, and historical milestone reconciliations.

| Script File | Primary Purpose | Verified Execution Command | Key Dependencies & Consumers |
| :--- | :--- | :--- | :--- |
| [`scripts/run_phase6_live_acquisition_audit.py`](../../scripts/run_phase6_live_acquisition_audit.py) | **Phase 6.6 Live Acquisition Reality Audit**: First-generation empirical audit of zero-auth scrapers. | `python scripts/run_phase6_live_acquisition_audit.py` | Outputs `artifacts/live_acquisition_audit/`. |
| [`scripts/run_phase6_6b_reconciliation.py`](../../scripts/run_phase6_6b_reconciliation.py) | **Phase 6.6B Ground-Truth Reconciliation**: Reconciles scraper capabilities with reality. | `python scripts/run_phase6_6b_reconciliation.py` | Outputs `artifacts/live_acquisition_audit_reconciled/`. |
| [`scripts/run_phase6_7_live_acquisition_audit.py`](../../scripts/run_phase6_7_live_acquisition_audit.py) | **Phase 6.7 Reality Audit**: Multi-channel acquisition reality audit across social sources. | `python scripts/run_phase6_7_live_acquisition_audit.py` | Outputs `artifacts/live_acquisition_audit_phase6_7/`. |
| [`scripts/run_phase6_8_resolution_benchmark.py`](../../scripts/run_phase6_8_resolution_benchmark.py) | **Phase 6.8.1 Entity Resolution Benchmark**: Evaluates entity-to-social-handle disambiguation. | `python scripts/run_phase6_8_resolution_benchmark.py` | Outputs `artifacts/live_acquisition_phase6_8/`. |
| [`scripts/run_pre_phase7_acquisition_audit.py`](../../scripts/run_pre_phase7_acquisition_audit.py) | **Pre-Phase 7 Acquisition Audit**: Bounded acquisition verification before architecture consolidation. | `python scripts/run_pre_phase7_acquisition_audit.py` | Outputs `artifacts/pre_phase7_audit/`. |
| [`scripts/run_complete_retrieval_fix_audit.py`](../../scripts/run_complete_retrieval_fix_audit.py) | **Complete Retrieval Quality Audit**: Validates entity filtering, temporal windowing, and relevance gating. | `python scripts/run_complete_retrieval_fix_audit.py` | Outputs `artifacts/complete_retrieval_fix_live_audit.json`. |
| [`scripts/run_final_retrieval_audit.py`](../../scripts/run_final_retrieval_audit.py) | **Final Authoritative Retrieval Audit**: Authoritative audit report generator. | `python scripts/run_final_retrieval_audit.py` | **Directly imported** by `tests/test_complete_retrieval_audit_integrity.py`. |
| [`scripts/run_fresh_4agent_audit.py`](../../scripts/run_fresh_4agent_audit.py) | **Blind Local 4-Agent Quality Audit**: Runs blind evaluations across all four agents. | `python scripts/run_fresh_4agent_audit.py` | Outputs `artifacts/fresh_4agent_audit/`. |
| [`scripts/run_realworld_investigation_audit.py`](../../scripts/run_realworld_investigation_audit.py) | **Real-World Investigation Audit**: End-to-end 4-agent case study on live news. | `python scripts/run_realworld_investigation_audit.py` | Generates full forensic dossier. |
| [`scripts/run_unlimited_case_study_audit.py`](../../scripts/run_unlimited_case_study_audit.py) | **Unlimited Time Case Study**: Exhaustive retrieval run for deep case analysis. | `python scripts/run_unlimited_case_study_audit.py` | Outputs `artifacts/unlimited_time_case_study_audit.json`. |
| [`scripts/run_live_case_study_granular_audit.py`](../../scripts/run_live_case_study_granular_audit.py) | **Granular Retrieval Audit**: Single-case deep-dive with per-fragment telemetry. | `python scripts/run_live_case_study_granular_audit.py` | Detailed fragment ranking outputs. |
| [`scripts/live_agent_json_audit.py`](../../scripts/live_agent_json_audit.py) | **Live Agent JSON Audit**: Verifies JSON schema conformity across live agent responses. | `python scripts/live_agent_json_audit.py` | Outputs schema validation report. |
| [`scripts/local_agent_json_audit.py`](../../scripts/local_agent_json_audit.py) | **Local Agent JSON Audit**: Offline verification of stored investigation responses. | `python scripts/local_agent_json_audit.py` | Referenced in `artifacts/retrieval_root_cause/FINAL_REPORT.md`. |

---

### Category 3: Benchmarks & Fixtures (`benchmarks/`)

Scripts that measure retrieval metrics, generate synthetic test fixtures, and stress test system capacity.

| Script File | Primary Purpose | Verified Execution Command | Key Dependencies & Consumers |
| :--- | :--- | :--- | :--- |
| [`scripts/benchmarks/run_retrieval_benchmark.py`](../../scripts/benchmarks/run_retrieval_benchmark.py) | **Core Retrieval Benchmark Runner**: Evaluates Cranfield metrics (Success@k, MRR, nDCG) on frozen fixtures. | `python scripts/benchmarks/run_retrieval_benchmark.py` | Reads `tests/retrieval_benchmark/scenarios.jsonl`. |
| [`scripts/run_retrieval_quality_benchmark.py`](../../scripts/run_retrieval_quality_benchmark.py) | **4-Agent Retrieval Benchmark Runner**: Root runner for agent retrieval quality. | `python scripts/run_retrieval_quality_benchmark.py` | **Directly imported** by `tests/test_retrieval_benchmark.py`. |
| [`scripts/build_retrieval_benchmark_fixtures.py`](../../scripts/build_retrieval_benchmark_fixtures.py) | **Benchmark Fixture Builder**: Compiles reproducible scenario fixtures for offline testing. | `python scripts/build_retrieval_benchmark_fixtures.py` | Generates candidate and scenario JSONL pools. |
| [`scripts/validate_retrieval_benchmark.py`](../../scripts/validate_retrieval_benchmark.py) | **Benchmark Schema Validator**: Validates integrity, schema, and formatting of frozen benchmark files. | `python scripts/validate_retrieval_benchmark.py` | **Directly imported** by `tests/retrieval_benchmark/test_benchmark_schema.py`. |
| [`scripts/benchmark_retrieval_backends.py`](../../scripts/benchmark_retrieval_backends.py) | **Retrieval Backend Benchmark**: Compares latency and throughput across acquisition adapters. | `python scripts/benchmark_retrieval_backends.py` | Evaluates native vs external scrapers. |
| [`scripts/load_test.py`](../../scripts/load_test.py) | **High-Concurrency Load Testing**: Asynchronous load test benchmark for FastAPI endpoints. | `python scripts/load_test.py` | Referenced in `docs/testing/CI_COVERAGE_MATRIX.md`. |

---

### Category 4: Evaluation & ML Baselines (`evaluation/`)

Scripts that compute scientific accuracy, train/evaluate learned rerankers, and perform ablation experiments.

| Script File | Primary Purpose | Verified Execution Command | Key Dependencies & Consumers |
| :--- | :--- | :--- | :--- |
| [`scripts/evaluate_dataset.py`](../../scripts/evaluate_dataset.py) | **Scientific Benchmark CLI**: Authoritative CLI for WELFake classical ML baseline (88.50%) and Learned Evidence Reranker. | `python scripts/evaluate_dataset.py --mode all_offline --seed 42` | Reads `backend/data/WELFake_Dataset.xlsx`. Extensively cited in `README.md`, `docs/EVALUATION.md`, `docs/TESTING.md`. |
| [`scripts/evaluate_all_agents.py`](../../scripts/evaluate_all_agents.py) | **4-Agent Quality Evaluation**: Comprehensive quality scoring across all four agents. | `python scripts/evaluate_all_agents.py` | **Directly imported** by `tests/integration/test_agent_quality_evaluation.py`. |
| [`scripts/evaluate_source_planner_modes.py`](../../scripts/evaluate_source_planner_modes.py) | **Source Planner A/B Evaluation**: Evaluates deterministic heuristic planning versus optional LLM planner. | `python scripts/evaluate_source_planner_modes.py` | Used in Phase 6.9.1 source planner evaluation. |
| [`scripts/run_live_retrieval_quality_evaluation.py`](../../scripts/run_live_retrieval_quality_evaluation.py) | **Live Retrieval Evaluation Harness**: Automated retrieval quality scoring on live web targets. | `python scripts/run_live_retrieval_quality_evaluation.py` | Referenced in ADR 0005. |
| [`scripts/run_retrieval_ablation.py`](../../scripts/run_retrieval_ablation.py) | **Retrieval Feature Ablation**: Measures ranking impact when stripping entity, temporal, or TF-IDF signals. | `python scripts/run_retrieval_ablation.py` | Referenced in `docs/EVALUATION.md`. |
| [`scripts/reproduce_retrieval_failures.py`](../../scripts/reproduce_retrieval_failures.py) | **Retrieval Failure Reproduction**: Replays known failure cases to verify bug fixes. | `python scripts/reproduce_retrieval_failures.py` | Forensic failure analysis tool. |

---

### Category 5: Diagnostics & Live Health Probes (`diagnostics/`)

Scripts that probe API keys, server endpoints, and live agent execution.

| Script File | Primary Purpose | Verified Execution Command | Key Dependencies & Consumers |
| :--- | :--- | :--- | :--- |
| [`scripts/diagnose_keys.py`](../../scripts/diagnose_keys.py) | **API Key Diagnosis**: Verifies availability and connectivity of configured provider keys without logging secrets. | `python scripts/diagnose_keys.py` | Reads environment settings. |
| [`scripts/verify_all_agents.py`](../../scripts/verify_all_agents.py) | **Multi-Agent CLI Verification**: Command-line verification of Scout, Trending, BrandShield, and Personal Watch. | `python scripts/verify_all_agents.py` | Direct agent invocation. |
| [`scripts/verify_live_after_fix.py`](../../scripts/verify_live_after_fix.py) | **Post-Fix Live QA**: Quick verification script run after acquisition fixes. | `python scripts/verify_live_after_fix.py` | Bounded live probe. |
| [`scripts/verify_live_scan.py`](../../scripts/verify_live_scan.py) | **Live Scan Verification**: Quick diagnostic tool for single-agent scan verification. | `python scripts/verify_live_scan.py` | Diagnostic utility. |
| [`scripts/test_agents_multi_cycle.py`](../../scripts/test_agents_multi_cycle.py) | **Multi-Cycle Agent Verification**: Multi-iteration loop testing agent resilience. | `python scripts/test_agents_multi_cycle.py` | Referenced in `docs/audit/TESTING_BASELINE.md`. |
| [`scripts/test_all_agents_live.py`](../../scripts/test_all_agents_live.py) | **Live 5-Agent Diagnostic**: Probes live execution across agents. | `python scripts/test_all_agents_live.py` | Referenced in `docs/audit/TESTING_BASELINE.md`. |
| [`scripts/test_all_endpoints.py`](../../scripts/test_all_endpoints.py) | **Endpoint & DB Verification**: Probes FastAPI endpoints and Supabase connectivity. | `python scripts/test_all_endpoints.py` | Referenced in `docs/audit/TESTING_BASELINE.md`. |
| [`scripts/test_api_docs_and_schema.py`](../../scripts/test_api_docs_and_schema.py) | **OpenAPI Schema Verification**: Verifies FastAPI `/openapi.json` contract. | `python scripts/test_api_docs_and_schema.py` | Referenced in `docs/audit/TESTING_BASELINE.md`. |
| [`scripts/test_fastapi_endpoints.py`](../../scripts/test_fastapi_endpoints.py) | **FastAPI Route Harness**: Diagnostic test suite for REST routes. | `python scripts/test_fastapi_endpoints.py` | Diagnostic runner. |

---

### Category 6: Development Tooling (`development/`)

Developer utility scripts.

| Script File | Primary Purpose | Verified Execution Command | Key Dependencies & Consumers |
| :--- | :--- | :--- | :--- |
| [`scripts/extract_mandate.py`](../../scripts/extract_mandate.py) | **Mandate Extractor**: Helper utility for extracting specification blocks. | `python scripts/extract_mandate.py` | Developer utility. |
| [`scripts/find_questions.py`](../../scripts/find_questions.py) | **Question Finder**: Helper utility for finding evaluation test questions. | `python scripts/find_questions.py` | Developer utility. |
| [`tools/make_audit_readme.py`](../../tools/make_audit_readme.py) | **Visual Audit Generator**: Compiles `docs/visual-audit/README.md` from screenshot records. | `python tools/make_audit_readme.py` | Generates visual audit index. |
