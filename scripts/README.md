# Aegis Protocol — Development Scripts Catalog

This directory contains executable tools, benchmark runners, evaluation harnesses, and release-validation scripts.

> **Full Documentation**: For an exhaustive catalog of all 40 scripts, their dependencies, and usage examples, see the canonical [Script Index](../docs/development/SCRIPT_INDEX.md).

---

## Quick Navigation: Top Recommended Commands

### 1. Release Candidate & Deployment Validation
```bash
# Run isolated release candidate smoke validation (11 gates, all 4 agents)
python scripts/validate_release_candidate_smoke.py

# Verify database and dossier rollback compatibility
python scripts/validate_rollback_compatibility.py
```

### 2. Scientific Benchmark & Evaluation CLI
```bash
# Run all offline ML benchmarks (WELFake classical ML baseline + Learned Reranker)
python scripts/evaluate_dataset.py --mode all_offline --seed 42

# Run Cranfield retrieval quality benchmark on frozen fixtures
python scripts/benchmarks/run_retrieval_benchmark.py
```

### 3. Agent Quality & Live Smoke
```bash
# Run 4-agent quality evaluation harness
python scripts/evaluate_all_agents.py

# Run live agent smoke verification (with automatic secret scrubbing)
python scripts/live_agent_smoke_test.py
```

---

## Functional Categorization

1. **Validation (`validation/`)**:
   - `validate_release_candidate_smoke.py`, `validate_rollback_compatibility.py`, `live_agent_smoke_test.py`, `test_launch_video_integrity.py`.
2. **Audits (`audits/`)**:
   - `run_phase6_...`, `run_phase6_7_...`, `run_phase6_8_...`, `run_pre_phase7_...`, `run_complete_retrieval_fix_audit.py`, `run_final_retrieval_audit.py`, `run_fresh_4agent_audit.py`, `run_realworld_investigation_audit.py`, `run_unlimited_case_study_audit.py`, `run_live_case_study_granular_audit.py`.
3. **Benchmarks (`benchmarks/`)**:
   - `benchmarks/run_retrieval_benchmark.py`, `run_retrieval_quality_benchmark.py`, `build_retrieval_benchmark_fixtures.py`, `validate_retrieval_benchmark.py`, `benchmark_retrieval_backends.py`, `load_test.py`.
4. **Evaluation (`evaluation/`)**:
   - `evaluate_dataset.py`, `evaluate_all_agents.py`, `evaluate_source_planner_modes.py`, `run_live_retrieval_quality_evaluation.py`, `run_retrieval_ablation.py`, `reproduce_retrieval_failures.py`.
5. **Diagnostics (`diagnostics/`)**:
   - `diagnose_keys.py`, `verify_all_agents.py`, `verify_live_after_fix.py`, `verify_live_scan.py`, `test_agents_multi_cycle.py`, `test_all_agents_live.py`, `test_all_endpoints.py`, `test_api_docs_and_schema.py`, `test_fastapi_endpoints.py`.
6. **Development (`development/`)**:
   - `extract_mandate.py`, `find_questions.py`.

*Note: All scripts remain at their primary paths to preserve backward compatibility for automated tests and CI runners.*
