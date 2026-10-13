# Aegis Protocol — Frontend

Static HTML/JS/CSS dashboard served directly from the `frontend/` directory.

## Pages
| File | Description |
|------|-------------|
| `index.html` | Main entry point with claim submission |
| `submit.html` | Canonical claim verification workspace; backend result or explicit insufficient-evidence state |
| `investigator-agent.html` | Safe entry point into `submit.html`; does not fabricate a standalone dossier |
| `scout-agent.html` | Financial and corporate research workspace |
| `trending-agent.html` | Narrative and trend research workspace |
| `brandshield-agent.html` | Brand-threat research workspace |
| `personal-watch-agent.html` | Identity and impersonation research workspace |
| `status.html` | Runtime status view |
| `about.html` | Labeled protocol pipeline simulator, not live investigation proof |

The unified report is rendered by `unified-report-renderer.js` on agent pages.
It preserves absent fields, distinguishes source-group heuristics from proven
independence, and displays query coverage separately from evidence. Backend
research must still be checked independently; the static UI does not establish
live-provider health or dossier integrity. See the latest
[handoff](../docs/handoffs/README.md) for current acceptance limits.

## Operation Health JS
`frontend/operation-health.js` — implements 45s TTL cache, visibility revalidation,
and honest stale-observation badges. Documented in `tests/frontend/test_operation_health.js`.

## Deployment
Deployed via Netlify. See `netlify.toml` and `frontend/netlify.toml`.
