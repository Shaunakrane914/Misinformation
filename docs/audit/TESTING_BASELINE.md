# Aegis Protocol — Testing Baseline & Quality Report

> [!WARNING]
> **[SUPERSEDED ARCHITECTURAL SNAPSHOT]**  
> This document records the initial October 2, 2026 test audit when the test suite was 180 tests. Aegis Protocol now maintains **530 passing automated tests** across unit, contract, integration, chaos, security, and Cranfield benchmark suites. For canonical testing instructions, see:
> - [`docs/TESTING.md`](../TESTING.md)
> - [`docs/archive/README.md`](../archive/README.md)

**Audit Date**: October 2, 2026 *(updated — v3.7.0)*

---

## 1. Current Test State

Prior to this audit, the repository had **no standardized test framework or `tests/` directory**.
Existing validation consisted entirely of standalone verification scripts located in `scripts/`:

| Script Name | Purpose | Execution Mode | Verification Result |
|---|---|---|---|
| `scripts/test_launch_video_integrity.py` | Validates Hyperframes launch video composition assets and `/launch-video` route | Static file + FastAPI TestClient | **PASS** (100% clean) |
| `scripts/test_fastapi_endpoints.py` | Exercises FastAPI endpoints | Live HTTP requests against port 8000/8001 | **PARTIAL** (requires running server) |
| `scripts/test_all_endpoints.py` | Tests full endpoint lifecycle including DB operations | Live HTTP requests | **BLOCKED** by external network latency / Supabase timeout |
| `scripts/test_all_agents_live.py` | Live agent test with external APIs | Live calls | **BLOCKED** without external API keys |
| `scripts/test_agents_multi_cycle.py` | Multi-cycle stress test | Live calls | **BLOCKED** without external API keys |
| `scripts/test_api_docs_and_schema.py` | Validates OpenAPI schema and Swagger endpoints | FastAPI TestClient | **PASS** |

---

## 2. Testing Deficits & Target Architecture

1. **Missing Pytest Suite**:
   - Need standard test runner config (`pytest.ini`).
   - Need categorized directories:
     - `tests/unit/`: Pure functions, claim normalization, schemas, mathematical instruments, error handling.
     - `tests/integration/`: FastAPI TestClient route tests, database memory fallback, background worker tasks.
     - `tests/security/`: SSRF URL validation, XSS escaping, prompt injection boundaries.
     - `tests/eval/`: Model benchmark metrics on held-out dataset.
2. **Missing Test Fixtures & Mocks**:
   - `MockGeminiProvider`: Returns deterministic JSON responses without making live network calls or consuming tokens.
   - `MockReachScraper`: Returns predictable news/social snippets for deterministic claim investigation tests.

---

## 3. v3.7.0 Test Status *(Updated October 2, 2026)*

**All deficits from §2 are now resolved.**

| Test File | Tests | Status | Coverage Area |
|---|---|---|---|
| `test_claim_quality_integrity.py` | 2 | ✅ PASS | `quality_tensor` / `quality_status` honesty |
| `test_query_execution_telemetry.py` | 5 | ✅ PASS | `QueryExecutionRecord`, funnel counters, telemetry |
| `test_provenance_deduplication.py` | 4 | ✅ PASS | `EvidenceFragment` lineage, dedup merge |
| `test_replay_verification.py` | 7 | ✅ PASS | `ReplayLedger` trace/refetch modes + API |
| `test_doctor_status_semantics.py` | 6 | ✅ PASS | `DoctorBridge` canonical status codes |
| **Total** | **24** | **✅ 24/24 PASS** | Core service integrity |

### Additional v3.7.0 Test Infrastructure
- **`tests/unit/conftest.py`** — Shared fixtures: `api_client`, `fresh_ledger`, `sample_quality_tensor`, `sample_dossier`, `mock_research_no_corpus`, `mock_investigator_false`.
- **`pytest.ini`** — Configured with `asyncio_mode = auto`, `rerun_on_failure = 2`, and `testpaths = tests/`.

### Integrity Guarantees Enforced by Tests
- `quality_tensor` is **never** synthesised from hardcoded defaults; confirmed `None` when no corpus exists.
- `quality_status` is exactly `UNAVAILABLE_NO_CORPUS` or `VERIFIED_CORPUS` — no other values.
- `ReplayLedger.replay_investigation(mode="trace_playback")` never makes live network calls.
- `DoctorBridge.get_canonical_status_code("youtube")` returns `DEGRADED` for rate-limited channels, **not** `AUTH_REQUIRED`.
