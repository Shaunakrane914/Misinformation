# Current API route map — independent follow-up 2026-10-14

Route decorators remain as below; the [independent review](../architecture/PHASE8_INDEPENDENT_REVIEW_2026-10-14.md) corrected output-contract behavior. Scout grouped catalysts/contradictions/news/social now assemble without slice errors or dictionary-key evidence. Specialist identity/media/PII/review outputs may use new conservative review-required status strings; unknown frontend values must stay unverified. Model-provided claims cannot verify themselves merely by citing a valid ID. Capability inventory includes four authoritative channels without implying live health. Exact runtime schemas remain authoritative.

This map is based on the decorators and router registry in
[`backend/api/`](../../backend/api/) at `e74b984`. The runtime OpenAPI at
`/openapi.json` or `/docs` is the exhaustive schema for the checked-out
server; compatibility aliases and hidden routes may not appear there. Route
existence does not prove live-provider health, a populated response, or
deployment readiness. See [Current State](../CURRENT_STATE.md).

| Method | Active path | Owning module | Meaning and boundary |
|---|---|---|---|
| POST | `/api/claims/verify` | `claims.py` | Synchronous claim verification; evidence-dependent and abstention-aware. |
| POST | `/api/claims/submit` | `claims.py` | Queue/ingest a claim; aliases include `/api/claims` and `/api/submit`. |
| GET | `/api/claims/{claim_id}` | `claims.py` | Claim status/result when available. |
| GET | `/api/claims/{claim_id}/research` | `claims.py` | Research corpus for a stored claim. |
| GET | `/api/claims/{claim_id}/evidence` | `claims.py` | Stored evidence records for a claim. |
| GET | `/api/claims` | `claims.py` | Paginated stored claims. |
| POST | `/api/scout/analyze` | `agents.py` | Scout financial investigation. |
| POST | `/api/scout/analyze/stream`, `/api/trending/scan/stream`, `/api/brandshield/scan/stream`, `/api/personal/scan/stream` | `agents.py`, `research_stream.py` | Additive live progress/result streams using the original validated payloads. Server-confirmed steps, not ETA or source-truth scores. See [stream contract](../operations/AGENT_PROGRESS_AND_TIMEOUTS.md). |
| POST | `/api/trending/scan` | `agents.py` | Trending investigation. |
| POST | `/api/brandshield/scan` | `agents.py` | BrandShield investigation. |
| POST | `/api/personal/scan` | `agents.py` | Personal Watch investigation; `/api/personal-watch/scan` is an alias. Legacy `official_handles`/`official_domains` request keys are unverified candidate hints. |
| GET | `/api/agent-reach/capabilities`, `/api/agent-reach/health`, `/api/agent-reach/doctor` | `agent_reach.py` | Capability inventory and diagnostics, not blanket provider-success certificates. |
| POST | `/api/agent-reach/scan`, `/api/agent-reach/omni-scan`, `/api/agent-reach/read`, `/api/agent-reach/debug` | `agent_reach.py` | Bounded acquisition and diagnostic operations. |
| POST | `/api/agent-reach/extract` | `agent_reach.py` | Phase 9 additive native operation read/search with bounded Quick/Deep follow-ups, runtime policy checks and captured-passage inspection; not claim adjudication. See [extraction contract](../operations/PHASE9_EXTRACTION_RUNBOOK.md). |
| GET | `/healthz`, `/readyz`, `/api/system/deployment-status` | `system.py` | Liveness/readiness/deployment observations; `/api/healthz`, `/api/readyz`, `/api/deployment-status` aliases exist. |
| GET/POST | `/api/research/replay/dossiers`, `/api/research/replay/dossiers/{session_id}`, `/api/research/replay/reexecute/{session_id}` | `replay.py` | List/read/replay stored dossiers; `/api/replay` aliases exist. Refetch mode may make live requests; hash/structural checks are not proof of source truth. |
| POST | `/api/lab/synthetic-detect`, `/api/lab/blast-radius`, `/api/lab/consensus` | `threat_lab.py` | Explicit statistical/simulation tools, not observed external evidence. |
| POST | `/api/deploy-response` | `agents.py` | Privileged response action guarded by operator token and backing-state requirements; not a public demo operation. |

The four agent pages are served by FastAPI at `/scout-agent`,
`/trending-agent`, `/brandshield-agent` and `/personal-watch-agent` (with
`.html` aliases). `/research-agent` and `/investigator-agent` are entry pages
for claim verification, not separate open-ended research APIs. Other frontend
paths and compatibility aliases live in [`backend/main.py`](../../backend/main.py).

Avoid copying legacy endpoint claims such as `/api/agents/research/query`,
`/api/verify/truth-dossier` or `/api/brandshield/audit`: those paths are not
registered by the current router modules. Request/response fields can change;
read the Pydantic models and generated OpenAPI for exact payloads.
