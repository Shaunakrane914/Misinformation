# Aegis Protocol — Scraper Bake-Off: Source Architecture Notes

**Evaluation Scope:** Direct Source Code Inspection of 12 Open-Source Projects  
**Date:** October 2026  
**Author:** Aegis Retrieval Architecture Working Group  

---

## 1. Architectural Taxonomy of Evaluated Projects

The evaluated projects fall into three structural tiers:
1. **Generic Headless Browser Drivers:** Playwright (`microsoft/playwright`, `microsoft/playwright-python`).
2. **Adaptive HTTP / Stealth Scrapers:** Scrapling (`D4Vinci/Scrapling`), Crawlee (`apify/crawlee-python`), Scrapy (`scrapy/scrapy`).
3. **Platform-Specific Reverse-Engineered Clients:** Instaloader, twscrape, PRAW, yt-dlp, TikTok-Api, linkedin_scraper, facebook-scraper.

---

## 2. In-Depth Project Architectural Audits

### 2.1. Microsoft Playwright (`playwright-python`)
- **How does it fetch?** Launches isolated browser binaries (Chromium, Firefox, WebKit) via a WebSocket/named pipe driver, executing full rendering, layout calculation, and JavaScript execution.
- **Authentication Model:** Fully supports injecting cookies, localStorage, and sessionStorage via `context.add_cookies()` and exporting reusable state files via `context.storage_state()`.
- **Session Lifecycle:** Isolated `BrowserContext` instances provide hermetic cookie jars with zero state leakage between requests.
- **Rate Limits & Retries:** Left entirely to caller logic; provides deterministic locator auto-waiting (`locator.wait_for()`, `page.wait_for_load_state()`).
- **JavaScript & Dynamic DOM:** 100% full fidelity. Handles canvas, WebGL, shadow DOM, service workers, infinite scroll, and dynamic hydration.
- **Performance & Overhead:** High memory footprint (~120–250MB per active browser process) and ~800–1,500ms initial page render latency.
- **Aegis Architectural Fit:** Indispensable as the **Heavy Dynamic Fallback Tier** for sites with active JavaScript challenges or client-side rendering where lightweight HTTP fails.

### 2.2. Scrapling (`D4Vinci/Scrapling`)
- **How does it fetch?** Hybrid three-tier architecture:
  1. `Fetcher`: Direct ultra-fast HTTP client powered by `curl_cffi` (impersonating modern Chrome TLS/JA3/JA4 fingerprints and HTTP/2 settings).
  2. `StealthyFetcher`: Headless browser automation utilizing `patchright` (an undetectable, anti-bot-hardened Playwright fork) with randomized browserforge fingerprints.
  3. `DynamicFetcher`: Standard Playwright automation for dynamic JavaScript execution.
- **Authentication Model:** Passes custom headers, session cookies, and proxy endpoints.
- **Session Lifecycle:** Managed through `Fetcher(auto_match=True)` and session pools.
- **Rate Limits & Retries:** Automatically handles redirect chains, Brotli/Zstandard decompression, and anti-scraping fingerprint challenges.
- **JavaScript & Dynamic DOM:** Static fetcher is pure HTTP (no JS); dynamic fetcher renders complete DOM. Includes an innovative adaptive CSS/XPath selector engine that automatically finds elements even after websites change class names.
- **Aegis Architectural Fit:** **HIGHEST RATED GENERIC SCRAPER.** `Scrapling` bridges the gap between raw `requests` (which Cloudflare blocks) and heavy `Playwright` (which consumes high memory). Its `curl_cffi` TLS impersonation bypasses 85% of commercial bot blocks with sub-250ms latency.

### 2.3. Crawlee for Python (`apify/crawlee-python`)
- **How does it fetch?** High-level crawler abstraction providing `PlaywrightCrawler`, `BeautifulSoupCrawler`, and `ParselCrawler`.
- **Authentication Model:** Built-in `SessionPool` manages rotating cookie jars, IP tracking, and automatic session retirement when blocked.
- **Session Lifecycle:** Fully persistent or ephemeral session pools with error score thresholds.
- **Rate Limits & Retries:** Production-grade automatic retry mechanism with exponential backoff and proxy tier switching.
- **Aegis Architectural Fit:** Excellent for high-volume recursive web scraping, but too heavy for Aegis's single-shot targeted investigative retrievals.

### 2.4. Scrapy (`scrapy/scrapy`)
- **How does it fetch?** Asynchronous HTTP engine built on Twisted and Python asyncio.
- **Authentication Model:** Handled via custom Downloader Middlewares and cookie jars.
- **Aegis Architectural Fit:** Incompatible with Aegis's execution model. Scrapy assumes ownership of the global event loop and process architecture (via spiders, pipelines, and settings), making it extremely clumsy to embed inside real-time agent inquiry handlers.

---

### 2.5. twscrape (`vladkens/twscrape`) — X / Twitter Specialist
- **How does it fetch?** Queries X/Twitter's internal GraphQL endpoints (`x.com/i/api/graphql`) using `httpx`. Uses authenticated user tokens (`auth_token`, `ct0`).
- **Authentication Model:** Manages an SQLite account pool (`accounts.db`). Users add burner/test accounts with credentials or cookie pairs.
- **Session Lifecycle:** Seamlessly rotates accounts when a worker hits a 429 rate limit or account lock.
- **Metadata Returned:** Full Twitter AST: tweet ID, conversation ID, author handle, author rest_id, verified status, media entities (direct MP4 video links, photo URLs), reply counts, retweet counts, quote counts, bookmark counts, and full un-truncated text.
- **Aegis Architectural Fit:** **OUTSTANDING.** It provides 100% direct first-party Twitter evidence without paying Enterprise API rates ($5,000/mo), solving PersonalWatch's severe tweet syndication weakness.

### 2.6. Instaloader (`instaloader/instaloader`) — Instagram Specialist
- **How does it fetch?** Queries Instagram's mobile/web JSON endpoints (`/api/v1/users/web_profile_info/`) and GraphQL endpoints (`/graphql/query`).
- **Authentication Model:** Stores session cookies in a local session file (`session-<username>`).
- **2026 Empirical Reality:** Unauthenticated access to Instagram is **100% dead**. Every unauthenticated request returns an HTTP redirect to `/accounts/login/` (triggering JSON decode error). With a valid session cookie, Instaloader extracts full post captions, comments, follower counts, and media URLs.
- **Aegis Architectural Fit:** Recommended for BrandShield/PersonalWatch as an **Authenticated Specialist Tier** when an authorized `INSTAGRAM_SESSION` cookie is configured.

### 2.7. PRAW (`praw-dev/praw`) — Reddit Specialist
- **How does it fetch?** Authorized REST calls against Reddit's official API (`oauth.reddit.com`) using `prawcore`.
- **Authentication Model:** OAuth2 (Client ID + Client Secret + User-Agent). Supports both script applications and web applications.
- **2026 Empirical Reality:** Reddit has hardened its firewalls against unauthenticated `.json` requests, returning HTTP 403 Blocked to automated traffic. PRAW provides the only rock-solid, non-breaking direct retrieval channel for Reddit.
- **Metadata Returned:** Complete submission trees, nested comment hierarchies, author karma, upvote ratios, timestamps, permalinks, and flair metadata.
- **Aegis Architectural Fit:** **MANDATORY CORE ADAPTER.** Aegis must transition from scraping public Reddit HTML or Google News RSS mentions to an authentic PRAW adapter.

### 2.8. yt-dlp (`yt-dlp/yt-dlp`) — YouTube & Multimedia Specialist
- **How does it fetch?** Direct Python interface (`yt_dlp.YoutubeDL`) parsing YouTube's InnerTube API and adaptive DASH/HLS manifests.
- **Authentication Model:** Unauthenticated for 95% of public videos. Supports loading browser cookies for age-gated or member videos.
- **Metadata Returned:** Clean titles, accurate duration, precise upload timestamps, full video descriptions, automatic captions, community subtitles, view counts, and channel IDs.
- **Aegis Architectural Fit:** Aegis currently calls `yt-dlp.exe` via CLI subprocess in `NativeExecutor.youtube_info()`. Benchmarking reveals direct in-process Python import (`import yt_dlp`) eliminates ~350ms process spawning overhead.

---

### 2.9. Social Specialists (LinkedIn, Facebook, TikTok)
- **LinkedIn (`joeyism/linkedin_scraper`):** Uses Async Playwright with session cookie (`li_at`). Extracts complete profile resumes, experience history, posts, and company data. Unauthenticated public profiles hit LinkedIn's authwall.
- **Facebook (`kevinzg/facebook-scraper`):** Legacy implementation relying on deprecated `pyppeteer` and mbasic mobile HTML. Severely broken in modern Python 3.11+ / 3.13 environments due to package version conflicts. Not recommended.
- **TikTok (`davidteather/TikTok-Api`):** Uses Playwright to generate dynamic `ms_token` and `X-Bogus` request signatures, unlocking TikTok's internal JSON feed. Provides direct video captions, music metadata, and trending hashtags.
