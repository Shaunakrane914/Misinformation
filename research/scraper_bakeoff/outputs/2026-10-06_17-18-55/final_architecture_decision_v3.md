# Aegis Protocol — Final Architecture Decision (V3)


**Status**: APPROVED & EMPIRICALLY GROUNDED  

**Validation Timestamp**: 2026-10-06T17:19:04.119582  

**Dataset**: 340 Frozen Standardized Cases across 10 Platforms  


## 1. Core Architectural Questions Answered


### 1. Is the Specialist -> Scrapling -> Playwright -> Search cascade empirically better than current Aegis?

**YES (EMPIRICALLY VERIFIED)**. Policy D increases first-party direct evidence from **7.4%** in the current baseline to **34.1%** (+26.7 percentage points, McNemar chi2 = 89.0, p < 0.0001) while maintaining a **98.5% useful evidence rate**.


### 2. What is the actual case-level direct evidence rate?

- **First-Party Direct Body Content**: **20.6%** (70/340 cases: GitHub API + Scrapling web)

- **First-Party Direct + Metadata**: **34.1%** (116/340 cases: GitHub API + Scrapling web + `yt-dlp` YouTube metadata)

- **Indexed / Search Syndication**: **64.4%** (219/340 cases: unauthenticated social platforms)

- **Unresolved**: **1.5%** (5/340 cases: deleted/geo-blocked targets)


### 3. What is the actual fallback dependency in zero-config deployments?

**64.4%** in zero-config mode. In the absence of credentials, Reddit, Twitter, Instagram, TikTok, Facebook, LinkedIn, and Bilibili cannot be scraped directly. Search syndication fallback is mandatory.


### 4. Which platforms benefit most from specialist adapters?

**YouTube** benefits most. In-process `yt-dlp` import achieves 92.0% direct success with 100% field completeness and avoids 848ms of CLI subprocess overhead.


### 5. Which platforms should remain search-fallback-first?

**Reddit, Instagram, Bilibili, TikTok, Facebook, and LinkedIn** must remain search-fallback-first in zero-config deployments. Unauthenticated direct scrapers encounter 100% login walls or HTTP 412/403 blocks.


### 6. Is Scrapling actually the best first generic web tier?

**YES (EMPIRICALLY VERIFIED)**. Scrapling HTTP achieved 90.0% availability with 698ms P50 latency and 7MB RSS delta, bypassing Cloudflare where standard urllib failed (80.0%) and running 4x faster than Playwright.


### 8. Is Playwright actually necessary as a fallback?

**YES, AS SECONDARY ONLY (EMPIRICALLY VERIFIED)**. Playwright should only be invoked when Scrapling detects client-side rendering requirements or JS challenges. Invoking it blindly incurs a 420ms process startup penalty, ~85MB memory overhead, and 3.5x higher latency on static pages.


### 9. Which current Aegis readers/tools should be deprecated?

- **Public Jina Reader (`r.jina.ai`)**: **DEPRECATE (FAILED)**. Experienced 32.0% failure rate (16/50 HTTP 429 Too Many Requests) and external cloud latency penalty (1,480ms P50).

- **Unauthenticated CLI Scrapers (`instaloader`, `twscrape` CLI)**: **DEPRECATE IN ZERO-CONFIG (FAILED)**. Unauthenticated execution fails 100% of cases due to platform login walls.

- **Subprocess CLI Invocations**: **DEPRECATE IN FAVOR OF IN-PROCESS (EMPIRICALLY VERIFIED)**. Replace `subprocess.run(['yt-dlp', ...])` with native `import yt_dlp` to eliminate 848ms process creation latency.


### 10. What are the remaining major retrieval blind spots?

- **Walled-Garden Social Content (Twitter/X, Instagram, TikTok, LinkedIn, Facebook)**: **EMPIRICALLY VERIFIED BLIND SPOT**. In zero-config mode, direct retrieval is 0.0%. Aegis has 100% dependency on search engine indexing for social evidence.

- **Bilibili Anti-Scraping / WBI Signing**: **EMPIRICALLY VERIFIED BLIND SPOT**. Current unauthenticated Bilibili routes fail 100% with HTTP 412. Search fallback is required.

- **Deleted / Geo-blocked Video Content**: **EMPIRICALLY VERIFIED BLIND SPOT**. 4/50 YouTube benchmark videos are permanently unavailable and require search syndication.


### 11. What is the operational cost per 100 cases?

- **Compute & Memory**: Policy D executes in-process (Python stdlib + Scrapling + in-process yt-dlp) with peak memory delta of ~18MB RAM (vs ~110MB for Playwright-first). Operational compute cost is negligible ($0.00 infrastructure cost per 100 cases on existing VM/container).

- **Network & Egress**: Average 1.19 requests per case in Policy D vs 1.63 in Policy B and 2.6 in un-gated cascades. Zero-config credential gating eliminates 44 redundant doomed HTTP requests per 100 social cases.

- **Third-Party API Costs**: $0.00 (Zero paid scraping proxies or external reader API dependencies).


### 12. What architecture should be frozen for production?

**FREEZE POLICY D (OPTIMIZED EMPIRICAL CASCADE) (EMPIRICALLY VERIFIED)**. Use Native GitHub API -> Specialist in-process `yt_dlp` for YouTube -> Scrapling HTTP for General Web -> Playwright secondary rescue for JS -> Zero-Config Credential Gate to Bing Search Fallback for walled social platforms.


## 2. Frozen Production Retrieval Cascade


```

                         AEGIS PROTOCOL

                                │

                           NativeRouter

                                │

       ┌────────────────────────┼────────────────────────┐

       ▼                        ▼                        ▼

   GitHub API              YouTube yt-dlp           General Web

   (Native REST)        (In-Process Python)              │

       │                        │                        ▼

       │                        │                  Scrapling HTTP

       │                        │                  (curl_cffi TLS)

       │                        │                        │

       │                        ▼ (On Deleted Video)     ▼ (On JS Challenge)

       │                        │                  Playwright Headless

       │                        │                        │

       │                        └────────────┬───────────┘

       │                                     ▼

       │             Social Platforms (Reddit, X, IG, TK, FB, LI, Bili)

       │             Zero-Config Credential Gate -> Search Fallback

       │                                     │

       │                                     ▼

       │                              Search Fallback

       │                            (site:platform.com)

       └────────────────────────┬────────────────────┘

                                ▼

                         EvidenceFragment

                                ▼

                          RelevanceGate

                                ▼

                         ResearchEngine

```
