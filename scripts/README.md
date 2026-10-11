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

## Functional Categorization & Physical Structure

All scripts are physically organized into Python packages with `__init__.py`:

1. **Validation (`scripts/validation/`)**:
   - `validate_release_candidate_smoke.py`: 11-gate release validation across all 4 agents.
   - `validate_rollback_compatibility.py`: SQLite schema and dossier storage rollback safety.
   - `validate_retrieval_benchmark.py`: Benchmark fixture schema & integrity validator.
   - `live_agent_smoke_test.py`: Live multi-agent smoke verification with secret scrubbing.
   - `test_launch_video_integrity.py`: Launch video asset codec & resolution verification.

2. **Audits (`scripts/audits/`)**:
   - `run_final_retrieval_audit.py`: Authoritative retrieval audit generator.
   - `run_complete_retrieval_fix_audit.py`: Bounded retrieval quality audit runner.
   - `run_pre_phase7_acquisition_audit.py`: Pre-Phase 7 acquisition audit.
   - `run_phase6_live_acquisition_audit.py`, `run_phase6_6b_reconciliation.py`, `run_phase6_7_live_acquisition_audit.py`, `run_phase6_8_resolution_benchmark.py`: Empirical phase audits.
   - `run_fresh_4agent_audit.py`, `run_realworld_investigation_audit.py`, `run_unlimited_case_study_audit.py`, `run_live_case_study_granular_audit.py`: Case study & blind audit harnesses.
   - `live_agent_json_audit.py`, `local_agent_json_audit.py`: Live and offline JSON contract auditors.

3. **Benchmarks (`scripts/benchmarks/`)**:
   - `run_retrieval_benchmark.py`: Cranfield retrieval benchmark runner on frozen fixtures.
   - `run_retrieval_quality_benchmark.py`: Multi-agent retrieval quality benchmark runner.
   - `build_retrieval_benchmark_fixtures.py`: Benchmark fixture builder.
   - `benchmark_retrieval_backends.py`: Latency/throughput backend benchmark.
   - `load_test.py`: High-concurrency FastAPI load test benchmark.

4. **Evaluation (`scripts/evaluation/`)**:
   - `evaluate_dataset.py`: Authoritative WELFake ML & Learned Evidence Reranker CLI.
   - `evaluate_all_agents.py`: 4-agent quality evaluation harness.
   - `evaluate_source_planner_modes.py`: Deterministic vs LLM source planner evaluation.
   - `run_live_retrieval_quality_evaluation.py`: Live retrieval quality scoring.
   - `run_retrieval_ablation.py`: Feature ablation experiment runner.
   - `reproduce_retrieval_failures.py`: Failure reproduction harness.

5. **Diagnostics (`scripts/diagnostics/`)**:
   - `diagnose_keys.py`: API key and network connectivity probe.
   - `verify_all_agents.py`, `verify_live_after_fix.py`, `verify_live_scan.py`: Direct agent CLI verification probes.
   - `test_agents_multi_cycle.py`, `test_all_agents_live.py`: Multi-cycle agent stability probes.
   - `test_all_endpoints.py`, `test_api_docs_and_schema.py`, `test_fastapi_endpoints.py`: Endpoint diagnostics.

6. **Development (`scripts/development/`)**:
   - `extract_mandate.py`: Helper script for extracting specification blocks.
   - `find_questions.py`: Helper script for evaluation question discovery.

### Backward-Compatibility Root Wrappers

To guarantee zero breakage of existing runbooks, documentation, and external CLI invocations, thin compatibility wrappers are preserved at `scripts/` root for the most frequently executed commands:
- `scripts/validate_release_candidate_smoke.py` -> forwards to `scripts/validation/validate_release_candidate_smoke.py`
- `scripts/validate_rollback_compatibility.py` -> forwards to `scripts/validation/validate_rollback_compatibility.py`
- `scripts/evaluate_dataset.py` -> forwards to `scripts/evaluation/evaluate_dataset.py`
- `scripts/live_agent_smoke_test.py` -> forwards to `scripts/validation/live_agent_smoke_test.py`
- `scripts/run_retrieval_quality_benchmark.py` -> forwards to `scripts/benchmarks/run_retrieval_quality_benchmark.py`

