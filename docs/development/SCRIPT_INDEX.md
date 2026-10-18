# Aegis Protocol — Authoritative Development Script Index

**Phase:** 7.2 (Workspace Organization, Repository Hygiene & Safe Structural Consolidation)  
**Status:** Authoritative Script Catalog & Usage Guide  
**Historical Phase 7.2 Tracked Scripts:** 40

This count is the historical Phase 7.2 snapshot. For current validation behavior and safe continuation, use the [coding-agent handoff](../handoffs/README.md). The validators below do not establish live-provider health or deployed rollback, and their default execution never overwrites historical audit reports.

---

## 1. Overview & Script Taxonomy

### Terminal-first / strict API-cost controls — 2026-10-18

- [Local terminal quality runner](../../scripts/audits/run_terminal_agent_quality.py): `--allow-live --env-file <existing-env> --output-dir <new-dir>`; repeat `--case "agent:input"` for bounded cases, otherwise twelve inputs. Normal acquisition is live, **AI credentials are excluded by default** and mocks remain off. `--capture-from <saved-native-directory>` instead blocks network and reprocesses only recorded acquisition bytes through current agents/API. Saved reads are not fresh transport observations. Review JSON/SSE and per-case pipeline exports before browser replay. Fresh persistence only, no historical writes.
- Optional advice requires a separately model-verified explicit `advisory_run` and investigation scope. Model identity is strictly `gemini-2.5-flash-lite`, <=160 output tokens, <=6,000 prompt characters, one attempt / 2s, one request/investigation and three/run. Shared SQLite reservations/cooldown cover entry points sharing its ledger path. No model/key fallback, automatic quota probes or native generative verdict/report synthesis. The audit runner's legacy `--allow-live-ai` flag only loads credentials; it does not create advisory authorization. **No generation is authorized in this checkpoint.** [Current handoff](../handoffs/2026-10-18_INTELLIGENCE_PIPELINE_COMPLETION.md).

### Bounded AI / PDF diagnostics — 2026-10-17

- [Explicit model-list diagnostic](../../scripts/diagnostics/check_ai_advisory_runtime.py): requires `--allow-live --env-file <existing-env> --output <new-json>`. At most one bounded account model-list request; **never generates**, rotates keys or probes quota recovery. Exit 2 means strict model support was not observed. Listing does not prove quota, key refresh or successful inference. Do not run without separate live authorization.
- The existing extraction cycle accepts `--extra-web-url <observed-public-pdf>` to exercise bounded PDF reading in addition to all 52 original targets. One extra target makes 53 executions, not 53 supported operations. Existing source display scaffolds remain explicitly separate from native agent investigations.

[Implementation, test commands and current-code live review](../handoffs/2026-10-17_ROLE_AWARE_AI_EVIDENCE.md).

### Continuous source-intelligence additions — 2026-10-17

- [Saved investigation comparison](../../scripts/audits/summarize_intelligence_loop.py): `--baseline <saved-native-dir> --after <saved-native-dir> --output <new-json>`. Read-only inventory of native records, depth labels, retained words, citation joins, read outcomes and stage timings; no provider calls or inferred accuracy. Refuses an existing output file.
- [Normal browser audit](../../scripts/audits/run_phase9_four_agent_browser_audit.py): default fixed twelve-input matrix; repeat `--case "agent:literal input"` for up to four additional controls. Records actual acquired-text metrics, failed resources and keyboard source-inspection screenshots. `--replay-dir` is explicitly saved SSE replay, not live research. Requires an existing server environment and actual pinned Chart.js 4.4.1 bytes; audit persistence/notifications are isolated.
- [All-operation extraction cycle](../../scripts/audits/run_phase9_extraction_cycle.py): preserves 52-operation coverage, captures public URL/ID/author/date where observed, and reads Git diagnostics explicitly as UTF-8 on Windows. Repeated source samples are not a research accuracy benchmark.

[Commands, results, failure history and next acceptance queue](../handoffs/2026-10-17_CONTINUOUS_SOURCE_INTELLIGENCE.md); [source-by-source and agent review](../testing/CONTINUOUS_SOURCE_INTELLIGENCE_REVIEW_2026-10-17.md). Do not overwrite old proof, frozen benchmarks or dossiers.

### Source text pipeline — 2026-10-17

- [Repeated source cycle](../../scripts/audits/run_phase9_extraction_cycle.py): `--all-operations` covers all 52 registered operations; `--capture-samples` retains bounded public text in fresh output; `--env-file` explicitly reads existing source settings without changing them. Source fingerprint stability and raw/readable measurements are not research accuracy.
- [Source display audit](../../scripts/audits/audit_source_text_frontend.py): requires a saved cycle directory, round number, pinned Chart.js asset and fresh output path. Exact native inspections in a labeled display scaffold across all four pages at 320/390/1440px. Checks both document overflow and evidence-card clipping; not native agent/API acceptance.
- [Source API smoke](../../scripts/audits/run_phase9_source_api_smoke.py): real local FastAPI extraction requests with word/byte metrics, isolated persistence and explicit access-context observation. No LLM inference or whole-source completeness claim.

Commands, results and limitations: [handoff](../handoffs/2026-10-17_SOURCE_TEXT_PIPELINE.md).

### Phase 9 remediation additions — 2026-10-16

- [Reference replay](../../scripts/evaluation/run_phase9_benchmark.py): requires `--output-dir`; runtime source qualification by default, explicit legacy oracle flag, never overwrites existing evidence. Not live accuracy.
- [Claim probes](../../scripts/audits/run_phase9_claim_probes.py): explicit `--allow-live --env-file --output-dir`, temporary persistence, real research/dossier/report path; optional named rechecks and baseline worktree. No HTTP/browser acceptance claim.
- [Four-agent browser audit](../../scripts/audits/run_phase9_four_agent_browser_audit.py): actual page buttons/local SSE for three inputs each, screenshots and count invariants. `--replay-dir` explicitly switches to saved-event replay without reacquisition. Requires an actual pinned Chart.js asset and existing Playwright/Chromium.
- [Rendered controls](../../scripts/audits/run_phase9_render_controls.py): separately labeled synthetic verdict/hostile/large/zero-source controls plus exact saved backend reports. Measures internal card clipping and keyboard disclosures; not screen-reader/contrast certification.

Use fresh output paths. See the [dated handoff](../handoffs/2026-10-16_PHASE9_REMEDIATION.md) for command templates, actual failures, counts and source-access limits.

### Independent Phase 8 additions — 2026-10-14

- [Real API investigation audit](../../scripts/audits/run_realworld_investigation_audit.py): `--allow-live --profile apple --output-root <new-directory>`; one call per actual agent, temporary persistence, sanitized payloads. Execution success is not research PASS.
- [Authoritative live probe](../../scripts/audits/run_phase8d_authoritative_source_live_probe.py): `--output-root <new-directory>`; append-only, SEC metadata/NVD/abstract/ClaimReview distinctions, explicit config/auth limitations.
- [Reference holdout](../../scripts/evaluation/run_phase8_reference_holdout.py): `--output-root <new-directory>`; optional `--engine-root <baseline-worktree>` for comparison. Source-adjudicated component replay, not human annotations/live retrieval/population accuracy.
- [Result rendering stress](../../scripts/audits/audit_phase8_result_stress.py): `--base-url <served-frontend> --api-results <summary.json> --output-root <new-directory> --axe-script <installed-file>`; recorded API replay and labeled synthetic large/hostile controls, not fresh browser requests.
- [General rendering audit](../../scripts/audits/audit_phase8_frontend_rendering.py) now accepts `--api-results <summary.json>` alongside optional `--test-fixtures`; explicit input provenance is retained.

See the [review handoff](../handoffs/2026-10-14_PHASE8_INDEPENDENT_REVIEW.md) for actual results and limitations. Existing output directories are rejected; never redirect these scripts over tracked benchmark results.

All executable scripts in `scripts/` are physically organized into six distinct functional package directories with `__init__.py`. To ensure backward compatibility for legacy external CLI callers, key root entry points (`validate_release_candidate_smoke.py`, `validate_rollback_compatibility.py`, `evaluate_dataset.py`, `live_agent_smoke_test.py`, `run_retrieval_quality_benchmark.py`) are maintained via lightweight wrappers at the `scripts/` root.

```text
scripts/
├── validation/     : Release-candidate gates, rollback verification, smoke harnesses
├── audits/         : Historical & live acquisition audits, single case-study runners
├── benchmarks/     : Cranfield retrieval benchmarks, fixture builders, load testing
├── evaluation/     : WELFake classical ML baseline, learned reranker, agent quality
├── diagnostics/    : Live provider health probes, endpoint checks, credential tests
└── development/    : Helper scripts for prompt extraction and developer tooling
```

---

## 2. Categorized Script Directory

### Category 1: Release Validation & Smoke Testing (`validation/`)

Scripts that exercise explicit offline release/persistence gates or separately authorized live probes. Interpret each script's scope and exit status before making a readiness claim.

| Script File | Primary Purpose | Verified Execution Command | Key Dependencies & Consumers |
| :--- | :--- | :--- | :--- |
| [`scripts/validation/validate_release_candidate_smoke.py`](../../scripts/validation/validate_release_candidate_smoke.py) | **Isolated Offline Smoke**: Exercises health/capabilities, four agent entrypoints and uncertain zero-evidence behavior in a fresh subprocess. *(Root wrapper preserved at `scripts/validate_release_candidate_smoke.py`)* | `python scripts/validation/validate_release_candidate_smoke.py` | Temporary SQLite/dossiers; reports to stdout. Optional `--output` creates a new report exclusively; it never overwrites an existing report. |
| [`scripts/validation/validate_rollback_compatibility.py`](../../scripts/validation/validate_rollback_compatibility.py) | **Offline Persistence and Historical Reader Compatibility**: Fresh producer/consumer and actual baseline readers; read-only archive inspection. *(Root wrapper preserved at `scripts/validate_rollback_compatibility.py`)* | `python scripts/validation/validate_rollback_compatibility.py` | Temporary persistence plus protected archive reads. Exit 1 currently reports 55 malformed historical JSON files; deployed rollback remains unverified. |
| [`scripts/validation/verify_frozen_benchmarks.py`](../../scripts/validation/verify_frozen_benchmarks.py) | **Frozen Dataset Integrity**: Checks pinned hashes, normalizing only CRLF/LF. | `python scripts/validation/verify_frozen_benchmarks.py` | Read-only scenarios/candidates/labels verification; fails on changed frozen content. |
| [`scripts/validation/inventory_historical_dossiers.py`](../../scripts/validation/inventory_historical_dossiers.py) | **Historical Dossier Recovery Inventory**: Read-only SHA-256 and parser-error inventory with optional repository/Git-history candidate discovery. | `python scripts/validation/inventory_historical_dossiers.py --candidate-root . --include-git-history` | Never copies dossier contents or repairs originals. Optional `--output` creates a new report exclusively. |
| [`scripts/validation/isolated_runtime.py`](../../scripts/validation/isolated_runtime.py) | **Isolation Support Module**: Temporary storage, blank credentials, network/DNS/provider-CLI guards and exclusive report creation. | Imported by validators and test setup; not a standalone acceptance gate | Keep Windows internal socketpair compatibility; never loosen guards to satisfy a live-I/O-dependent test. |
| [`scripts/validation/live_agent_smoke_test.py`](../../scripts/validation/live_agent_smoke_test.py) | **Live Agent Smoke Verification Suite**: Multi-agent live test with secret sanitization and artifact output. *(Root wrapper preserved at `scripts/live_agent_smoke_test.py`)* | `python scripts/validation/live_agent_smoke_test.py` | **Directly imported** by `tests/unit/test_live_smoke_harness.py`. Outputs `artifacts/live_agent_smoke_result.json`. |
| [`scripts/validation/test_launch_video_integrity.py`](../../scripts/validation/test_launch_video_integrity.py) | **Launch Video Integrity**: Automated verification of launch video asset resolution, aspect ratio, and codec. | `python scripts/validation/test_launch_video_integrity.py` | Validates `brag-output/brag.mp4`. Referenced in `docs/audit/TESTING_BASELINE.md`. |


---

### Category 2: Empirical Audits (`audits/`)

Scripts that conduct structured evidence acquisition audits, reality checks, and historical milestone reconciliations.

| Script File | Primary Purpose | Verified Execution Command | Key Dependencies & Consumers |
| :--- | :--- | :--- | :--- |
| [`scripts/audits/run_phase6_live_acquisition_audit.py`](../../scripts/audits/run_phase6_live_acquisition_audit.py) | **Phase 6.6 Live Acquisition Reality Audit**: First-generation empirical audit of zero-auth scrapers. | `python scripts/audits/run_phase6_live_acquisition_audit.py` | Outputs `artifacts/live_acquisition_audit/`. |
| [`scripts/audits/run_phase6_6b_reconciliation.py`](../../scripts/audits/run_phase6_6b_reconciliation.py) | **Phase 6.6B Ground-Truth Reconciliation**: Reconciles scraper capabilities with reality. | `python scripts/audits/run_phase6_6b_reconciliation.py` | Outputs `artifacts/live_acquisition_audit_reconciled/`. |
| [`scripts/audits/run_phase6_7_live_acquisition_audit.py`](../../scripts/audits/run_phase6_7_live_acquisition_audit.py) | **Phase 6.7 Reality Audit**: Multi-channel acquisition reality audit across social sources. | `python scripts/audits/run_phase6_7_live_acquisition_audit.py` | Outputs `artifacts/live_acquisition_audit_phase6_7/`. |
| [`scripts/audits/run_phase6_8_resolution_benchmark.py`](../../scripts/audits/run_phase6_8_resolution_benchmark.py) | **Phase 6.8.1 Entity Resolution Benchmark**: Evaluates entity-to-social-handle disambiguation. | `python scripts/audits/run_phase6_8_resolution_benchmark.py` | Outputs `artifacts/live_acquisition_phase6_8/`. |
| [`scripts/audits/run_pre_phase7_acquisition_audit.py`](../../scripts/audits/run_pre_phase7_acquisition_audit.py) | **Pre-Phase 7 Acquisition Audit**: Bounded acquisition verification before architecture consolidation. | `python scripts/audits/run_pre_phase7_acquisition_audit.py` | Outputs `artifacts/pre_phase7_audit/`. |
| [`scripts/audits/run_phase8_live_acquisition_audit.py`](../../scripts/audits/run_phase8_live_acquisition_audit.py) | **Phase 8A Real Acquisition Proof**: Exercises all 16 protected operations through the production router, records mandatory outcome classes and can consolidate bounded retry runs. | `python scripts/audits/run_phase8_live_acquisition_audit.py --include-auxiliary` | Writes exclusively to a new `artifacts/phase8_live_acquisition/<timestamp>/` directory; never retains full bodies or credentials. |
| [`scripts/audits/run_phase8_auxiliary_adapter_probe.py`](../../scripts/audits/run_phase8_auxiliary_adapter_probe.py) | **Phase 8B auxiliary adapter spot-check**: Probes the separate GitHub, web and YouTube direct adapters against three fixed public targets. This is not the 16-operation gate. | `python -m scripts.audits.run_phase8_auxiliary_adapter_probe` | Writes a new `artifacts/phase8_auxiliary_adapter_probes/<timestamp>/summary.json` containing bounded observation metadata, not response bodies. |
| [`scripts/audits/run_phase8_github_issue_comment_probe.py`](../../scripts/audits/run_phase8_github_issue_comment_probe.py) | **Phase 8B opt-in issue-discussion spot-check**: Exercises capped GitHub issue-comment follow-up on a fixed public repository and records only status/field-presence metrics. | `python -m scripts.audits.run_phase8_github_issue_comment_probe` | Writes a new `artifacts/phase8_issue_comment_probes/<timestamp>/summary.json`; never saves comment or issue text. |
| [`scripts/audits/audit_phase8_frontend_rendering.py`](../../scripts/audits/audit_phase8_frontend_rendering.py) | **Phase 8E real-browser layout and keyboard smoke**: Renders all four agent pages at 1440/390/320px. Optional clearly labeled synthetic contract fixtures exercise sparse/adversarial rendering, escaped URLs, reveal timing, and dossier focus/Escape. | `python scripts/audits/audit_phase8_frontend_rendering.py --base-url http://127.0.0.1:8765 --output-root artifacts/phase8_frontend_visual/<new-run> --test-fixtures` | Requires an already running localhost server for `frontend/`, Python Playwright and Chromium. Output directory must not exist; screenshots are not live evidence. |
| [`scripts/audits/audit_phase8_accessibility.py`](../../scripts/audits/audit_phase8_accessibility.py) | **Phase 8E automated accessibility scan**: axe-core WCAG A/AA and best-practice checks on initial rendered states at the same three widths. Records violations and incomplete rules. | `python scripts/audits/audit_phase8_accessibility.py --base-url http://127.0.0.1:8765 --axe-script <local-axe.min.js> --output-root artifacts/phase8_frontend_accessibility/<new-run>` | Explicit local axe-core dependency; does not establish screen-reader, modal-state or manual visual acceptance. |
| [`scripts/audits/summarize_phase8_extraction.py`](../../scripts/audits/summarize_phase8_extraction.py) | **Phase 8B richness summary**: Computes bounded important-field population and evidence-length metrics from retained probe JSONL; not a raw-provider completeness score. | `python -m scripts.audits.summarize_phase8_extraction --probe-records <new-probe.jsonl> --output <new-summary.json>` | Performs no live acquisition and refuses to overwrite an existing summary. |
| [`scripts/audits/run_complete_retrieval_fix_audit.py`](../../scripts/audits/run_complete_retrieval_fix_audit.py) | **Complete Retrieval Quality Audit**: Validates entity filtering, temporal windowing, and relevance gating. | `python scripts/audits/run_complete_retrieval_fix_audit.py` | Outputs `artifacts/complete_retrieval_fix_live_audit.json`. |
| [`scripts/audits/run_final_retrieval_audit.py`](../../scripts/audits/run_final_retrieval_audit.py) | **Final Authoritative Retrieval Audit**: Authoritative audit report generator. | `python scripts/audits/run_final_retrieval_audit.py` | **Directly imported** by `tests/test_complete_retrieval_audit_integrity.py`. |
| [`scripts/audits/run_fresh_4agent_audit.py`](../../scripts/audits/run_fresh_4agent_audit.py) | **Blind Local 4-Agent Quality Audit**: Runs blind evaluations across all four agents. | `python scripts/audits/run_fresh_4agent_audit.py` | Outputs `artifacts/fresh_4agent_audit/`. |
| [`scripts/audits/run_realworld_investigation_audit.py`](../../scripts/audits/run_realworld_investigation_audit.py) | **Real-World Investigation Audit**: End-to-end 4-agent case study on live news. | `python scripts/audits/run_realworld_investigation_audit.py` | Generates full forensic dossier. |
| [`scripts/audits/run_unlimited_case_study_audit.py`](../../scripts/audits/run_unlimited_case_study_audit.py) | **Unlimited Time Case Study**: Exhaustive retrieval run for deep case analysis. | `python scripts/audits/run_unlimited_case_study_audit.py` | Outputs `artifacts/unlimited_time_case_study_audit.json`. |
| [`scripts/audits/run_live_case_study_granular_audit.py`](../../scripts/audits/run_live_case_study_granular_audit.py) | **Granular Retrieval Audit**: Single-case deep-dive with per-fragment telemetry. | `python scripts/audits/run_live_case_study_granular_audit.py` | Detailed fragment ranking outputs. |
| [`scripts/audits/live_agent_json_audit.py`](../../scripts/audits/live_agent_json_audit.py) | **Live Agent JSON Audit**: Verifies JSON schema conformity across live agent responses. | `python scripts/audits/live_agent_json_audit.py` | Outputs schema validation report. |
| [`scripts/audits/local_agent_json_audit.py`](../../scripts/audits/local_agent_json_audit.py) | **Local Agent JSON Audit**: Offline verification of stored investigation responses. | `python scripts/audits/local_agent_json_audit.py` | Referenced in `artifacts/retrieval_root_cause/FINAL_REPORT.md`. |

---

### Category 3: Benchmarks & Fixtures (`benchmarks/`)

Scripts that measure retrieval metrics, generate synthetic test fixtures, and stress test system capacity.

| Script File | Primary Purpose | Verified Execution Command | Key Dependencies & Consumers |
| :--- | :--- | :--- | :--- |
| [`scripts/benchmarks/run_retrieval_benchmark.py`](../../scripts/benchmarks/run_retrieval_benchmark.py) | **Core Retrieval Benchmark Runner**: Evaluates Cranfield metrics (Success@k, MRR, nDCG) on frozen fixtures. | `python scripts/benchmarks/run_retrieval_benchmark.py` | Reads `tests/retrieval_benchmark/scenarios.jsonl`. |
| [`scripts/benchmarks/run_retrieval_quality_benchmark.py`](../../scripts/benchmarks/run_retrieval_quality_benchmark.py) | **4-Agent Retrieval Benchmark Runner**: Root runner for agent retrieval quality. *(Root wrapper preserved at `scripts/run_retrieval_quality_benchmark.py`)* | `python scripts/benchmarks/run_retrieval_quality_benchmark.py` | **Directly imported** by `tests/test_retrieval_benchmark.py`. |
| [`scripts/benchmarks/build_retrieval_benchmark_fixtures.py`](../../scripts/benchmarks/build_retrieval_benchmark_fixtures.py) | **Benchmark Fixture Builder**: Compiles reproducible scenario fixtures for offline testing. | `python scripts/benchmarks/build_retrieval_benchmark_fixtures.py` | Generates candidate and scenario JSONL pools. |
| [`scripts/validation/validate_retrieval_benchmark.py`](../../scripts/validation/validate_retrieval_benchmark.py) | **Benchmark Schema Validator**: Validates integrity, schema, and formatting of frozen benchmark files. | `python scripts/validation/validate_retrieval_benchmark.py` | **Directly imported** by `tests/retrieval_benchmark/test_benchmark_schema.py`. |
| [`scripts/benchmarks/benchmark_retrieval_backends.py`](../../scripts/benchmarks/benchmark_retrieval_backends.py) | **Retrieval Backend Benchmark**: Compares latency and throughput across acquisition adapters. | `python scripts/benchmarks/benchmark_retrieval_backends.py` | Evaluates native vs external scrapers. |
| [`scripts/benchmarks/load_test.py`](../../scripts/benchmarks/load_test.py) | **High-Concurrency Load Testing**: Asynchronous load test benchmark for FastAPI endpoints. | `python scripts/benchmarks/load_test.py` | Referenced in `docs/testing/CI_COVERAGE_MATRIX.md`. |

---

### Category 4: Evaluation & ML Baselines (`evaluation/`)

Scripts that compute scientific accuracy, train/evaluate learned rerankers, and perform ablation experiments.

| Script File | Primary Purpose | Verified Execution Command | Key Dependencies & Consumers |
| :--- | :--- | :--- | :--- |
| [`scripts/evaluation/evaluate_dataset.py`](../../scripts/evaluation/evaluate_dataset.py) | **Scientific Benchmark CLI**: Authoritative CLI for WELFake classical ML baseline (88.50%) and Learned Evidence Reranker. *(Root wrapper preserved at `scripts/evaluate_dataset.py`)* | `python scripts/evaluation/evaluate_dataset.py --mode all_offline --seed 42` | Reads `backend/data/WELFake_Dataset.xlsx`. Extensively cited in `README.md`, `docs/EVALUATION.md`, `docs/TESTING.md`. |
| [`scripts/evaluation/evaluate_all_agents.py`](../../scripts/evaluation/evaluate_all_agents.py) | **4-Agent Quality Evaluation**: Comprehensive quality scoring across all four agents. | `python scripts/evaluation/evaluate_all_agents.py` | **Directly imported** by `tests/integration/test_agent_quality_evaluation.py`. |
| [`scripts/evaluation/evaluate_source_planner_modes.py`](../../scripts/evaluation/evaluate_source_planner_modes.py) | **Source Planner A/B Evaluation**: Evaluates deterministic heuristic planning versus optional LLM planner. | `python scripts/evaluation/evaluate_source_planner_modes.py` | Used in Phase 6.9.1 source planner evaluation. |
| [`scripts/evaluation/run_live_retrieval_quality_evaluation.py`](../../scripts/evaluation/run_live_retrieval_quality_evaluation.py) | **Live Retrieval Evaluation Harness**: Automated retrieval quality scoring on live web targets. | `python scripts/evaluation/run_live_retrieval_quality_evaluation.py` | Referenced in ADR 0005. |
| [`scripts/evaluation/run_retrieval_ablation.py`](../../scripts/evaluation/run_retrieval_ablation.py) | **Retrieval Feature Ablation**: Measures ranking impact when stripping entity, temporal, or TF-IDF signals. | `python scripts/evaluation/run_retrieval_ablation.py` | Referenced in `docs/EVALUATION.md`. |
| [`scripts/evaluation/reproduce_retrieval_failures.py`](../../scripts/evaluation/reproduce_retrieval_failures.py) | **Retrieval Failure Reproduction**: Replays known failure cases to verify bug fixes. | `python scripts/evaluation/reproduce_retrieval_failures.py` | Forensic failure analysis tool. |

---

### Category 5: Diagnostics & Live Health Probes (`diagnostics/`)

Scripts that probe API keys, server endpoints, and live agent execution.

| Script File | Primary Purpose | Verified Execution Command | Key Dependencies & Consumers |
| :--- | :--- | :--- | :--- |
| [`scripts/diagnostics/diagnose_keys.py`](../../scripts/diagnostics/diagnose_keys.py) | **Offline key presence**: No connectivity, provider generation or database requests; never prints values. | `python scripts/diagnostics/diagnose_keys.py` | Reads environment settings; presence is not validity. |
| [`scripts/diagnostics/verify_all_agents.py`](../../scripts/diagnostics/verify_all_agents.py) | **Multi-Agent CLI Verification**: Command-line verification of Scout, Trending, BrandShield, and Personal Watch. | `python scripts/diagnostics/verify_all_agents.py` | Direct agent invocation. |
| [`scripts/diagnostics/verify_live_after_fix.py`](../../scripts/diagnostics/verify_live_after_fix.py) | **Post-Fix Live QA**: Quick verification script run after acquisition fixes. | `python scripts/diagnostics/verify_live_after_fix.py` | Bounded live probe. |
| [`scripts/diagnostics/verify_live_scan.py`](../../scripts/diagnostics/verify_live_scan.py) | **Live Scan Verification**: Quick diagnostic tool for single-agent scan verification. | `python scripts/diagnostics/verify_live_scan.py` | Diagnostic utility. |
| [`scripts/diagnostics/test_agents_multi_cycle.py`](../../scripts/diagnostics/test_agents_multi_cycle.py) | **Multi-Cycle Agent Verification**: Multi-iteration loop testing agent resilience. | `python scripts/diagnostics/test_agents_multi_cycle.py` | Referenced in `docs/audit/TESTING_BASELINE.md`. |
| [`scripts/diagnostics/test_all_agents_live.py`](../../scripts/diagnostics/test_all_agents_live.py) | **Live 5-Agent Diagnostic**: Probes live execution across agents. | `python scripts/diagnostics/test_all_agents_live.py` | Referenced in `docs/audit/TESTING_BASELINE.md`. |
| [`scripts/diagnostics/test_all_endpoints.py`](../../scripts/diagnostics/test_all_endpoints.py) | **Endpoint & DB Verification**: Probes FastAPI endpoints and Supabase connectivity. | `python scripts/diagnostics/test_all_endpoints.py` | Referenced in `docs/audit/TESTING_BASELINE.md`. |
| [`scripts/diagnostics/test_api_docs_and_schema.py`](../../scripts/diagnostics/test_api_docs_and_schema.py) | **OpenAPI Schema Verification**: Verifies FastAPI `/openapi.json` contract. | `python scripts/diagnostics/test_api_docs_and_schema.py` | Referenced in `docs/audit/TESTING_BASELINE.md`. |
| [`scripts/diagnostics/test_fastapi_endpoints.py`](../../scripts/diagnostics/test_fastapi_endpoints.py) | **FastAPI Route Harness**: Diagnostic test suite for REST routes. | `python scripts/diagnostics/test_fastapi_endpoints.py` | Diagnostic runner. |

---

### Category 6: Development Tooling (`development/`)

Developer utility scripts.

| Script File | Primary Purpose | Verified Execution Command | Key Dependencies & Consumers |
| :--- | :--- | :--- | :--- |
| [`scripts/development/extract_mandate.py`](../../scripts/development/extract_mandate.py) | **Mandate Extractor**: Helper utility for extracting specification blocks. | `python scripts/development/extract_mandate.py` | Developer utility. |
| [`scripts/development/make_audit_readme.py`](../../scripts/development/make_audit_readme.py) | **Visual Audit Generator**: Compiles `docs/visual-audit/README.md` from screenshot records. | `python scripts/development/make_audit_readme.py` | Generates visual audit index. |


