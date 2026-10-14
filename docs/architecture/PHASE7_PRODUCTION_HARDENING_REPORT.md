# Phase 7 production hardening report

## Reliability and security

- Shared GET transport: safe initial/final URL and redirect validation, four-redirect maximum, 5 MiB default response cap, identity encoding, and cross-origin authorization stripping.
- Retries: two attempts by default for 429/500/502/503/504 and transient network failures; exponential backoff with small jitter; at most two seconds local sleep. 400/401/403/404/405/410/422 are not retried.
- Rate limits: observable `Retry-After` seconds or HTTP-date reaches dispatcher telemetry and operation cooldown, capped at one hour. Long provider delays are surfaced without blocking a worker.
- Browser rescue: validates every HTTP(S) request and final page URL, bounds rendered HTML, and never bypasses a 401 or 429.
- Empty HTTP 200 content remains empty/failed research rather than successful evidence.
- Retrieved text remains data: planner permissions come from deterministic schemas and capability validation; malicious/unsupported LLM actions are rejected.
- Evidence keeps requested channel, actual retrieval channel, canonical URL, observed endpoint, content depth, transport facts, cache state, source identity, and lineage. Unknown HTTP facts remain unknown.

## Planning and four-agent results

Hardware and financial allegations produce different plans; financial claims prioritize regulatory filings. Explicit safe social URLs keep their concrete operation. Unsupported operations, invented communities, prompt-injection text, invalid LLM output, missing credentials, and policy-blocked Reddit actions fail closed. One evidence-gap replan is retained. Adaptive rounds deduplicate initial queries and consult operation health before execution.

`tests/integration/test_source_planner_agent_execution.py` exercises the real production entry points for BrandShield, Personal Watch, Trending, and Scout with deterministic fixtures at the acquisition boundary. It verifies source-plan propagation, normalized evidence, and provenance. Agent golden-master and research pipeline suites remain part of the full gate.

## Frontend/API status verification

`/api/agent-reach/capabilities` exposes operation assessments. `frontend/operation-health.js` maps them to direct-content, limited/partial, temporarily degraded, authentication-required, policy-blocked, not-implemented, and not-yet-verified states. Every agent page uses this presenter. A mixed state—for example healthy `twitter.profile` with unavailable `twitter.search`—is `limited`, never green. BrandShield’s hardcoded Reddit/Twitter success badges were removed.

`/api/readyz` reports process readiness separately from provider verification and explicitly states that readiness does not prove unprobed third-party health.

## Measured performance comparison

Identical deterministic input was run at pre-change commit `5c24498` and the hardened working tree. The fixture supplied three equivalent `web.search` requests, each with an 80 ms provider delay, no cache, no deep reads, and the same evidence response.

| Metric | Before | After | Change |
|---|---:|---:|---:|
| Provider calls | 3 | 1 | -66.7% |
| Planned queries | 3 | 1 | -66.7% |
| Executed queries | 3 | 1 | -66.7% |
| Wall time | 152.01 ms | 149.92 ms | -1.4% |

Concurrency hid most wall-time savings in this fixture; the proven benefit is lower provider/network load without evidence loss. No claim is made about uncached internet latency.

## Limits

- Operation observations are in-memory per process. Multiple workers may temporarily show different recent health until a shared store is intentionally designed.
- External tools do not expose HTTP status reliably; the system does not invent it.
- Credentials were absent for Xueqiu, Xiaohongshu, Instagram search, Facebook search, and Boss direct operations in the bounded live run.
- Reddit direct access remained policy-blocked.

