# Aegis Protocol — Verified 16-Channel Capability Matrix

**Audit Run ID:** `2026-10-10_12-45-00`  
**Date:** October 10, 2026  
**Standard:** Measured Real-Network Reality vs Advertised Capability Claims

---

| # | Channel | Advertised Operations | Tested Operations | Active Backend Selected | Direct Scraping Success Rate | Content Quality | Verification Status |
|---|---|---|---|---|---|---|---|
| 1 | **web** | read | read, read_bot_protected | Scrapling HTTP (curl_cffi) | 50.0% (1/2 direct, 1 Cloudflare blocked) | Full Article Body (up to 136k chars) | **VERIFIED_WORKING** |
| 2 | **web_search** | search | search | Bing Search HTTP + URL Decoder | 100.0% (1/1 indexed) | Search Index Snippet (120–180 chars) | **VERIFIED_WORKING** (Indexed) |
| 3 | **github** | search, read, issues, prs, releases, commits | search, read, issues | GitHub REST API (gh CLI failed) | 50.0% (REST API works, gh CLI parameter bug) | Structured Repository & Issue Metadata | **PARTIALLY_WORKING** (REST fallback active) |
| 4 | **youtube** | search, read, transcript, comments | search, read, transcript, comments | yt-dlp (in-process + CLI) | 75.0% (3/4 ops work; comments missing) | Full Transcripts (4,017 chars) & Video Metadata | **VERIFIED_WORKING** (Comments unimpl.) |
| 5 | **bilibili** | search, read, hot, rank | search, read, hot, rank | Bilibili Public Search API | 25.0% (1/4 ops work; read/hot/rank unimpl.) | Structured Video Search Results | **PARTIALLY_WORKING** (Search only) |
| 6 | **v2ex** | hot, latest, search, topic, replies | hot, latest, replies | V2EX Public REST API | 100.0% (3/3 ops work) | Full Discussion Threads & Replies | **VERIFIED_WORKING** |
| 7 | **rss** | read | read | feedparser | 100.0% (1/1 ops work) | Structured News & Press Release Feeds | **VERIFIED_WORKING** |
| 8 | **reddit** | search, read, comments | search, post, search_router | Bing Search Index Fallback | 0.0% Direct (Arctic Shift down; 100% indexed fallback) | Search Index Snippet (150–250 chars) | **FALLBACK_ONLY** (Arctic Shift down) |
| 9 | **twitter** | search, read, status, profile, feed | profile, status, search_router | FxTwitter (profile/status) + Bing Index (search) | 66.7% (2/3 ops work; profile is shell, search is indexed) | Profile Shell & Direct Status Content | **PARTIALLY_WORKING** (Profile/Status work) |
| 10 | **xueqiu** | search, quotes, hot_posts, hot_stocks | search | OpenCLI (AUTH_REQUIRED) | 0.0% (Requires XUEQIU_COOKIE) | N/A (Blocked at auth gate) | **AUTH_GATED** |
| 11 | **linkedin** | profile, company, jobs, read | profile | mcp-server-linkedin (AUTH_REQUIRED) | 0.0% (Requires LINKEDIN_COOKIE) | N/A (Blocked at auth gate) | **AUTH_GATED** |
| 12 | **xiaohongshu** | search, read, comments, feed | search | OpenCLI (AUTH_REQUIRED) | 0.0% (Requires XIAOHONGSHU_COOKIE) | N/A (Blocked at auth gate) | **AUTH_GATED** |
| 13 | **facebook** | search, profile, feed, groups | profile | OpenCLI (AUTH_REQUIRED) | 0.0% (Direct HTTP returns empty JS shell) | N/A (Login Wall) | **AUTH_GATED** |
| 14 | **instagram** | search, profile, posts, explore | profile | OpenCLI (AUTH_REQUIRED) | 0.0% (Direct HTTP returns login redirect) | N/A (Login Wall) | **AUTH_GATED** |
| 15 | **boss** | search_jobs, read_jd | search_jobs | boss-agent-cli (AUTH_REQUIRED) | 0.0% (Requires BOSS_CDP_PORT) | N/A (CDP Session Required) | **AUTH_GATED** |
| 16 | **xiaoyuzhou** | transcribe | transcribe | groq-whisper (AUTH_REQUIRED) | 0.0% (Requires GROQ_API_KEY) | N/A (API Key Required) | **AUTH_GATED** |
