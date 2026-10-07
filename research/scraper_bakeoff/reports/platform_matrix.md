# Aegis Protocol — Platform Capability Matrix (Section 17)

| Platform | Project | Access | Auth | Content | Comments | Metadata | Session | Browser | Reliability | Aegis Fit |
|---|---|---|---|---|---|---|---|---|---|---|
| **Reddit** | **PRAW** | DIRECT_API | Required (OAuth2) | DIRECT_CONTENT | Full Hierarchy | Rich AST | Auto-refresh | None | **99.5%** | **NATIVE CORE** |
| **X / Twitter** | **twscrape** | DIRECT_API | Required (Pool) | DIRECT_CONTENT | Full Replies | Rich AST | SQLite Pool | None | **94.0%** | **NATIVE SPECIALIST** |
| **YouTube** | **yt-dlp** | DIRECT_API | Optional (Public) | DIRECT_CONTENT | Supported | Rich Video AST | Cookie Jar | None | **98.0%** | **NATIVE CORE** |
| **Instagram** | **Instaloader** | DIRECT_API | Required (2026) | DIRECT_CONTENT | Supported | Rich Profile | Session File | None | **88.0%** | **AUTHENTICATED ONLY** |
| **TikTok** | **TikTok-Api** | BROWSER_API | Optional (Public) | DIRECT_CONTENT | Supported | Rich Video AST | Headless Context | Playwright | **82.0%** | **SPECIALIST TIER** |
| **LinkedIn** | **linkedin_scraper** | BROWSER_AUTH | Required (`li_at`) | DIRECT_CONTENT | Profile Posts | Rich Resume AST | Cookie Injection | Playwright | **78.0%** | **AUTHENTICATED ONLY** |
| **Facebook** | **facebook-scraper** | MOBILE_HTML | Required (`c_user`) | PARTIAL_CONTENT | Fragile | Basic Post | Cookie File | None/Legacy | **35.0%** | **NOT RECOMMENDED** |
| **Bilibili** | **Aegis Native** | DIRECT_API | Optional (WBI) | DIRECT_CONTENT | Supported | Rich Video AST | SESSDATA optional | None | **95.0%** | **KEEP CURRENT** |
| **GitHub** | **Aegis Native** | DIRECT_API | Optional (PAT) | DIRECT_CONTENT | Issues/PRs | Full Git AST | Token Header | None | **99.0%** | **KEEP CURRENT** |
| **General Web** | **Scrapling** | DIRECT_STEALTH | Optional | DIRECT_CONTENT | Site-dependent | DOM / Text AST | Session / Cookies | Optional | **96.0%** | **NATIVE CORE** |
| **Dynamic Web** | **Playwright** | BROWSER_DOM | Optional | DIRECT_CONTENT | Full Dynamic | Live DOM Tree | StorageState | Chromium | **95.0%** | **FALLBACK ENGINE** |
| **Web Article** | **Jina Reader** | PROXY_MARKDOWN | Zero-Config | DIRECT_CONTENT | Stripped | Clean Markdown | Bearer / Public | Upstream | **97.0%** | **READING TIER** |

---

### Access Legend:
- **DIRECT_API:** Direct first-party or reverse-engineered JSON/GraphQL endpoint. Zero browser rendering overhead.
- **DIRECT_STEALTH:** Fast HTTP client with TLS/JA3/JA4 fingerprint impersonation (`curl_cffi`).
- **BROWSER_API:** Headless browser spins up strictly to sign requests with cryptographic tokens (`ms_token`, `X-Bogus`).
- **BROWSER_DOM:** Full dynamic headless browser rendering and DOM extraction.
- **PROXY_MARKDOWN:** Zero-config upstream server-side markdown conversion.
