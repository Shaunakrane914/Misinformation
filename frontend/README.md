# Aegis Protocol — Frontend

Static HTML/JS/CSS dashboard served directly from the `frontend/` directory.
For current Phase 8 acceptance and known browser/backend gaps, read the
[dated project state](../docs/CURRENT_STATE.md). Static-page checks do not
establish real acquisition or production deployment.

## Independent review checkpoint — 2026-10-14

See the [independent review](../docs/architecture/PHASE8_INDEPENDENT_REVIEW_2026-10-14.md) and [handoff](../docs/handoffs/2026-10-14_PHASE8_INDEPENDENT_REVIEW.md). Exact unknown verdicts stay unverified; source scores are heuristic. Real recorded API replays exposed and corrected Scout and BrandShield 320px overflow plus an incomplete explorer ARIA tab role. Browser/axe checks are bounded; gradient contrast, manual screen reader and evidence-rich live result acceptance remain open. Screenshots are real captures, not fabricated data; synthetic stress inputs are labeled test-only.

## Pages
| File | Description |
|------|-------------|
| `index.html` | Main entry point with claim submission |
| `submit.html` | Canonical claim verification workspace; backend result or explicit insufficient-evidence state |
| `investigator-agent.html` | Safe entry point into `submit.html`; does not fabricate a standalone dossier |
| `research-agent.html` | Claim-research entry point into `submit.html`; no standalone open-ended research API |
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
The four agent pages use `safe-source-url.js` as a display-link guard; it
rejects non-HTTP(S) schemes and credential-bearing URLs. This does not replace
backend SSRF validation or prove that a linked publisher is authentic.

Each of the four agent pages now opens with a short verification guide. Preset
queries are real buttons; source filters and dossier dialogs are keyboard
operable; advanced identity inputs are disclosed with an announced state.
No guide or sparse-result panel substitutes demonstration data for a backend
result. Scout's former illustrative market numbers are gone. Personal Watch
separates catalog-listed handles from user-supplied, unverified candidates;
the catalog is not a live identity-authentication service. An empty forensic
finding list is not a verdict of consistency or truth.

For repeatable rendered-page checks, serve `frontend/` on localhost and run
[`audit_phase8_frontend_rendering.py`](../scripts/audits/audit_phase8_frontend_rendering.py)
with a new output directory. Its optional `--test-fixtures` payloads are
explicitly synthetic and only test rendering contracts, not live acquisition.
[`audit_phase8_accessibility.py`](../scripts/audits/audit_phase8_accessibility.py)
requires an explicitly supplied local axe-core script. Automated checks do not
replace manual screen-reader or real backend-result validation.

## Operation Health JS
`frontend/operation-health.js` — implements 45s TTL cache, visibility revalidation,
and honest stale-observation badges. Documented in `tests/frontend/test_operation_health.js`.

## Deployment
Netlify configuration is present in `netlify.toml` and
`frontend/netlify.toml`; this documentation does not verify an active public
deployment or approve a release.
