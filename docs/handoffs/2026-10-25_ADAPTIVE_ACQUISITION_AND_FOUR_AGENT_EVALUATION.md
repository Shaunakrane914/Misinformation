# Adaptive Acquisition & Four-Agent Evaluation Handoff — 2026-10-25

## 1. Summary of Completed Work

This milestone completes the interleaved acquisition architecture in `.scratch/phase9-remediation-20261016` (branch `release/specialist-task-20261024`):
1. **Adaptive Interleaved Controller Verified**: Implemented `InterleavedController` in `backend/services/research/adaptive_acquisition.py` with immediate capture inspection, zero-yield publisher deferral, substantive task-relevant discovery pausing, and 35/60/25 HTTP allocation within the 120-admission ceiling.
2. **GDELT DOC API Integrated**: Created `backend/infrastructure/acquisition/adapters/news/gdelt.py` (`GdeltDocAdapter`) supporting topic searches, exact phrase quotes, 48h timespan filtering, ISO 8601 UTC timestamp parsing, SSRF safe URL filtering, and graceful 429 throttling / timeout handling. Wired into `SourcePlanningEngine` and `expanded_catalog.py`.
3. **Personal Watch Statements & Fact-Checks Enhanced**: Separated public statements/speeches/interviews from identity threats; integrated Google Fact Check Tools API (`claims.search`) with explicit attribution tagging; expanded regional news container selectors (`.artText`, `.article_body`, `.storyContent`) and JSON-LD `NewsArticle` body qualification; refined `OBJECTIVE_TERMS["personal"]` to prevent corporate earnings from falsely matching personal watch.
4. **Scout and BrandShield Intelligence Preserved**: Retained SEC EDGAR priority and investor-relations earnings transcripts for Scout, and official consumer warnings/recalls (OPSS, FTC) and trademark infringement reporting for BrandShield.
5. **Evaluation Conducted**: Completed offline capture replay across all four historical cases (`replay_acquisition_feedback.py`) and executed live evaluations (`run_terminal_agent_quality.py`) with DEEP profile, max 240s timeout, max 24 deep reads, max 120 HTTP admissions, and zero live AI calls.

Detailed report: [Adaptive Acquisition Evaluation 2026-10-25](../testing/ADAPTIVE_ACQUISITION_EVALUATION_2026-10-25.md).

---

## 2. Regression Test Verification

- Fast Suite (`tests/unit`, `tests/chaos`, `tests/security`): **2,212 passed in 63.45s**.
- Fatal Lint Check (`flake8 backend tests scripts`): **0 fatal errors**.
- Focused Component Suites:
  - `tests/unit/test_gdelt_adapter.py`: 5 passed.
  - `tests/unit/test_personal_watch_statements.py`: 4 passed.
  - `tests/security/test_interleaved_http_budget.py`: 13 passed.
  - `tests/unit/test_two_layer_pipeline.py`: 10 passed.
  - `tests/unit/test_recovered_scope_projection.py`: 14 passed.
  - `tests/unit/test_expansion_safety_and_wiring.py`: 29 passed.

---

## 3. Git Status & Commits

- All edits are tracked within `.scratch/phase9-remediation-20261016`.
- Benchmark datasets (`tests/retrieval_benchmark/*`) and historical dossiers (`backend/data/dossiers/*`) remain untouched.
- Ready for commit and push on branch `release/specialist-task-20261024`.
