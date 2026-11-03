# Frontend

Responsive HTML, CSS and JavaScript workspaces for claims, Scout, BrandShield,
Trending and Personal Watch. FastAPI serves these locally; the production static
site can also be uploaded to Cloudflare Pages.

- `aegis-nav.js`: shared navigation and mobile drawer/dock.
- `agent-research-client.js`: specialist requests, progress and error handling.
- `unified-report-renderer.js`: shared reports and passage workbench.
- `forensic-explorer.js`: inspectable acquisition and source details.
- `aegis-theme.css`: shared visual styles.

Run every Node script in `tests/frontend/` after shared UI changes. Browser checks
should use actual report text and mobile/desktop viewports; page word count alone
does not establish useful evidence. See [Testing](../docs/TESTING.md),
[API](../docs/api/README.md) and [known limitations](../docs/EVALUATION.md).
