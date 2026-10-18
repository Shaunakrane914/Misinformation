# AI Layer Model Migration & Key Prefix Alignment — 2026-10-18

## Scope and Context
User requested verification and resolution of AI layer generation failures where:
1. `gemini-2.5-flash-lite` failed with HTTP 404 (endpoint removed/deprecated by Google).
2. `gemini-3.1-flash-lite` timed out against the strict 2.0s advisory deadline (latency was 4.96s).
3. The root provider's `AIzaSy` prefix filter rejected modern Google AI Studio keys (`AQ.Ab8...`).

Worktree: `.scratch/phase9-remediation-20261016` (branch `feat/continuous-source-intelligence-20261017`) and root workspace (`feat/phase8-real-acquisition-proof`).

## Code Changes & Decisions

1. **Advisory Model Update (`gemini-3.5-flash-lite`):**
   - [`backend/infrastructure/llm/advisory_policy.py`](file:///c:/Users/Shaunak%20Rane/Desktop/Projects/Misinformation/.scratch/phase9-remediation-20261016/backend/infrastructure/llm/advisory_policy.py): Updated `MODEL` from discontinued `gemini-2.5-flash-lite` to Google's recommended upgrade `gemini-3.5-flash-lite`.
   - [`backend/core/settings.py`](file:///c:/Users/Shaunak%20Rane/Desktop/Projects/Misinformation/.scratch/phase9-remediation-20261016/backend/core/settings.py): Updated `llm_advisory_model` default to `gemini-3.5-flash-lite`. Replaced deprecated `gemini-2.5-*` models in `gemini_models` with `gemini-3.5-flash` and `gemini-3.5-flash-lite`.
   - [`frontend/netlify/functions/gemini.js`](file:///c:/Users/Shaunak%20Rane/Desktop/Projects/Misinformation/.scratch/phase9-remediation-20261016/frontend/netlify/functions/gemini.js): Updated serverless function candidate list to `['gemini-3.5-flash-lite', 'gemini-3.5-flash', 'gemini-flash-latest']`.

2. **Google AI Studio Key Prefix Normalization:**
   - [`backend/infrastructure/llm/providers/gemini.py`](file:///c:/Users/Shaunak%20Rane/Desktop/Projects/Misinformation/backend/infrastructure/llm/providers/gemini.py): Updated API key prefix filter to `k.startswith(("AIzaSy", "AQ."))` supporting both legacy Google Cloud keys and modern Google AI Studio key formats.

3. **Regression Tests Updated:**
   - [`tests/unit/test_ai_advisory_cost_controls.py`](file:///c:/Users/Shaunak%20Rane/Desktop/Projects/Misinformation/.scratch/phase9-remediation-20261016/tests/unit/test_ai_advisory_cost_controls.py): Updated assertion to expect `gemini-3.5-flash-lite`.
   - [`tests/unit/test_llm_gateway.py`](file:///c:/Users/Shaunak%20Rane/Desktop/Projects/Misinformation/.scratch/phase9-remediation-20261016/tests/unit/test_llm_gateway.py): Updated mocked URL target to `gemini-3.5-flash-lite:generateContent`.

## Empirical Verification & Validation Commands

All commands executed with clean exit 0:

- **Diagnostic Model Lookup:**
  `python scripts/diagnostics/check_ai_advisory_runtime.py --allow-live --env-file ...` -> HTTP 200, `model: "gemini-3.5-flash-lite"`, `model_listed: true`.
- **Live Provider End-to-End Inference:**
  `CentralizedLLMGateway.generate_text()` -> HTTP 200, latency 972.89 ms, returned exact expected output.
- **Fast Offline Test Suite:**
  `python -m pytest tests/unit tests/chaos tests/security -q` -> **1,194 passed** in 24.33s.
- **Critical Flake8 Syntax:**
  `flake8 backend tests scripts --count --select=E9,F63,F7,F82` -> 0 findings.
- **Release Smoke Validation:**
  `python scripts/validate_release_candidate_smoke.py` -> `OFFLINE_SMOKE_PASS`.
- **Rollback Reader Compatibility:**
  `python scripts/validate_rollback_compatibility.py` -> `OFFLINE_PERSISTENCE_PASS`.
- **Node Frontend Contracts:**
  All 7 frontend suites passed (including 8/8 operation health & 6/6 Phase 8E modules).
- **Frozen Benchmark Proof:**
  `python scripts/validation/verify_frozen_benchmarks.py` -> Content hashes verified unchanged.

## Git Status
Changes are made cleanly in working copies (uncommitted). No secrets, credentials, or private keys were logged or committed.
