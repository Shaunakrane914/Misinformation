# Production Deployment: Cloudflare Pages & Render Live Rollout — 2026-11-01

**Scope:** Deployment and live verification of AEGIS / Signal adaptive redesign, mobile navigation (dock, drawer, exit animations), Claim Intelligence Core, and AI scraping expansion across Cloudflare Pages and Render.

---

## 1. Root Cause Analysis: Why Frontend Initially Appeared Undeployed

- **Render Backend (`https://misinformation-1ouh.onrender.com`)**: Connected directly to GitHub `main` via Render auto-deploy. Deployments trigger automatically on push.
- **Cloudflare Pages (`https://aegis-protocol-110.pages.dev`)**: Configured with `Git Provider: No` (direct upload project). Pushing commits to GitHub does NOT trigger a Cloudflare Pages rebuild automatically.
- Cloudflare Pages was last deployed 3 days prior. When checked directly:
  - `https://aegis-protocol-110.pages.dev/index.html` lacked `.hero-agent-pills-row`.
  - `https://aegis-protocol-110.pages.dev/aegis-nav.js` lacked `#aeMobileDock` and `#aeNavMobileToggle`.

---

## 2. Deployment Execution & Live Verification

### Cloudflare Pages Direct Upload
Executed direct deployment using authenticated Wrangler OAuth credentials:
```bash
npx wrangler pages deploy frontend --project-name aegis-protocol --branch main --commit-hash 4c621fb --commit-message "feat: AEGIS / Signal adaptive redesign, mobile navigation, Claim Intelligence Core, and AI scraping expansion" --commit-dirty=false
```
- **Deployment ID & URL**: `https://664a6f07.aegis-protocol-110.pages.dev`
- **Canonical Production URL**: `https://aegis-protocol-110.pages.dev/`
- **Files Uploaded**: 34 static assets (`_headers`, `_redirects`, HTML, CSS, JS).

### CI Matrix Repair
- Resolved a regression in `backend/services/research/research_profiles.py` where changing `STANDARD` constants broke `tests/unit/test_oct28_evidence_selection_repairs.py::test_deep_request_rebases_only_implicit_standard_limits`. Restored standard baseline limits while retaining adversarial probe expansions in the planning engine.
- Committed and pushed as `4c621fb` (`fix(budget): restore standard profile limits to satisfy rebase contracts`).
- GitHub Actions run **41318293504** completed with all 5 jobs green:
  1. `Fatal Python lint and frontend contracts` (Passed in 26s)
  2. `Unit, chaos and security (Python 3.12)` (Passed in 1m29s)
  3. `Unit, chaos and security (Python 3.13)` (Passed in 1m41s)
  4. `Unit, chaos and security (Python 3.11)` (Passed in 1m32s)
  5. `Entire offline suite, persistence and release validators` (Passed in 2m7s)

---

## 3. Live Empirical Verification

### Live Mobile Playwright Test (iPhone 14, 390x844)
Targeting `https://aegis-protocol-110.pages.dev/index.html`:
- `#aeMobileDock` visibility: `True`
- `#aeNavMobileToggle` visibility: `True`
- `.hero-agent-pills-row` visibility: `True`
- Layout Metrics: `scrollWidth = 390px`, `innerWidth = 390px`, `overflowSafe = True`
- Live mobile screenshot saved to `scratch/live_mobile_index.png` and artifact storage.

### Live Render API Endpoints
- `GET https://misinformation-1ouh.onrender.com/health`: `HTTP 200 OK`, `version: 4.1.0`.
- `GET https://misinformation-1ouh.onrender.com/api/healthz`: `HTTP 200 OK`, `system: "Aegis Protocol"`, `registered_modules: 7`.
