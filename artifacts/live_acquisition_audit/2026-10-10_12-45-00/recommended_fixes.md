# Aegis Protocol — Phase 6.7: Prioritized Acquisition Fixes Plan

**Audit Run ID:** `2026-10-10_12-45-00`  
**Target Phase:** Phase 6.7 (Pre-Phase 7 Cleanup Gate)

---

## Ranked Engineering Action Plan

### Priority 1: Zero-Auth GitHub CLI Parameter Bug Fixes (Immediate)
- **Problem:** `NativeExecutor.execute_github_search` calls `gh search repos --json ... stargazerCount`, and `execute_github_read` calls `gh repo view --json ... readme`. Both crash with exit code 1.
- **Fix:** Change `stargazerCount` to `stargazersCount`. In `execute_github_read`, remove `readme` from `--json` and use `gh repo view <repo> --json description,stargazerCount,latestRelease,url` with a secondary `gh repo view <repo> --readme` invocation.
- **Impact:** Instantly restores 100% primary native CLI execution for GitHub without needing the REST fallback.

### Priority 2: Alternative Reddit Mirror Integration (High Urgency)
- **Problem:** Arctic Shift (`arctic-shift.photon-reddit.com`) is timing out or returning 403 on the real network. 100% of Reddit requests currently degrade to superficial Bing search snippets.
- **Fix:** Implement a robust multi-provider mirror cascade for Reddit:
  1. Try Arctic Shift with reduced 3.0s timeout.
  2. Fall back to PullPush public API (`https://api.pullpush.io/reddit/search/submission/`).
  3. Fall back to unauthenticated JSON streams (`https://www.reddit.com/r/{sub}/hot.json`) using randomized User-Agent rotation.
  4. Final fallback: Bing Search Index (`INDEX_ONLY` with honest disclosure).
- **Impact:** Re-establishes direct Reddit discussion and comment acquisition for Scout and BrandShield.

### Priority 3: NativeDoctor Active Canary Health Checks
- **Problem:** `NativeDoctor.get_channel_status("reddit")` hardcodes `status="ok"`, masking Arctic Shift's actual network downtime.
- **Fix:** Introduce lightweight, cached (60s TTL) live canary pings in `NativeDoctor`:
  - Quick HEAD or GET with 1.5s timeout to mirror endpoints.
  - Set status to `"degraded"` or `"offline"` when canary fails, updating `active_backend` to reflect the active fallback.
- **Impact:** Prevents downstream planners from expecting zero-auth direct mirrors when they are down.

### Priority 4: Implement Missing NativeExecutor Methods
- **YouTube Comments:** Implement `execute_youtube_comments` using `yt-dlp --get-comments --dump-json`.
- **Bilibili Video Info / Hot:** Implement `execute_bilibili_video_info` using `https://api.bilibili.com/x/web-interface/view?bvid=...`.
- **Impact:** Eliminates false capability claims in `CAPABILITY_MATRIX`.

### Priority 5: Web Reader Anti-Bot Defense Enhancement
- **Problem:** Scrapling HTTP Fetcher gets HTTP 403 on aggressive Cloudflare-protected domains (e.g. `thehill.com`).
- **Fix:** In `NativeExecutor.execute_web_read`, when Scrapling HTTP receives HTTP 403, trigger Playwright headless browser rescue immediately.
- **Impact:** Increases full-text extraction success rate on protected media outlets.

---

## Safe Deprecation vs Must-Retain Assessment (For Phase 7)

### Must Retain (CRITICAL FALLBACKS):
1. **`backend/services/agent_reach_scraper.py`:** DO NOT DELETE YET. Its Bing News RSS parser, Google News parser, and PullPush Reddit scraper provide essential fallback functionality when native tools fail.
2. **`NativeRouter._fallback_github_rest`:** Must be retained as the secondary tier when `gh CLI` is unauthenticated or missing.
3. **`execute_web_read` Multi-Tier Cascade:** Must retain Scrapling -> Playwright -> Jina Reader emergency fallback.

### Safe to Deprecate (in Phase 7 after Phase 6.7 fixes):
1. Mock test files in `scrapers/websites/` that hardcode synthetic data (e.g. `BilibiliScraperTest`, `FacebookScraperTest`) once integration tests use real adapters.
2. Redundant compatibility shims that have zero active callers across the 4 domain agents.
