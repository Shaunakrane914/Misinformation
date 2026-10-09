# ADR 0002: Single Authoritative Acquisition Runtime & Deprecation of Shadow Scrapers

## Status
**ACCEPTED**

## Date
2026-10-09

## Deciders
- Principal Software Architect & Migration Lead
- Aegis Protocol Core Engineering Team

---

## 1. Context and Problem Statement
Evidence acquisition across the internet is the foundational capability of Aegis Protocol. Currently, evidence fetching is fragmented across multiple overlapping subsystems:
1. `backend/services/agent_reach/native/router.py`: A 1,706-line monolithic router implementing in-memory caching, direct Arctic Shift Reddit calls, direct FxTwitter calls, Jina reader HTTP calls, web search queries, and custom fallback chains.
2. `backend/services/agent_reach/adapter.py`: A 926-line facade containing **two conflicting definitions of `AgentReachService.retrieve`** (line 190 and line 631), where Python silently binds only the latter.
3. `backend/services/agent_reach/native/adapters/`: Standalone adapter classes (GitHub, Reddit, Twitter, Web, YouTube) that are partially bypassed by the monolithic router.
4. `backend/services/agent_reach_scraper.py`: A legacy 686-line BeautifulSoup/regex scraper maintained as a fallback.
5. `backend/services/agent_reach/scout/`: An embedded sub-framework inside `agent_reach` with duplicate adapters and query runners.

This duplication causes unpredictable fallback behavior, non-deterministic latency spikes, and severe maintenance risks.

---

## 2. Decision Drivers
1. **One Authoritative Routing Contract**: Every acquisition request must flow through a single, capability-aware routing engine.
2. **Explicit Fallback Accounting**: Fallback chains must record every attempt truthfully with `actual_retrieval_channel`, `is_fallback`, and `error_reason`.
3. **SSRF & URL Security**: Every outbound URL read must pass through strict private-IP and DNS rebinding validation.
4. **Resolution of Duplicate Methods**: The conflicting `retrieve` method signatures in `AgentReachService` must be reconciled into an unambiguous, typed contract with backwards compatibility.

---

## 3. Considered Alternatives
- **Alternative 1: Keep Legacy Scraper and Native Router Side-by-Side**.
  - *Rejected*: Leads to silent divergence where different agents receive different quality evidence depending on which arbitrary method they call.
- **Alternative 2: Rewrite Acquisition Using External Microservice/API**.
  - *Rejected*: Incurs recurring SaaS subscription costs, adds network hops, and violates the zero-cost self-contained deployment philosophy.
- **Alternative 3: Consolidate Around a Single Modular Acquisition Fabric (Chosen)**.
  - Refactor `NativeRouter` into a thin orchestration facade (`infrastructure/acquisition/routing/`).
  - Move channel-specific logic into clean, modular platform adapters (`infrastructure/acquisition/adapters/`).
  - Maintain `agent_reach_service` as the public application-facing port.
  - Retire `agent_reach_scraper.py` into a strictly isolated, test-covered fallback adapter before deprecation.

---

## 4. Decision Outcome
Chosen option: **Alternative 3 — Consolidated Modular Acquisition Fabric**.

### 4.1 Resolution of Duplicate `AgentReachService.retrieve`
Investigation verified that callers currently fall into two distinct usage patterns:
1. **Domain Agents (`scout_agent.py`, `trending_agent.py`, `scout/engine.py`)**:
   - Call `agent_reach_service.execute(request: RetrievalRequest) -> List[EvidenceFragment]`.
2. **Legacy / Test Callers (`test_agent_reach_service.py`, `test_agent_reach_chaos.py`, `adapter.py:omni_scan`)**:
   - Call `agent_reach_service.retrieve(query=str, domain=str, channels=list, ...) -> RetrievalResult`.

**Architectural Contract:**
- `execute(request: RetrievalRequest) -> List[EvidenceFragment]`: The primary strongly-typed domain contract.
- `retrieve(...)`: Reconciled to accept either `request: RetrievalRequest` or keyword arguments `(query: str, domain: str = "general", channels: Optional[List[str]] = None, ...)`. If a `RetrievalRequest` is provided, it delegates cleanly to `execute()`. The duplicate shadowed method definition at line 190 of `adapter.py` is removed, and polymorphism is handled within a single method body.

### 4.2 Modular Decomposition of `router.py` (1,706 lines)
The monolithic `router.py` will be decomposed into focused units:
- `infrastructure/acquisition/routing/router.py`: Core routing and channel dispatch (~250 lines).
- `infrastructure/acquisition/routing/policy.py`: Fallback chain selection and rate-limit backoff (~150 lines).
- `infrastructure/acquisition/adapters/social/reddit.py`: Arctic Shift batch & post client (~200 lines).
- `infrastructure/acquisition/adapters/social/twitter.py`: FxTwitter status & profile client (~150 lines).
- `infrastructure/acquisition/adapters/web/jina.py`: Zero-auth markdown reader (~150 lines).
- `infrastructure/acquisition/security/url_validator.py`: SSRF, loopback, and cloud metadata filter (~120 lines).

---

## 5. Consequences

### Positive Consequences
- **Predictable Telemetry**: Every evidence fragment carries verified `actual_retrieval_channel` and fallback lineage.
- **Isolated Testing**: Social adapters can be tested with simulated Arctic Shift or FxTwitter payloads without spinning up the entire router.
- **Zero Ambiguity**: No duplicate method definitions in class bodies.

### Negative Consequences / Trade-offs
- Requires updating imports during Phase 3 migration. Backward-compatibility import aliases in `backend/services/agent_reach/` will be preserved until Phase 7.
