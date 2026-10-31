# CodeRabbit Review Remediation & Governance Tightening

**Date:** 2026-11-01  
**Branch:** `feat/v2-consolidated-release`  
**Base Commit:** `d02bbe3` (`feat: consolidate PR #4 and isolated integration worktree into clean v2 candidate`)  
**Target Pull Request:** [PR #5](https://github.com/Shaunakrane914/Misinformation/pull/5)  
**Status:** Verification Complete (27/27 unit regressions passing, 12/12 frontend suites passing, smoke validation PASS). Awaiting user approval to commit, push, and monitor CI.

---

## 1. Summary of Changes Across the 6 Priority Tracks

### Track 1: AI-Proposed Issuer Identifier Consistency
- **File:** `backend/services/research/hybrid_discovery.py`
- **Remediation:**
  - AI proposed entities in `verify_candidate_entity` and `_propose_and_verify_scout_entity` must have mutual agreement among all non-empty identifiers (`cik`, `ticker`, `legal_name`).
  - Gated candidate lookup against the authoritative SEC index so each provided identifier must resolve to the identical authoritative CIK.
  - Added company query agreement checks verifying query token overlap or explicit corporate affiliation terms (`SUBSIDIARY`, `PARENT`, `ACQUISITION`, etc.) to reject unrelated entities proposed by LLM suggestions.
- **Tests Added:** `test_scout_verification_rejects_conflicting_identifiers`, `test_scout_verification_rejects_candidate_not_matching_requested_company` in `tests/unit/test_hybrid_entity_resolution_and_discovery.py`.

### Track 2: Consistent Advisory Governance across Gemini, Groq, and OpenAI
- **Files:** `backend/infrastructure/llm/advisory_policy.py`, `gateway.py`, `providers/groq.py`, `providers/openai.py`
- **Remediation:**
  - Introduced `AdvisoryProviderBlocked(AdvisoryPolicyError)` to distinguish temporary provider-level blocks (cooldown from 429, busy lock) from system-level governance violations (exceeded daily budget, single-call-per-investigation invariant).
  - Provider-level blocks raise `AdvisoryProviderBlocked`, which `DefaultLLMGateway` treats as a recoverable failover condition that proceeds down the fallback chain (`Gemini` &rarr; `Groq` &rarr; `OpenAI`).
  - System-level governance violations raise `AdvisoryPolicyError` which immediately fails closed without attempting secondary providers.
  - Enforced uniform advisory limits across secondary providers: 6,000 char prompt limits, `max_attempts=1`, finite timeouts $\le 2.5$s, bounded output tokens (1–250), and provider-specific cooldown on HTTP 429.
- **Tests Added:** `test_gemini_in_cooldown_falls_over_to_groq`, `test_budget_exhaustion_fails_closed_without_secondary_attempts` in `tests/unit/test_llm_provider_fallback_chain.py`.

### Track 3: Frontend Keyword-Derived Catalysts Separated from Verified Findings
- **File:** `frontend/intelligence-transformer.js`
- **Remediation:**
  - Gated `report.catalysts` so that heuristic keyword extractions NEVER overwrite or synthesize `report.catalysts`. Backend-supplied catalysts are preserved as-is.
  - Client-derived heuristics are isolated under `report.client_derived = { heuristic_catalysts: ... }`.
  - Removed fabricated `evidence_ids: [s.publisher]` and source name fallbacks (`'Verified Source'`, `'Wire Network'`) from heuristic catalysts.
  - In `frontend/unified-report-renderer.js`, completely removed loops inserting catalysts into `deckItems`.

### Track 4: Finding-to-Passage Matching and Provenance Honesty
- **File:** `frontend/unified-report-renderer.js`
- **Remediation:**
  - Removed arbitrary modulo index matching (`passages[i % (passages.length || 1)]`) in `renderFindings`. If a finding does not match a passage substring, `relatedPassage` remains `null`.
  - Replaced unsupported claims and verification phrases (`"Verified Disclosure Node"`, `"Current Milestone"`, `"GROUNDED FINDING"`, `"Corroborated across primary filing..."`) with neutral, factual descriptions (`"Publisher unavailable"`, `"Date unknown"`, `"REPORTED FINDING"`, `""`).
  - Renamed `renderVisualAnalytics` metrics heading from `// VERIFIED QUANTITATIVE & REGULATORY INDICATORS` to `// EXTRACTED QUANTITATIVE FIGURES (UNVERIFIED)`.

### Track 5: Truthful Visualizations & Metrics Handling
- **Files:** `frontend/aegis-graphs.js`, `frontend/intelligence-transformer.js`
- **Remediation:**
  - **Channel Dispersion (`computeChannelDispersion`):**
    - Normalized object-shaped evidence (`evidence.primary`, `evidence.independent`, `evidence.community`).
    - Excluded passage duplication from the denominator (`total = evidence.length`).
    - Replaced substring matching with exact hostname parsing (`host === 'x.com' || host.endsWith('.x.com')`), preventing false positives such as `netflix.com` or `fedex.com`.
    - Computed `web_pct` directly as classified web items rather than an unclassified remainder.
  - **Volatility Chart (`renderVolatilityChart`):**
    - Filtered history to finite numeric values before the fewer-than-two check.
    - Derived empirical mean and standard deviation from observations; mapped `mean ± 1.5σ` to chart Y coordinates.
    - Updated band title to `// EMPIRICAL DISPERSION BAND (MEAN ± 1.5σ)`, and omitted the band entirely when variance is zero.
  - **6-Axis Epistemic Tensor Radar (`renderEpistemicRadar`):**
    - Treated null/missing axes as absent (`n/a`), excluding them from score calculations rather than treating them as 0.0.
    - Renamed score label to `Mean Epistemic Score` and plotted vertex nodes for assessed dimensions only.
  - **Hawkes Acceleration (`renderHawkesVelocity`):**
    - Extended empty state guard to reject non-finite $R_0$.
    - Eliminated synthetic `sin()` curve and hardcoded time labels (`T-48h`) when longitudinal arrival timestamps are absent. Rendered honest scalar metric card with $R_0$ and criticality status instead.
  - **Identity Threat Gauge (`renderIdentityThreatGauge`):**
    - Treated null threat vectors as unassessed; clamped assessed vectors to 0–100%.
    - Derived overall status using assessed vectors only (`NOT ASSESSED` if empty).
    - Reworded empty-state text to: `"No assessments recorded; this is not evidence of safety."`

### Track 6: SEC Configuration & Review Findings Evaluation
- **Files:** `backend/infrastructure/acquisition/adapters/authoritative/sec_edgar.py`, `backend/services/research/issuer_identity.py`
- **Remediation:**
  - `sec_edgar.py`: Added static map alias check (`TICKER_CIK_MAP`, `COMPANY_NAME_CIK_MAP`) in `fetch_sec_submissions()` before rejecting unindexed query aliases (e.g., `Google` &rarr; Alphabet Inc CIK `0001652044`).
  - `issuer_identity.py`: Added `_cached_index_loaded` lock memoization to prevent redundant re-reads, and added `is_live: bool = False` to `observe_ticker_index()` to avoid resetting sync failure errors on offline cache loads.
- **Intentionally Rejected Findings:**
  - **Comment 1 (`trending/agent.py:126`):** Already addressed in commit `d02bbe3` via `if not virality: return None`.
  - **Comment 5 (SSRF on Wikidata in `social_resolver.py`):** Comment was on documentation (`docs/handoffs/...`), noting that static public endpoints (`www.wikidata.org`) bypass `is_safe_url()`. Attempting to wrap `www.wikidata.org` in `is_safe_url()` causes DNS resolution failures in offline test environments (`test_phase6_8_social_resolution.py`). Because `_query_wikidata_live` targets a static, hardcoded public API domain with URL-quoted entity queries, dynamic SSRF validation is not required and would violate the offline test reproducibility invariant.

---

## 2. Verification Proof

### Python Regression Suites
```text
pytest tests/unit/test_hybrid_entity_resolution_and_discovery.py tests/unit/test_llm_provider_fallback_chain.py tests/unit/test_sec_issuer_identity_verification.py -q
=> 27 passed in 2.60s

pytest tests/unit/test_phase6_8_social_resolution.py -q
=> 17 passed in 0.24s

flake8 backend tests scripts --count --select=E9,F63,F7,F82 --show-source --statistics
=> 0 errors

python scripts/validate_release_candidate_smoke.py
=> OFFLINE_SMOKE_PASS (All 5 gates pass, all 4 agents pass, zero-evidence guard passes)
```

### Node Frontend Suites
```text
node tests/frontend/test_truthful_graphics_and_intelligence.js
=> ALL TRUTHFUL GRAPHICS AND INTELLIGENCE TESTS PASSED! (6/6 tests)

All 12 frontend test suites in tests/frontend/test_*.js
=> ALL 12/12 PASSED (test_agent_research_client, test_agent_ui_truth, test_claim_ui_truth, test_cloudflare_api_routing, test_desktop_evidence_audit, test_evidence_workbench, test_forensic_explorer_truth, test_operation_health, test_phase8e_frontend_intelligence, test_security_and_health_regressions, test_truthful_graphics_and_intelligence, test_unified_report_renderer)
```

---

## 3. Next Actions
- Commit the focused changes to branch `feat/v2-consolidated-release`.
- Push to `origin feat/v2-consolidated-release` to update PR #5.
- Monitor GitHub Actions CI until all workflow jobs complete green.
