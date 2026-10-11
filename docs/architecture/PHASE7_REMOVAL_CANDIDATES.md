# Phase 7 removal-candidate register

No candidate in this register was removed.

| Component | Current callers / dependency | Potential replacement | Redundancy evidence | Regression coverage | Rollback | Recommendation |
|---|---|---|---|---|---|---|
| `backend/services/agent_reach/adapter.py` | historical imports, tests, downstream patch targets | canonical infrastructure service | re-export-only shim | acquisition contracts and identity tests | restore shim | Retain for v1; remove only after downstream deprecation window |
| `backend/services/agent_reach/native/router.py` | historical imports and monkeypatch targets | infrastructure router | re-export-only shim | route and compatibility tests | restore shim | Retain for v1 |
| `backend/services/agent_reach/scout/` shims | Scout historical imports and test patch targets | `backend/agents/scout/sources/` | identity-preserving re-exports | Phase 5 compatibility tests | restore shims | Retain until public migration notice |
| `CapabilityRegistry` channel health | registration, legacy health API, route availability | operation inventory for eligibility | channel state is coarser than operation state | capability API and runtime tests | keep registry authority | Narrow later; do not delete registration role |
| `RetrievalPlanner` initial channel selection | query wording and adaptive follow-up generation | SourcePlanningEngine | source selection overlaps historically | planner/pipeline tests | restore channel selection | Retain only query-diversity role for v1; migrate wording in later phase |
| `backend/services/agent_reach_scraper.py` | legacy fallbacks and diagnostics | canonical adapters | some duplicated fetching, but unique fallback behavior remains | shared fabric and chaos tests | retain file | Do not archive until live reliability proves replacement equivalence |
| Scout discovery strategies / `ScoutTransport` | import compatibility; not production network path | shared acquisition fabric | runtime invariant proves `ScoutSourceEngine` delegates centrally | architecture invariant and Phase 5 tests | re-enable isolated strategy | Retain, mark non-production; owner approval required to remove |

