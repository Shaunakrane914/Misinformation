# Aegis Protocol — Phase 6.7: Scraper Reconnection & Reliability Plan

**Target Phase:** Phase 6.7 (Pre-Phase 7 Cleanup Gate)  
**Standard:** Ranked Implementation Roadmap Based on Reconciled Ground Truth

---

## 1. Categorized Platform Action Matrix

### Category A: Existing Scraper Works but is Disconnected / Disarmed
- **Reddit RSS Fallback in `agent_reach_scraper.py`:**
  `agent_reach_scraper.py:126` has a working Reddit RSS stream parser. Connect it as a secondary zero-auth fallback before degrading to Bing search index.
- **Seven Credential-Gated Channels in `StandardChannelHandlers`:**
  Currently, `_execute_authenticated()` returns `[]` even when credentials are present.
  - Implement real adapter calls when credentials exist (e.g. `instaloader` session file, `mcp-server-linkedin`, `GROQ_API_KEY` for Xiaoyuzhou).
  - When credentials are absent, return explicit `AUTH_REQUIRED` and route gracefully to `Bing Search Index` for public entity mentions without claiming direct scraping.
  - Fix bug: Never set `telemetry["status"] = "SUCCESS"` when `len(fragments) == 0`.

### Category B: Existing Scraper Has a Fixable Bug
- **GitHub CLI (`NativeExecutor`):**
  - Fix line 192: Change `stargazerCount` to `stargazersCount`.
  - Fix line 229: Remove `readme` from `--json` in `gh repo view`. Use `gh repo view <repo> --readme` to fetch the README markdown separately.
  - Impact: Restores primary CLI path; REST API remains as secondary fallback.
- **YouTube Comments (`NativeExecutor`):**
  - Implement `execute_youtube_comments` using `yt-dlp --get-comments --dump-json`.
- **Bilibili Details (`NativeExecutor`):**
  - Implement `execute_bilibili_video_info` using `https://api.bilibili.com/x/web-interface/view?bvid=...`.
- **Web Reader Challenge Bypass (`NativeExecutor`):**
  - Fix line 128: When Scrapling HTTP encounters challenge tokens or HTTP 403, trigger Playwright headless browser rescue immediately, regardless of body character count.

### Category C: Alternative Imported Scraper Performs Better
- **YouTube in-process vs CLI:**
  In-process `yt-dlp` (`import yt_dlp`) performs 848ms faster than CLI subprocess. Retain in-process as primary.
- **Scrapling vs Playwright on general web:**
  Scrapling HTTP runs 4x faster with 7MB RSS delta. Retain Scrapling HTTP primary, Playwright secondary rescue.

### Category D: Public Access is Temporarily Failing (External Dependency Downtime)
- **Reddit (Arctic Shift):**
  Implement multi-mirror cascade with short timeouts (3.0s):
  1. Arctic Shift (3.0s timeout).
  2. PullPush API (`api.pullpush.io`).
  3. Reddit RSS stream with rotating headers.
  4. Bing Search Index (`INDEX_ONLY` with honest disclosure).

### Category E: Public Access is Restricted and Authorization is Required
- **Instagram, Facebook, LinkedIn, Xiaohongshu, Boss, Xiaoyuzhou:**
  Direct unauthenticated scraping is dead or non-existent upstream.
  - Honor credential requirements cleanly.
  - Route public queries to search syndication index.
  - Never fabricate direct scraping success.

### Category F: No Tested Working Implementation Exists
- None. All 16 platforms now have clear classifications and documented integration paths.

---

## 2. Definitive Deprecation Boundaries for Phase 7

### Scrapers That MUST Be Retained:
1. **`backend/services/agent_reach_scraper.py`:** Retain its Google News RSS, Bing News RSS, and Reddit RSS parsers.
2. **`NativeRouter._fallback_github_rest`:** Retain as the permanent secondary tier for GitHub when `gh CLI` is unauthenticated or missing.
3. **`execute_web_read` Multi-Tier Cascade:** Retain Scrapling HTTP -> Playwright Rescue -> Jina Reader emergency cascade.

### Safe to Deprecate (in Phase 7 after Phase 6.7):
1. Synthetic laboratory test classes in `scrapers/websites/` (`BilibiliScraperTest`, `FacebookScraperTest`, `InstagramScraperTest`) once unit tests validate real adapters.
2. Redundant compatibility shims that have zero active callers across the 4 domain agents.

---

## 3. The Definitive Answer

### **Which of our 16 platforms can Aegis directly retrieve real public content from today, which cannot, and precisely why?**

1. **CAN Directly Retrieve Full Content / Transcripts / Threads (5 Platforms):**
   - **`web`:** Scrapling HTTP retrieves full article bodies (up to 136k chars) from general media and Wikipedia.
   - **`youtube`:** `yt-dlp` extracts full video auto-subtitles and transcripts (4,000+ chars).
   - **`v2ex`:** Public JSON API retrieves full developer threads and user replies.
   - **`rss`:** `feedparser` retrieves structured press releases and wire articles.
   - **`github` (Issues):** GitHub REST API retrieves full issue bodies and comments.

2. **CAN Directly Retrieve Metadata / Search / Status (3 Platforms):**
   - **`github` (Search & Repos):** REST API retrieves authentic repo metadata and star counts (CLI currently broken by parameter typos).
   - **`bilibili`:** Public search API retrieves video search results and metadata (read/hot/rank unimpl).
   - **`twitter`:** `api.fxtwitter.com` retrieves authentic status text and profile bios (keyword search relies on Bing index).

3. **CANNOT Directly Retrieve Without Credentials (7 Platforms):**
   - **`instagram`, `facebook`, `linkedin`, `xiaohongshu`, `xueqiu`, `boss`, `xiaoyuzhou`:**
   - **Why:** Direct unauthenticated scraping is blocked upstream by login walls, session checks, and anti-bot challenges. The dispatcher currently contains only credential guards that return empty lists.

4. **CANNOT Directly Retrieve Due to Mirror Downtime (1 Platform):**
   - **`reddit`:**
   - **Why:** Arctic Shift origin server is dead/unresponsive behind Cloudflare; PullPush returns HTTP 429; direct Reddit JSON returns HTTP 403. Currently relies 100% on Bing Search Index snippets.
