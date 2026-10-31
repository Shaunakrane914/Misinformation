# Aegis Protocol — Hybrid Entity Resolution & Adaptive Source Discovery Engine Handoff

**Date:** 2026-10-31  
**Worktree:** `.scratch/integration-reconciliation-20261031`  
**Branch:** `fix/sec-issuer-identity-and-reconciliation`  
**Base Commit:** `ced963e` (`origin/main`)  
**Status:** Verification & Architecture Integration Complete (Uncommitted, Unmerged)

---

## 1. Executive Summary & Objective

In accordance with user directives:
1. **Evaluated Provider Credentials:**
   - **Groq API Key:** Authenticated and confirmed operational with model `openai/gpt-oss-20b`.
   - **OpenAI API Key:** Authenticated but rejected upstream with `HTTP 429 credit_balance_exhausted` (quota exhausted as predicted).
2. **Provider Failover Architecture:** Integrated Groq and OpenAI into `CentralizedLLMGateway` (`backend/infrastructure/llm/gateway.py`) as a **sequential fallback chain** (Gemini -> Groq -> OpenAI -> Mock/Fail), strictly avoiding side-by-side or parallel calls.
3. **Consolidated Discovery System:** Consolidated existing discovery components:
   - `SourcePlanningEngine.plan()` and `replan()` (`backend/services/agent_reach/source_planner.py`)
   - `search_advice.py` (`backend/services/research/search_advice.py`)
   - `CentralizedLLMGateway` (`backend/infrastructure/llm/gateway.py`)
   - Advisory policy and budget controls (`advisory_policy.py`, `evidence_advisor.py`)
   - `IssuerIdentityResolver` (`backend/services/research/issuer_identity.py`)
4. **Architectural Separation of the Two Core Failure Modes:**
   - **Failure Mode 1 (Target Unknown):** Target missing from Layer 1 (Catalog) & Layer 2 (Registry) -> AI suggests candidate entities -> **Verification Gate** validates candidate against authoritative registry before acquisition. Model proposals are NEVER written to static catalogs.
   - **Failure Mode 2 (Source Denied or Empty):** Target is known and verified, but primary endpoint returns HTTP 401/403/429 or empty observation -> AI proposes alternative queries/channels for the **SAME entity** -> Native acquisition engine fetches documents -> Telemetry honestly logs primary denial alongside fallback.

---

## 2. Key Components Created & Updated

### A. Sequential Provider Fallback Chain
- [`backend/infrastructure/llm/providers/groq.py`](../../backend/infrastructure/llm/providers/groq.py):
  Implements `LLMProvider` protocol using Groq OpenAI-compatible endpoint with model `openai/gpt-oss-20b`, bounded timeout (max 5.0s), JSON mode support, and token usage accounting.
- [`backend/infrastructure/llm/providers/openai.py`](../../backend/infrastructure/llm/providers/openai.py):
  Implements `LLMProvider` protocol using OpenAI endpoint with model `gpt-4o-mini`, gracefully handling 429 quota exhaustion without crashing downstream pipelines.
- [`backend/core/settings.py`](../../backend/core/settings.py):
  Added `groq_api_key`, `groq_model`, `openai_api_key`, `openai_model`, and helper properties `has_groq` and `has_openai`.
- [`backend/infrastructure/llm/gateway.py`](../../backend/infrastructure/llm/gateway.py):
  Updated `DefaultLLMGateway` to execute sequential failover: `Gemini -> Groq -> OpenAI -> Mock/Fail`. Preserved fail-closed production rules (mock mode strictly forbidden in production).

### B. Consolidated Discovery & Verification Engine
- [`backend/services/research/hybrid_discovery.py`](../../backend/services/research/hybrid_discovery.py):
  Shared coordinator implementing the 3-Layer architecture:
  - `VerificationGate`: Deterministically validates AI-proposed entities against official registry indexes (`IssuerIdentityResolver` for Scout, safe domain checks for BrandShield, length/injection checks for Trending, PII checks for Personal Watch). Rejects hallucinations.
  - `HybridDiscoveryCoordinator.resolve_entity()`: Coordinates Layer 1 (static catalog), Layer 2 (authoritative dynamic registry), and Layer 3 (AI proposal + Verification Gate) for Failure Mode 1.
  - `HybridDiscoveryCoordinator.adapt_sources_on_failure()`: Coordinates secondary permitted channels when primary endpoints fail for Failure Mode 2.
- [`backend/services/agent_reach/source_planner.py`](../../backend/services/agent_reach/source_planner.py):
  Enhanced `SourcePlanningEngine.replan()` to detect primary denials/empty observations and invoke `HybridDiscoveryCoordinator.adapt_sources_on_failure()` while logging fallback warnings.
- [`backend/agents/scout/financial.py`](../../backend/agents/scout/financial.py):
  Wired `resolve_company_identity()` to `hybrid_discovery_coordinator.resolve_entity()`, enabling dynamic and heuristic resolution of previously unknown filers with strict SEC registry verification.

---

## 3. Empirical Verification & Test Results

All commands executed in worktree `.scratch/integration-reconciliation-20261031`:

```bash
# 1. Focused Unit & Fallback Suites
pytest tests/unit/test_dynamic_issuer_resolution_and_isolation.py \
       tests/unit/test_sec_issuer_identity_verification.py \
       tests/unit/test_scout_primary_intelligence.py \
       tests/unit/test_scout_disclosure_prose.py \
       tests/unit/test_four_agent_coverage_preservation.py \
       tests/unit/test_llm_gateway.py \
       tests/unit/test_llm_provider_fallback_chain.py \
       tests/unit/test_hybrid_entity_resolution_and_discovery.py \
       tests/unit/test_source_planning_engine.py -q
# Result: 112 passed in 17.70s

# 2. Chaos and Security Suites
pytest tests/chaos tests/security -q
# Result: 100 passed in 4.73s

# 3. Flake8 Fatal Syntax & Undefined Symbol Check
flake8 backend tests scripts --count --select=E9,F63,F7,F82 --show-source --statistics
# Result: 0 errors

# 4. Release Candidate Smoke Validation
python scripts/validate_release_candidate_smoke.py
# Result: OFFLINE_SMOKE_PASS

# 5. Rollback Reader Compatibility Validation
python scripts/validate_rollback_compatibility.py
# Result: OFFLINE_PERSISTENCE_PASS
```

---

## 4. Invariants & Safety Guarantees Maintained

1. **Model Suggestions Never Enter Static Catalogs:** Verified by `test_failure_mode_1_never_mutates_static_catalog`. `issuer_identity_catalog.json` remains immutable at runtime.
2. **Deterministic Registry Gating:** Candidate entities proposed by AI must exist in the SEC EDGAR index or official registers; hallucinated candidates are discarded (`test_failure_mode_1_hallucinated_candidate_rejected_by_gate`).
3. **SSRF & Dangerous URL Defense:** All URLs in source hints pass through `is_safe_url()`; metadata IP addresses and private loopbacks are blocked.
4. **Target Entity Immutability in Source Failures:** When primary sources return 403 or empty, alternative queries are generated for the exact same verified entity without mutating its legal name or CIK.
5. **No Secrets Logged:** API keys are loaded via environment variables and settings without being printed to logs, transcripts, or committed files.

---

## 5. Status & Next Actions

- All changes reside cleanly in the isolated worktree `.scratch/integration-reconciliation-20261031` on branch `fix/sec-issuer-identity-and-reconciliation`.
- Root workspace (`feat/phase8-real-acquisition-proof`) remains untouched.
- **Zero commits, merges, pushes, or deployments have been made**, adhering to explicit safety guidelines.
- Ready for owner review and merge instructions.

