# Current implementation owners

Maintained 2026-10-15. Paths identify concrete owners, not measured acceptance. See [handoffs](../handoffs/README.md) for the checked branch and dated validation.

| Responsibility | Owner |
|---|---|
| App composition, static routes and middleware | [backend/main.py](../../backend/main.py) |
| HTTP request/response entry points | [backend/api](../../backend/api/) |
| Research stage orchestration | [application research](../../backend/application/research/) |
| Claim workflows (not yet extracted to application layer) | [claims API](../../backend/api/claims.py), [claim worker](../../backend/workers/claim_worker.py) |
| Canonical acquisition service | [service.py](../../backend/infrastructure/acquisition/service.py) |
| Native dispatch and cohesive handlers | [routing](../../backend/infrastructure/acquisition/routing/) |
| Bounded public transport and redirect checks | [HTTP transport](../../backend/infrastructure/acquisition/network/http.py) |
| Operation policy, cooldowns and executable inventory | [operation capabilities](../../backend/services/agent_reach/native/operation_capabilities.py) |
| Provider normalization | [native normalizer](../../backend/services/agent_reach/native/normalizer.py) |
| Claim-aware source planning | [source planner](../../backend/services/agent_reach/source_planner.py) |
| Relevance, source qualification and proposition grounding | [research services](../../backend/services/research/) |
| Specialist behavior | [Scout](../../backend/agents/scout/), [Trending](../../backend/agents/trending/), [BrandShield](../../backend/agents/brandshield/), [Personal Watch](../../backend/agents/personal_watch/) |
| Unified report conversion | [report builder](../../backend/services/report_builder.py) and [report schema](../../backend/schemas/unified_report.py) |
| Pure captured-text inspection | [evidence inspection](../../backend/schemas/evidence_inspection.py) |
| Shared evidence UI and safe follow-up reads | [renderer](../../frontend/unified-report-renderer.js), [theme](../../frontend/aegis-theme.css) |
| Phase 9 repeatable source sampling | [cycle runner](../../scripts/audits/run_phase9_extraction_cycle.py), [real extraction API smoke](../../scripts/audits/run_phase9_source_api_smoke.py) |
| Phase 9 regression controls | [capture/contract tests](../../tests/unit/test_phase9_extraction_quality.py), [community-source tests](../../tests/unit/test_phase9_community_sources.py), [extraction API tests](../../tests/unit/test_phase9_extraction_api.py) |

Legacy agent modules and `backend/services/agent_reach/adapter.py` remain compatibility surfaces. Do not delete them because canonical implementations are elsewhere. Historical inventories and design specifications retain their original dates and may contain obsolete module names; prefer this map and the checked source for implementation work.
