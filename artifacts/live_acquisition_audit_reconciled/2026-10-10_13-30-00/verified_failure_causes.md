# Aegis Protocol — Verified Root-Cause Failure Analysis

**Audit Run ID:** `2026-10-10_13-30-00`  

---

## 1. Verified Concrete Bugs in Active Code

### A. GitHub CLI Parameter Incompatibilities
- **Bug 1 (`github.search`):** In `backend/services/agent_reach/native/executor.py:192`:
  `cmd = [gh_bin, "search", "repos", query, "--json", "fullName,description,url,stargazerCount,updatedAt"]`
  In `gh` CLI 2.97.0, the valid field name is `stargazersCount` (plural). Subprocess exits with code 1: `Unknown JSON field: "stargazerCount"`.
- **Bug 2 (`github.read`):** In `backend/services/agent_reach/native/executor.py:229`:
  `cmd = [gh_bin, "repo", "view", repo, "--json", "name,description,readme,url,stargazerCount,latestRelease"]`
  In `gh repo view`, `readme` is not a valid `--json` field name. Subprocess exits with code 1: `Unknown JSON field: "readme"`.
- **Resilience Clarification:** GitHub REST API fallback (`_fallback_github_rest`) in `NativeRouter` caught these exceptions and returned authentic metadata. **GitHub REST fallback is implemented directly in `NativeRouter` and has ZERO dependency on `backend/services/agent_reach_scraper.py`.** The previous report's claim that deleting `agent_reach_scraper.py` would break GitHub REST was factually incorrect.

### B. YouTube & Bilibili Missing Executor Methods
- `youtube.comments`: `NativeExecutor` has no `execute_youtube_comments` method.
- `bilibili.hot`, `bilibili.rank`, `bilibili.read`: `NativeExecutor` only contains `execute_bilibili_search`.
- Both channels advertise these operations in `CAPABILITY_MATRIX`, but callers crash or abort because methods do not exist.

### C. Web Reader Challenge Misclassification & Playwright Rescue Bypassing
- In `backend/services/agent_reach/native/executor.py:128`:
  `if len(markdown_text) < 100 or status_code in (403, 503):`
  When probing `thehill.com`, Scrapling HTTP extracted 375 characters of Cloudflare challenge HTML tokens. Because `375 > 100` and `status_code` was read as 200/403, the method returned `status: SUCCESS` with challenge garbage.
- Furthermore, the initial Phase 6.6 runner categorized this as `DIRECT_CONTENT`, concealing the Cloudflare block. In Phase 6.6B, this is correctly reclassified as `BLOCKED`.

### D. NativeDoctor False Health Reporting
- In `backend/services/agent_reach/native/doctor.py:82-103`:
  `get_channel_status("reddit")` and `get_channel_status("twitter")` intercept before running any probe and hardcode `status="ok"`, `zero_auth="AVAILABLE"`.
  This masks the real Arctic Shift network downtime and falsely reports Reddit as available to downstream agents.

### E. Architectural Module Paths Corrected
- **Agents:** The canonical domain agents are located in `backend/agents/brandshield/`, `backend/agents/trending/`, `backend/agents/scout/`, and `backend/agents/personal_watch/` (with shims `backend/agents/*_agent.py`). References to `backend/domain/...` in the previous report were erroneous.
- **Dispatcher:** The shared channel dispatcher is located in `backend/infrastructure/acquisition/routing/channel_dispatcher.py`, not `routing/dispatcher.py`.

---

## 2. Upstream Network & Platform Failures

### A. The Reddit Crisis: Total Zero-Auth Mirror Blackout
1. **Arctic Shift Outage:**
   `https://arctic-shift.photon-reddit.com/api` DNS resolves to Cloudflare IPs (`104.21.8.166`, `172.67.139.201`). TCP connection and TLS handshake complete, but the origin server hangs indefinitely. All requests time out (>8.0s).
2. **PullPush Outage:**
   `https://api.pullpush.io/reddit/search/submission/` returns `HTTP Error 429: Too Many Requests` due to public gateway congestion.
3. **Reddit Direct JSON Block:**
   `https://www.reddit.com/r/.../hot.json` returns `HTTP Error 403: Blocked` without official OAuth client headers.
4. **Reddit Search RSS:**
   `https://www.reddit.com/search.rss` returns `HTTP Error 429: Too Many Requests` to automated User-Agents.
5. **Consequence:** 100% of Reddit requests currently degrade to Bing Search Indexing (`INDEX_ONLY`). Direct Reddit post and comment scraping is **completely down**.

### B. The X / Twitter Mirror Limitations
1. **FxTwitter Profile Limitation:**
   `https://api.fxtwitter.com/<user>` returns bio metadata only. It has no user status feed endpoint.
2. **FxTwitter Search Absence:**
   FxTwitter is an embed card renderer; it has no search engine endpoint. Keyword queries degrade to Bing search index snippets (`INDEX_ONLY`).
