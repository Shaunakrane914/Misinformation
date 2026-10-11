# Aegis Protocol — Research & Evaluation Artifacts Catalog

**Status:** Authoritative Artifact Index & Research Evidence Directory  
**Total Tracked Milestone Suites:** 17 directories  
**Total Root Contract Files:** 14 files  

---

## 1. Directory Taxonomy & Classification

The `artifacts/` directory houses empirical research evidence, frozen benchmark metrics, multi-agent evaluation reports, and release candidate validation records produced across the development lifecycle of Aegis Protocol.

Per repository invariants (`AGENTS.md` and Phase 7.2C specifications), historical evidence, frozen datasets, and contractually bound test outputs are strictly protected from accidental deletion or destructive alteration.

```text
artifacts/
├── [1. Frozen Benchmark Evidence]      : Cranfield retrieval metrics & quality reports
├── [2. Historical Acquisition Audits]  : Provider reality audits across phases 6.6 – 7.0
├── [3. Agent Evaluation Reports]       : Multi-agent quality scores & source planner benchmarks
├── [4. Release Candidate Validation]   : Isolated smoke test gates & liveness verification
├── [5. Diagnostic & Root Cause Audits] : Forensic failure analyses & JSON schema verifiers
└── [6. Single-Case Investigation Logs] : Granular case study telemetry & forensic dossiers
```

---

## 2. Comprehensive Artifact Inventory

### Category 1: Frozen Benchmark Evidence (`benchmarks/`)

Empirical proof of retrieval quality, reranking accuracy, and latency metrics on immutable test collections.

| Artifact Path | Classification | Generating Runner | Description & Invariants |
| :--- | :--- | :--- | :--- |
| [`artifacts/retrieval_benchmark/`](retrieval_benchmark/) | **Frozen Benchmark Evidence** | `scripts/benchmarks/run_retrieval_benchmark.py` | Authoritative Cranfield benchmark outputs across 104 scenarios (MRR: 0.20 → 1.00, nDCG: 0.28 → 0.94). Contains `summary.json`, `summary.md`, and `retrieval_quality_report.md`. Contractually cited in `docs/FEATURE_STATUS.md` and `docs/EVALUATION.md`. **PROTECTED**. |
| [`artifacts/scraper_benchmark/`](scraper_benchmark/) | **Benchmark Evidence** | `scripts/benchmarks/benchmark_retrieval_backends.py` | Latency and throughput benchmarks comparing native adapters against legacy scrapers. |

---

### Category 2: Historical Acquisition Audits (`acquisition-audits/`)

Empirical zero-auth scraper reality checks, provider availability matrices, and resolution audits.

| Artifact Path | Classification | Generating Runner | Description & Invariants |
| :--- | :--- | :--- | :--- |
| [`artifacts/live_acquisition_audit/`](live_acquisition_audit/) | **Historical Audit** | `scripts/audits/run_phase6_live_acquisition_audit.py` | Phase 6.6 live acquisition audit records (2026-10-10 12:45 UTC). Contains verified capability matrix and raw operation telemetry. |
| [`artifacts/live_acquisition_audit_reconciled/`](live_acquisition_audit_reconciled/) | **Historical Audit** | `scripts/audits/run_phase6_6b_reconciliation.py` | Phase 6.6B ground-truth reconciliation between marketing claims and true provider availability. |
| [`artifacts/live_acquisition_audit_phase6_7/`](live_acquisition_audit_phase6_7/) | **Historical Audit** | `scripts/audits/run_phase6_7_live_acquisition_audit.py` | Phase 6.7 social acquisition audit across Twitter, Reddit, YouTube, and RSS. |
| [`artifacts/live_acquisition_phase6_8/`](live_acquisition_phase6_8/) | **Historical Audit** | `scripts/audits/run_phase6_8_resolution_benchmark.py` | Phase 6.8 entity resolution benchmark and raw HTTP evidence for corporate/VIP handles. |
| [`artifacts/pre_phase7_audit/`](pre_phase7_audit/) | **Historical Audit** | `scripts/audits/run_pre_phase7_acquisition_audit.py` | Bounded acquisition readiness audit prior to architecture consolidation. |
| [`artifacts/phase7_live_audit/`](phase7_live_audit/) | **Historical Audit** | `scripts/audits/run_fresh_4agent_audit.py` | Phase 7 live multi-agent capability and telemetry audit. |

---

### Category 3: Agent Evaluation Reports (`agent-evaluations/`)

Comprehensive scoring and adversarial robustness evaluations across all four sentinels.

| Artifact Path | Classification | Generating Runner | Description & Invariants |
| :--- | :--- | :--- | :--- |
| [`artifacts/all_agents_evaluation.json`](all_agents_evaluation.json) | **Agent Evaluation Report** | `scripts/evaluation/evaluate_all_agents.py` | Full quality metrics across Scout, Trending, BrandShield, and Personal Watch. Contractually imported and verified by `tests/integration/test_agent_quality_evaluation.py`. |
| [`artifacts/all_agents_evaluation.md`](all_agents_evaluation.md) | **Agent Evaluation Report** | `scripts/evaluation/evaluate_all_agents.py` | Markdown executive summary for `all_agents_evaluation.json`. |
| [`artifacts/fresh_4agent_audit/`](fresh_4agent_audit/) | **Agent Evaluation Report** | `scripts/audits/run_fresh_4agent_audit.py` | Blind local quality audit across all four production agents. |
| [`artifacts/phase6_9_1_capability_audit/`](phase6_9_1_capability_audit/) | **Capability Audit** | `scripts/audits/run_pre_phase7_acquisition_audit.py` | Dynamic operation capability health status audit. |
| [`artifacts/phase6_9_1_planner_evaluation/`](phase6_9_1_planner_evaluation/) | **Planner Evaluation** | `scripts/evaluation/evaluate_source_planner_modes.py` | Empirical evaluation comparing deterministic heuristic source planning vs optional LLM planning. |
| [`artifacts/live_retrieval_evaluation/`](live_retrieval_evaluation/) | **Retrieval Evaluation** | `scripts/evaluation/run_live_retrieval_quality_evaluation.py` | Live web retrieval evaluation scores across query sets. |

---

### Category 4: Release Candidate Validation (`release-validation/`)

Automated gate results proving staging readiness and runtime stability.

| Artifact Path | Classification | Generating Runner | Description & Invariants |
| :--- | :--- | :--- | :--- |
| [`artifacts/phase7_1_smoke_validation_results.json`](phase7_1_smoke_validation_results.json) | **Release Validation** | `scripts/validation/validate_release_candidate_smoke.py` | 11-gate automated release-candidate smoke validation results covering probes, healthz, readyz, capabilities, 4 agents, and negative guards. Cited in `docs/architecture/PHASE7_1_RELEASE_CANDIDATE_REPORT.md` and `docs/testing/ISOLATED_SMOKE_TEST_REPORT.md`. |
| [`artifacts/live_agent_smoke_result.json`](live_agent_smoke_result.json) | **Release Validation** | `scripts/validation/live_agent_smoke_test.py` | Multi-agent live smoke verification with secret scrubbing. Contractually verified by `tests/unit/test_live_smoke_harness.py`. |

---

### Category 5: Forensic Audits & Root Cause Analyses (`diagnostics/`)

Failure investigations and schema conformance reports.

| Artifact Path | Classification | Generating Runner | Description & Invariants |
| :--- | :--- | :--- | :--- |
| [`artifacts/retrieval_root_cause/`](retrieval_root_cause/) | **Diagnostic Analysis** | `scripts/evaluation/reproduce_retrieval_failures.py` | Forensic failure analysis and `FINAL_REPORT.md` analyzing historical retrieval regressions. |
| [`artifacts/complete_retrieval_fix_live_audit.json`](complete_retrieval_fix_live_audit.json) & [`.md`](complete_retrieval_fix_live_audit.md) | **Audit Evidence** | `scripts/audits/run_complete_retrieval_fix_audit.py` | Verification evidence for entity filtering and temporal windowing fixes. |
| [`artifacts/final_retrieval_audit.json`](final_retrieval_audit.json) & [`.md`](final_retrieval_audit.md) | **Authoritative Audit** | `scripts/audits/run_final_retrieval_audit.py` | Authoritative retrieval audit report. Contractually verified by `tests/test_complete_retrieval_audit_integrity.py`. |
| [`artifacts/live_agent_verification/`](live_agent_verification/) | **Verification Log** | `scripts/diagnostics/verify_all_agents.py` | Multi-agent runtime execution traces. |
| [`artifacts/live_agent_verification_after_fix/`](live_agent_verification_after_fix/) | **Verification Log** | `scripts/diagnostics/verify_live_after_fix.py` | Post-fix runtime verification traces. |
| [`artifacts/live_json_audit/`](live_json_audit/) | **Schema Audit** | `scripts/audits/live_agent_json_audit.py` | JSON schema validation results on live responses. |
| [`artifacts/local_json_audit/`](local_json_audit/) | **Schema Audit** | `scripts/audits/local_agent_json_audit.py` | JSON schema validation results on local stored dossiers. |

---

### Category 6: Single-Case Study Reports (`case-studies/`)

Granular telemetry for representative research investigations.

| Artifact Path | Classification | Generating Runner | Description & Invariants |
| :--- | :--- | :--- | :--- |
| [`artifacts/single_case_4_agent_fetch_audit.json`](single_case_4_agent_fetch_audit.json) & [`.md`](single_case_4_agent_fetch_audit.md) | **Case Study Report** | `scripts/audits/run_realworld_investigation_audit.py` | Real-world case study investigation dossier across 4 sentinels. |
| [`artifacts/single_case_study_retrieval_audit.json`](single_case_study_retrieval_audit.json) & [`.md`](single_case_study_retrieval_audit.md) | **Case Study Report** | `scripts/audits/run_live_case_study_granular_audit.py` | Granular per-fragment retrieval telemetry for deep-dive investigation. |
| [`artifacts/unlimited_time_case_study_audit.json`](unlimited_time_case_study_audit.json) & [`.md`](unlimited_time_case_study_audit.md) | **Case Study Report** | `scripts/audits/run_unlimited_case_study_audit.py` | Exhaustive investigation trace run without timeout bounds. |

---

## 3. Contractual Path Retention Policy

Every root-level file in `artifacts/` corresponds to a **strict contracted output path** defined in active Python scripts, regression tests, or authoritative documentation:

1. **Test Verification Gates**: `tests/test_complete_retrieval_audit_integrity.py`, `tests/integration/test_agent_quality_evaluation.py`, and `tests/unit/test_live_smoke_harness.py` expect canonical file paths directly in `artifacts/`.
2. **Git Tracking Policy**: `.gitignore` enforces a default `/artifacts/*` ignore pattern with explicit allowlist rules (`!/artifacts/<filename>`) for contracted files.
3. **Release Reproducibility**: Runbooks and CI specifications (`docs/architecture/PHASE7_1_RELEASE_CANDIDATE_REPORT.md`, `docs/testing/ISOLATED_SMOKE_TEST_REPORT.md`) directly link to canonical artifact locations.

To prevent silent build breakage or lost provenance, established paths are preserved while this index provides clear structural navigation.
