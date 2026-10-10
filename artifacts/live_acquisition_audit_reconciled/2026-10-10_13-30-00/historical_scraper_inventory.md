# Aegis Protocol — Historical Scraper Inventory & Repository Recovery

**Audit Run ID:** `2026-10-10_13-30-00`  
**Historical References:** `research/scraper_bakeoff/reports/repository_inventory.json`, `research/scraper_bakeoff/repos/`, `backend/services/agent_reach_scraper.py`

---

## Complete 16-Platform Scraper Implementation Inventory

### 1. Web (`web`)
- **Tested Implementations:** Scrapling (`Fetcher`), Playwright (`sync_playwright`), Jina Reader (`r.jina.ai`), urllib/BeautifulSoup.
- **Repository / Library:** `Scrapling` (v0.4.15, D4Vinci, MIT), `playwright-python` (v1.52.0, Microsoft, Apache-2.0).
- **Authentication Required:** None.
- **Historical Outcome:** Scrapling achieved 90.0% availability, 698ms P50 latency. Playwright had 420ms startup penalty.
- **Current Status:** Installed & active in `NativeExecutor.execute_web_read`.
- **Reachable Today:** **YES**. Primary Scrapling HTTP is actively invoked.

### 2. Web Search (`web_search`)
- **Tested Implementations:** Bing Search Scraper (HTTP + Base64 URL decoder), DuckDuckGo, Exa via mcporter.
- **Repository / Library:** Native in-process HTTP client.
- **Authentication Required:** None.
- **Historical Outcome:** 100% resolution of fallback social cases.
- **Current Status:** Installed & active in `NativeRouter._execute_web_search`.
- **Reachable Today:** **YES**. Primary search engine for Aegis.

### 3. GitHub (`github`)
- **Tested Implementations:** `gh CLI`, GitHub REST API (`api.github.com`), PyGithub.
- **Repository / Library:** GitHub CLI 2.97.0 + `urllib.request` REST client.
- **Authentication Required:** None for public repos (60 req/hr unauth limit).
- **Historical Outcome:** 99.0% reliability across issues, PRs, and repos.
- **Current Status:** Installed. `gh CLI` currently fails due to 2 parameter bugs (`stargazerCount`, `readme`). GitHub REST fallback is active and achieves 100% metadata retrieval.
- **Reachable Today:** **YES** via REST fallback.

### 4. YouTube (`youtube`)
- **Tested Implementations:** `yt-dlp` (in-process `import yt_dlp`), `yt-dlp` CLI subprocess, Whisper transcribe.
- **Repository / Library:** `yt-dlp` (v2026.09.28 / CLI 2026.08.19, The Unlicense).
- **Authentication Required:** None for public videos.
- **Historical Outcome:** 92.0% direct metadata retrieval, 100% field completeness. In-process eliminated 848ms CLI overhead.
- **Current Status:** Installed & active for search, metadata, and auto-subtitles. Comments method missing.
- **Reachable Today:** **YES** for 3/4 operations.

### 5. Bilibili (`bilibili`)
- **Tested Implementations:** Bilibili Web Search API (`api.bilibili.com/x/web-interface/search/all/v2`), `bili-cli`, WBI signer.
- **Repository / Library:** Native HTTP client.
- **Authentication Required:** None for basic search; WBI/SESSDATA required for high-res video streaming.
- **Historical Outcome:** Direct video stream scrapers encountered HTTP 412 anti-scraping blocks.
- **Current Status:** Public search API is implemented and works. `hot`, `rank`, `read` are not implemented.
- **Reachable Today:** **YES** (Search only).

### 6. V2EX (`v2ex`)
- **Tested Implementations:** V2EX Public REST API (`/api/topics/hot.json`, `/api/topics/latest.json`, `/api/replies/show.json`).
- **Repository / Library:** Native HTTP client.
- **Authentication Required:** None.
- **Historical Outcome:** 100% success rate, low latency (~330ms).
- **Current Status:** Installed & fully operational.
- **Reachable Today:** **YES**.

### 7. RSS (`rss`)
- **Tested Implementations:** `feedparser` on Google News RSS, Bing News RSS, PR wires.
- **Repository / Library:** `feedparser` (v6.0.12, BSD-2-Clause).
- **Authentication Required:** None.
- **Historical Outcome:** 100% reliable news wire syndication.
- **Current Status:** Installed & fully operational.
- **Reachable Today:** **YES**.

### 8. Reddit (`reddit`)
- **Tested Implementations:**
  1. `PRAW` (v7.8.1, BSD-2-Clause): Required OAuth2 client ID/secret. Cloned & installed, but rejected for zero-config mode due to mandatory API keys.
  2. `PullPush` API (`api.pullpush.io`): Used in legacy `agent_reach_scraper.py`. Currently returns HTTP 429 Too Many Requests.
  3. Reddit RSS (`reddit.com/search.rss`): Used in legacy `agent_reach_scraper.py`. Currently blocked by Reddit IP limits (HTTP 429/403).
  4. `Arctic Shift` (`arctic-shift.photon-reddit.com/api`): Promoted on Oct 6. **Currently timing out (>8.0s) on live network.**
  5. `Bing Search Index`: Active tertiary fallback in modern router.
- **Current Status:** Arctic Shift is unreachable. System degrades 100% to Bing Search Index.
- **Reachable Today:** **YES** (as indexed fallback only).

### 9. Twitter / X (`twitter`)
- **Tested Implementations:**
  1. `twscrape` (v0.20.1, MIT): GraphQL scraper using account pool with `auth_token` & `ct0` cookies in SQLite `accounts.db`. Installed, but rejected for zero-config mode due to cookie pool maintenance burden.
  2. `Twitter Syndication` (`syndication.twitter.com`): Used in legacy `agent_reach_scraper.py`. Currently returns HTTP 429.
  3. `FxTwitter` (`api.fxtwitter.com`): Promoted on Oct 6. Fully operational for status (`/status/<id>`) and profile (`/<user>`). Does not support keyword search.
  4. `Bing Search Index`: Active search fallback.
- **Current Status:** FxTwitter active for status and profile; Bing search index active for search.
- **Reachable Today:** **YES** (Status/Profile direct; search indexed).

### 10. Xueqiu (`xueqiu`)
- **Tested Implementations:** Bing Search Index (in Oct 6 benchmark), Xueqiu Cookie API.
- **Authentication Required:** Cookie required for direct API (`xq_a_token`).
- **Historical Outcome:** Search index provided 125-char snippets. Direct scraper was never built.
- **Current Status:** Credential guard only in `StandardChannelHandlers`.
- **Reachable Today:** **NO** (returns empty list).

### 11. LinkedIn (`linkedin`)
- **Tested Implementations:** `linkedin_scraper` (v3.1.2, MIT, Playwright-based requiring `li_at`), Bing Search Index, Jina Reader.
- **Authentication Required:** Mandatory session cookie (`li_at`).
- **Historical Outcome:** 78% reliability with cookie; 0% unauthenticated (HTTP 999 wall).
- **Current Status:** Credential guard only in `StandardChannelHandlers`.
- **Reachable Today:** **NO** (returns empty list).

### 12. Xiaohongshu (`xiaohongshu`)
- **Tested Implementations:** Bing Search Index (in Oct 6 benchmark), `xhs-cli` / MCP server.
- **Authentication Required:** Mandatory web session cookie (`web_session`).
- **Historical Outcome:** Search index only. Direct unauthenticated scraping blocked by anti-bot slider captcha.
- **Current Status:** Credential guard only in `StandardChannelHandlers`.
- **Reachable Today:** **NO** (returns empty list).

### 13. Facebook (`facebook`)
- **Tested Implementations:** `facebook-scraper` (v0.2.59, MIT), Bing Search Index.
- **Authentication Required:** Mandatory cookies (`c_user`, `xs`).
- **Historical Outcome:** 35% reliability historically with cookies. Stale library broken on Python 3.13. Unauthenticated yields 0 posts.
- **Current Status:** Credential guard only in `StandardChannelHandlers`.
- **Reachable Today:** **NO** (returns empty list).

### 14. Instagram (`instagram`)
- **Tested Implementations:** `instaloader` (v4.15.3, MIT), Bing Search Index.
- **Authentication Required:** Mandatory session in 2026 (`sessionid`).
- **Historical Outcome:** Unauthenticated fails with `ConnectionException: line 1 column 1` (login redirect).
- **Current Status:** Credential guard only in `StandardChannelHandlers`.
- **Reachable Today:** **NO** (returns empty list).

### 15. Boss直聘 (`boss`)
- **Tested Implementations:** `boss-agent-cli` via Chrome DevTools Protocol (CDP).
- **Authentication Required:** Mandatory live browser CDP session port (`BOSS_CDP_PORT`).
- **Historical Outcome:** Requires interactive browser session to bypass slider challenge.
- **Current Status:** Credential guard only in `StandardChannelHandlers`.
- **Reachable Today:** **NO** (returns empty list).

### 16. Xiaoyuzhou (`xiaoyuzhou`)
- **Tested Implementations:** Groq Whisper audio transcription.
- **Authentication Required:** `GROQ_API_KEY`.
- **Historical Outcome:** Multimedia transcription service.
- **Current Status:** Credential guard only in `StandardChannelHandlers`.
- **Reachable Today:** **NO** (returns empty list).
