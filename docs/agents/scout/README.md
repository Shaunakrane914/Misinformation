# AGENT 1: SCOUT — TRADING & NEWS INTELLIGENCE SPECIFICATION

**Agent:** Agent 1 — SCOUT  
**System:** Aegis Protocol  
**Implementation Package:** [`backend/services/agent_reach/scout/`](file:///backend/services/agent_reach/scout/)  
**Agent Class:** [`ScoutAgent`](file:///backend/agents/scout_agent.py)

---

## 1. Architectural Mission & Identity

Scout is **Agent 1** in the Aegis Protocol: the **trading and news intelligence agent**.

Scout is **NOT** a generic scraper, not a search wrapper, and not a claim verifier. Scout's purpose is:
```text
detect potentially important market/news events
        ↓
discover relevant information
        ↓
collect the strongest available sources
        ↓
extract structured facts
        ↓
cross-check / corroborate
        ↓
distinguish confirmed information from rumor
        ↓
assess market relevance
        ↓
produce structured trading/news intelligence
```

Underneath Scout operates the proprietary **Scout Source Engine** (`ScoutSourceEngine`), an empirical, zero-auth acquisition and extraction engine built strictly on the Aegis 348-case transport audit and 200-case semantic benchmark.

---

## 2. Scout Documentation Suite

This directory contains the complete specifications, data contracts, failure models, and empirical benchmark reports for Agent 1:

| Document | Description |
|---|---|
| [**SCOUT_SOURCE_ENGINE_DESIGN.md**](file:///docs/agents/scout/SCOUT_SOURCE_ENGINE_DESIGN.md) | Complete 7-stage architectural design specification of `ScoutSourceEngine`. |
| [**SCOUT_SOURCE_ENGINE_AUDIT.md**](file:///docs/agents/scout/SCOUT_SOURCE_ENGINE_AUDIT.md) | Initial Phase 1 audit of the codebase, duplicate scraper cleanup, and architecture inventory. |
| [**SCOUT_ARCHITECTURE_AUDIT.md**](file:///docs/agents/scout/SCOUT_ARCHITECTURE_AUDIT.md) | Deep structural analysis of Scout within the Aegis multi-agent pipeline. |
| [**SCOUT_SOURCE_CAPABILITY_MATRIX.md**](file:///docs/agents/scout/SCOUT_SOURCE_CAPABILITY_MATRIX.md) | Empirical zero-auth capability matrix covering 15+ platforms and fallback rules. |
| [**SCOUT_DATA_CONTRACT.md**](file:///docs/agents/scout/SCOUT_DATA_CONTRACT.md) | Integration contract between Scout and downstream Aegis agent consumers. |
| [**SCOUT_DATA_MODEL.md**](file:///docs/agents/scout/SCOUT_DATA_MODEL.md) | Comprehensive data model definitions (`ScoutResult`, `FinancialFact`, `CorporateEvent`, `StoryCluster`). |
| [**SCOUT_EXTRACTION_SPEC.md**](file:///docs/agents/scout/SCOUT_EXTRACTION_SPEC.md) | Technical specification for JSON-LD, microdata, multicurrency numbers, and temporal tags. |
| [**SCOUT_EVENT_MODEL.md**](file:///docs/agents/scout/SCOUT_EVENT_MODEL.md) | 13-category corporate event taxonomy, rumor-vs-fact states, and contradiction rules. |
| [**SCOUT_FAILURE_MODEL.md**](file:///docs/agents/scout/SCOUT_FAILURE_MODEL.md) | Taxonomy of error codes (`ScoutFailureCode`) and transparent fallback disclosures. |
| [**SCOUT_SOURCE_POLICY.md**](file:///docs/agents/scout/SCOUT_SOURCE_POLICY.md) | Operational guidelines for zero-auth scraping, token-bucket pacing, and caching. |
| [**SCOUT_BEFORE_AFTER_BENCHMARK.md**](file:///docs/agents/scout/SCOUT_BEFORE_AFTER_BENCHMARK.md) | Comparative evaluation of naive Top-1 vs. the audited Top-5 semantic ranking engine. |
| [**SCOUT_TEST_REPORT.md**](file:///docs/agents/scout/SCOUT_TEST_REPORT.md) | Formal test execution log proving 100% test pass rate across 23 unit & trap tests. |

---

## 3. Core Capabilities Summary

### 3.1 Hard Semantic Rejection Gates
- **`PlatformScopeGate`**: Prevents cross-community false positives (e.g., rejecting `r/privacy` when `r/investing` is specified).
- **`URLStructureGate`**: Enforces specific content URLs (`/comments/<id>` for Reddit, `/status/<id>` for X).
- **`AntiTokenCheatGate`**: Evaluates contextual co-occurrence, surname boundaries, and entity disambiguation to prevent naive token cheats (e.g. Satya, Sam, Jensen, CHIPS Act).
- **`DomainIntegrityGate`**: Rejects video or corporate domains when social community discussion is requested.

### 3.2 Specialist Zero-Auth Adapters
- **Reddit**: Arctic Shift public mirror (`photon-reddit.com/api/posts/ids`).
- **X / Twitter**: FxTwitter public mirror (`api.fxtwitter.com`).
- **YouTube**: Direct video metadata and transcript acquisition via `yt-dlp`.
- **Primary Filings**: SEC EDGAR API and investor relations endpoints.
- **GitHub**: Native REST API control standard.
- **General Web**: Adaptive Scrapling HTTP + Jina Reader + Playwright rescue.

### 3.3 Financial Fact & Corporate Event Extraction
- Multicurrency extraction (`$`, `₹`, `€`, `£`, `bps`, `EPS`) with metric normalization (`revenue`, `ebitda`, `capex`, `guidance`).
- Corporate event classification across 13 types (`GUIDANCE_CHANGE`, `EARNINGS`, `M_AND_A`, `REGULATORY_ACTION`, etc.).
- Temporal disambiguation maintaining separation between `event_at`, `published_at`, and `retrieved_at`.

### 3.4 Corroboration & Non-Destructive Contradiction
- Groups syndicated wire stories (Reuters, AP, Bloomberg, PR Newswire) into single story clusters to avoid inflated independent source counts.
- Flags conflicting numbers without destructive mathematical averaging, setting epistemic status to `CONTRADICTED` while preserving both raw observations.

---

## 4. Verification & Testing

To run the full Scout test suite:
```bash
python -m pytest tests/unit/test_scout_source_engine.py -v
```
All **23/23 tests pass (100%)**, including formal rejection of all 10 canonical adversarial audit traps.
