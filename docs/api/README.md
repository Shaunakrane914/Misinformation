# API reference

Run the application and open `/docs` for the generated OpenAPI schemas, parameters
and error responses. The route implementations are in `backend/api/`.

| Endpoint | Purpose |
| --- | --- |
| `POST /api/claims/verify` | Synchronous specific-claim investigation |
| `POST /api/claims/submit` | Submit a claim for queued processing |
| `GET /api/claims/{claim_id}` | Retrieve claim state/results |
| `GET /api/claims/{claim_id}/research` | Retrieve its retained research corpus |
| `POST /api/scout/analyze/stream` | Scout research progress and result |
| `POST /api/brandshield/scan/stream` | BrandShield research progress and result |
| `POST /api/trending/scan/stream` | Trending research progress and result |
| `POST /api/personal/scan/stream` | Personal Watch progress and result |
| `GET /api/healthz` | Process liveness |
| `GET /api/readyz` | Application readiness |
| `GET /api/system/deployment-status` | Deployment observations |

An HTTP 200 or completed stream means a response arrived. It does not establish
that relevant articles qualified or that a claim was verified. Inspect source,
finding, uncertainty, acquisition and workbench fields separately.

Source IDs, hashes and passage offsets support citation inspection. They do not
prove source truth, publisher independence or identity authenticity. Missing source
coverage must remain explicit. See [architecture](../ARCHITECTURE.md) and
[testing](../TESTING.md).
