# Aegis Protocol — Live Reality vs Historical Benchmarks Matrix

**Audit Run ID:** `2026-10-10_13-30-00`  

---

| Channel | Advertised in `CAPABILITY_MATRIX` | October 6 Scraper Bake-off | October 6 Zero-Auth Migration | Phase 6.6 Initial Audit Claim | Phase 6.6B Reconciled Reality | Ground Truth Discrepancy |
|---|---|---|---|---|---|---|
| **web** | `read` (none) | 90.0% Scrapling HTTP; Playwright secondary | Preserved Policy D | 50.0% direct; 1 Cloudflare blocked (labeled DIRECT) | **50.0% Direct; 50.0% Blocked (The Hill HTTP 403)** | Phase 6.6 wrongly classified The Hill Cloudflare block as DIRECT_CONTENT |
| **web_search** | `search` (none) | 100% search syndication fallback | Preserved Bing Search | 100% indexed | **100% INDEX_ONLY (Bing Search)** | Verified |
| **github** | `search, read, issues, prs, releases` | 99.0% native API / CLI | Preserved gh CLI + REST | 50% success (REST works; gh CLI failed) | **REST Fallback 100% Direct; gh CLI 100% Failed** | `stargazerCount` & `readme` parameter bugs in `NativeExecutor` |
| **youtube** | `search, read, transcript, comments` | 92.0% yt-dlp in-process metadata | Preserved yt-dlp | 75% success; comments missing | **75.0% Working; 25.0% NOT_IMPLEMENTED** | `youtube.comments` missing from `NativeExecutor` |
| **bilibili** | `search, read, hot, rank` | 95.0% Search API; 412 video blocks | Search API retained | 25% success; 3 unimpl | **25.0% Working (Search); 75.0% NOT_IMPLEMENTED** | `hot`, `rank`, `read` missing from `NativeExecutor` |
| **v2ex** | `hot, latest, search, topic, replies` | 100% public REST API | Public API retained | 100% success (3/3 direct) | **100% DIRECT_CONTENT** | Verified |
| **rss** | `read` (none) | 100% feedparser | feedparser retained | 100% success (1/1 direct) | **100% DIRECT_CONTENT** | Verified |
| **reddit** | `search, read, comments` | PRAW (99.5% auth) -> Search fallback (65.9%) | Arctic Shift promoted as Zero-Auth Mirror | 0% Direct; 100% Bing index | **0.0% Direct; 100% INDEX_ONLY (Arctic Shift Dead)** | Arctic Shift origin server dead behind Cloudflare. Doctor wrongly reported "ok". |
| **twitter** | `search, read, status, profile, feed` | twscrape (94.0% auth) -> Search fallback | FxTwitter promoted as Zero-Auth Mirror | 66.7% direct (grouped profile shell) | **33.3% Direct Body; 33.3% Partial; 33.3% Indexed** | Phase 6.6 inflated direct rate. FxTwitter has no search or user tweet timeline. |
| **xueqiu** | `search, quotes, hot_posts` | Search index only (125 chars) | Auth-gated | 0% (AUTH_REQUIRED) | **0.0% (DISCONNECTED_GUARD)** | `_execute_authenticated` returns empty list even when credentials pass |
| **linkedin** | `profile, company, jobs, read` | linkedin_scraper (78% auth); Search fallback | Auth-gated | 0% (AUTH_REQUIRED) | **0.0% (DISCONNECTED_GUARD)** | `_execute_authenticated` returns empty list even when credentials pass |
| **xiaohongshu**| `search, read, comments, feed` | Search index only (125 chars) | Auth-gated | 0% (AUTH_REQUIRED) | **0.0% (DISCONNECTED_GUARD)** | `_execute_authenticated` returns empty list even when credentials pass |
| **facebook** | `search, profile, feed, groups` | facebook-scraper (35% auth); Search fallback | Auth-gated | 0% (AUTH_REQUIRED) | **0.0% (DISCONNECTED_GUARD)** | `_execute_authenticated` returns empty list even when credentials pass |
| **instagram** | `search, profile, posts, explore` | Instaloader (88% auth); Search fallback | Auth-gated | 0% (AUTH_REQUIRED) | **0.0% (DISCONNECTED_GUARD)** | `_execute_authenticated` returns empty list even when credentials pass |
| **boss** | `search_jobs, read_jd` | CDP browser session; Search fallback | Auth-gated | 0% (AUTH_REQUIRED) | **0.0% (DISCONNECTED_GUARD)** | `_execute_authenticated` returns empty list even when credentials pass |
| **xiaoyuzhou** | `transcribe` | Groq Whisper | Auth-gated | 0% (AUTH_REQUIRED) | **0.0% (DISCONNECTED_GUARD)** | `_execute_authenticated` returns empty list even when credentials pass |
