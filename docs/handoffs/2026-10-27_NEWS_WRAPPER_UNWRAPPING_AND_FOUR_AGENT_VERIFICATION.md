# News Wrapper Unwrapping, Two-Layer Temporal Guard & Four-Agent Verification — 2026-10-27

## Scope & Objective
1. **Four-Agent Smoke & Matrix Verification**: Validate all 4 Aegis intelligence agents (Scout, BrandShield, Trending, Personal Watch) with live smoke tests and offline unit/functional regression matrices.
2. **Google News Wrapper URL Resolution & Direct Publisher Prioritization**: Resolve opaque Google News redirect wrapper tokens (`news.google.com/rss/articles/CBMi...`) that cannot be fetched by deep readers, ensuring content-poor or niche queries (e.g., "battery recycling") obtain real publisher URLs.
3. **Two-Layer Temporal Guard Labeling**: Transition the Trending gate from hard-rejection to a two-layer model (fresh-first with NEW tag, and top-up to page minimum using OLD tag) so pages are never empty while freshness is honestly surfaced.
4. **Golden Pipeline Invariance**: Ensure all 12 scenarios in `test_research_pipeline_golden.py` preserve exact legacy hash invariance without regressions.

---

## Changes Implemented

### 1. Direct Publisher Extraction & News Channel Prioritization
- **`backend/infrastructure/acquisition/routing/standard_handlers.py`**:
  - For `channel == "news"`, prioritized Bing News RSS (`https://www.bing.com/news/search?q={query}&format=rss`) which returns publisher URLs wrapped in an immediate query parameter (`apiclick.aspx?...&url=...`).
  - Falls back to Google News RSS only if Bing returns zero entries.
- **`backend/services/agent_reach/native/normalizer.py`**:
  - In `normalize_rss_entries`, added regex-based parameter unquoting for Bing News `apiclick.aspx?...&url=...` and Yahoo `/RU=...` wrappers, directly resolving them to target publisher URLs.
  - Extracted `<source url="...">` from RSS entries into `source_url` metadata.
- **`backend/agents/trending/discovery.py`**:
  - Updated emergency news fallback to attempt Bing News RSS with `apiclick.aspx` unquoting first before falling back to Google News RSS.
- **`backend/services/research/deep_reader.py`**:
  - Added URL resolution check for `news.google.com`: checks `item.metadata` for `source_url` or `publisher_url`.
  - Unresolved `news.google.com` wrapper tokens are fast-failed (`PUBLISHER_UNRESOLVED`) rather than fetching the heavy JavaScript client shell (`c-wiz`), preventing read batch timeouts and resource starvation for readable sources.
  - Increased concurrent read worker cap to 12 and `max_chars` ceiling to 25,000.

### 2. Trending Temporal Guard Two-Layer Design
- **`backend/services/research/relevance_gate.py`**:
  - Converted freshness into a label (`temporal_fresh: Optional[bool]`) instead of hard dropping at `evaluate_item()`.
  - Added `_apply_trending_freshness_threshold()`: keeps all fresh items (`NEW`); if count < `TRENDING_MIN_RESULTS` (6), tops up with the most recent older items (`OLD`).
  - Omitted `temporal_fresh` from `RelevanceAssessment.to_dict()` when `None` to preserve legacy serialization and golden master hash invariance for non-trending domains.

### 3. Source Planning & Fixture Determinism
- **`backend/services/agent_reach/source_planner.py`**:
  - Guarded fixture agents (`phase4_fixture`) from adding untracked expansion sources or requesting LLM-suggested plans, preserving deterministic golden test execution.

---

## Verification & Commands Run

| Test / Verification Suite | Scope | Result | Details |
| :--- | :--- | :---: | :--- |
| `scripts/live_agent_smoke_test.py` | All 4 Agents Live | **PASS** | Scout (25.6s), BrandShield (183.2s), Trending (178.5s), Personal Watch (31.0s) |
| `tests/unit/test_functional_agents_matrix.py` | All 4 Agents Matrix | **PASS** | 24 / 24 passed in 0.55s |
| `tests/test_trending_temporal_guard.py` | Temporal Guard 2-Layer | **PASS** | 10 / 10 passed in 0.12s |
| `tests/unit/test_research_pipeline_golden.py` | Golden Master Manifest | **PASS** | 12 / 12 passed in 0.26s (all hashes matched) |
| `tests/unit/test_source_planning_engine.py` | Source Planning Engine | **PASS** | 10 / 10 passed in 0.14s |
| `tests/unit/test_trending_2.py` + workflow | Trending Integration | **PASS** | 14 / 14 passed in 1.52s |
| Fast Test Suite (`tests/unit`, `tests/chaos`, `tests/security`) | Complete Offline Fast Suite | **PASS** | **867 / 867 passed** in 15.32s |
| Syntax & Compilation Lint (`flake8`) | Fatal Errors (E9, F63, F7, F82) | **PASS** | 0 fatal syntax or compilation errors |
| `scripts/validate_release_candidate_smoke.py` | Release Smoke Gate | **PASS** | OFFLINE_SMOKE_PASS across all gates |
| `scripts/validate_rollback_compatibility.py` | Archive & Rollback Integrity | **EXPECTED** | Reports 55 historical malformed dossiers honestly (`HISTORICAL_ARCHIVE_FAIL`) without data mutation |
| `tests/frontend/test_*.js` | Frontend Health & Regressions | **PASS** | 8/8 operation health passed, security regressions passed |

---

## Operational Status & Deployment
- All test suites, security gates, and golden hash checks pass cleanly.
- Ready for deployment trigger.
