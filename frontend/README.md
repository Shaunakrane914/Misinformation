# Aegis Protocol — Frontend

Static HTML/JS/CSS dashboard served directly from the `frontend/` directory.

## Pages
| File | Description |
|------|-------------|
| `index.html` | Main dashboard with claim submission |
| `about.html` | Protocol pipeline simulator |
| `operation-health.html` | Live operation capability monitor |

## Operation Health JS
`frontend/operation-health.js` — implements 45s TTL cache, visibility revalidation,
and honest stale-observation badges. Documented in `tests/frontend/test_operation_health.js`.

## Deployment
The static frontend is served by Cloudflare Pages (`https://aegis-protocol-110.pages.dev/`), configured via `_headers` and `_redirects`. API requests proxy to the active Render backend.
