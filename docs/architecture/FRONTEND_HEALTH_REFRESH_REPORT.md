# Aegis Protocol — Frontend Operation Health Freshness Report
**Phase 7.1 Release Candidate Deliverable C**  
*Lead Release Engineer & QA Architect Audit*

---

## 1. Executive Summary

In Phase 7, all four agent interfaces (`scout-agent.html`, `trending-agent.html`, `brandshield-agent.html`, `personal-watch-agent.html`) were standardized on `frontend/operation-health.js` to eliminate hardcoded provider badges and enforce operation-level classification truth.

However, an audit of `frontend/operation-health.js` revealed a critical caching defect:
- `fetchCapabilities()` previously cached a resolved `capabilityPromise` indefinitely.
- The resolved promise lived for the lifetime of the page with **no TTL, no revalidation, no visibility trigger, and no stale degradation**.
- Consequently, if a user left a dashboard open, the UI could display a "Direct content" green badge hours after the underlying provider became rate-limited, authentication-gated, or policy-blocked.

In Phase 7.1, `frontend/operation-health.js` was completely hardened with a bounded TTL cache, concurrent request deduplication, stale state degradation, and controlled visibility revalidation.

---

## 2. Hardened Architecture & Lifecycle

### 2.1 Bounded TTL Cache (`DEFAULT_CONFIG`)
```javascript
const DEFAULT_CONFIG = {
  ttlMs: 45000,            // 45 seconds cache validity (bounded between 30–60s)
  staleThresholdMs: 90000, // 90 seconds: observations transition to 'stale'
  timeoutMs: 3500          // 3.5 seconds fetch timeout via AbortController
};
```
- **Cache Hit (< 45s)**: Returns cached data immediately without issuing redundant HTTP requests.
- **Cache Expiry (45s – 90s)**: Automatically issues a fresh fetch to `/api/agent-reach/capabilities`.
- **Stale Boundary (> 90s)**: If revalidation fails or has not succeeded within 90 seconds, operations degrade to `'stale'`. A previously healthy provider **never remains green indefinitely**.

### 2.2 Deduplication of Concurrent In-Flight Requests
When multiple dashboard pills or components request capabilities simultaneously (e.g. at page load), only **one** network request is initiated. All callers share `inFlightPromise`.

### 2.3 Explicit Invalidation & Revalidation
- `fetchCapabilities({ force: true })` bypasses the cache and forces a live network probe.
- `invalidateCapabilities()` evicts cached data and clears in-flight state.
- `getCacheState()` exposes `{ hasData, lastFetchedAt, ageMs, isExpired, isStale, inFlight, lastFetchError }`.

### 2.4 Controlled Page Visibility Revalidation
- Implemented a `visibilitychange` listener on `document`.
- When `document.visibilityState === 'visible'`, if cached data is older than `ttlMs`, a bounded background revalidation is triggered and subscribed UI pills are re-rendered.
- Inactive / hidden background tabs issue **zero polling requests**, preventing runaway polling or mobile battery drain.

### 2.5 Truthful State Taxonomy & Rendering
| State | Label | Visual Class | Condition |
|---|---|---|---|
| `healthy` | Direct content | `healthy` (green) | Fresh (< 45s), `runtime_health === 'HEALTHY'`, `last_outcome === 'DIRECT_CONTENT'` |
| `limited` | Limited / partial | `degraded` (amber) | Direct metadata, syndicated summary, or search-index discovery |
| `degraded` | Temporarily degraded | `degraded` (amber) | 429 rate limit cooldown, transient transport error |
| `auth_required` | Authentication required | `degraded` (amber) | Missing optional session cookie or API token |
| `blocked` | Policy blocked | `unavailable` (red/dim) | Autonomous access forbidden by platform policy |
| `stale` | Stale observation | `degraded` / `unverified` | Data age > 90s and unverified; **never green** |
| `unavailable` | Not implemented | `unavailable` (red/dim) | No handler implemented |
| `unverified` | Not yet verified | `unverified` (neutral) | Fresh process boot before empirical observation |

---

## 3. Automated Verification Evidence

The behavior is verified across two test layers:

### A. Dedicated Node.js Test Suite (`tests/frontend/test_operation_health.js`)
Executed via pure Node.js stdlib with zero external npm dependencies:
```
--- TEST 1: Initial Successful Capability Fetch ---
✓ Initial successful fetch verified
--- TEST 2: Cache Hit Within TTL ---
✓ Cache hit within TTL verified
--- TEST 3: Fetch After TTL Expiry ---
✓ Fetch after TTL expiry verified
--- TEST 4: Concurrent Requests Share In-Flight Fetch (Deduplication) ---
✓ Request deduplication verified
--- TEST 5: Healthy Operation Becomes Blocked ---
✓ Blocked operation classification verified
--- TEST 6: Healthy Operation Becomes Rate-Limited ---
✓ Rate-limited operation classification verified
--- TEST 7: Capability API Becomes Unavailable (No Indefinite Green) ---
✓ Stale observations degrade gracefully without staying green
--- TEST 8: Page Becomes Visible After Inactivity ---
✓ Page visibility revalidation verified

ALL FRONTEND OPERATION HEALTH TESTS PASSED (8/8)!
```

### B. Python Contract Test Suite (`tests/unit/test_frontend_operation_health_contract.py`)
- `test_capability_api_payload_exposes_operation_level_truth` — PASSED
- `test_all_four_agent_pages_use_shared_operation_health_presenter` — PASSED
- `test_presenter_prevents_mixed_operation_state_from_becoming_green` — PASSED
- `test_brandshield_no_longer_hardcodes_provider_success_badges` — PASSED
- `test_operation_health_js_ttl_and_stale_contracts` — PASSED
- `test_operation_health_node_suite_executes_successfully` — PASSED

### C. Four Agent UI Inspection
All 4 agent pages verify inclusion of `operation-health.js` and call `AegisOperationHealth`:
1. **Scout** (`scout-agent.html`): Displays 8 channel pills with operation-level popovers.
2. **Trending** (`trending-agent.html`): Updates 6 channel dots dynamically via `loadTrendingOperationHealth()`.
3. **BrandShield** (`brandshield-agent.html`): Renders operation status pills via `renderPills()`.
4. **Personal Watch** (`personal-watch-agent.html`): Renders operation status pills via `renderPills()`.
