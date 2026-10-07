# Aegis Protocol — Final Architecture Decision (V3)


**Status**: APPROVED & EMPIRICALLY GROUNDED  

**Validation Timestamp**: 2026-10-06T17:17:12.556447  

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


### 7. Is Playwright necessary as a fallback?

**YES, AS SECONDARY ONLY**. Playwright should only be invoked when Scrapling detects client-side rendering requirements, avoiding unnecessary 420ms startup costs and browser child processes on static pages.


### 8. Which current Aegis readers should be deprecated?

Public Jina Reader (`r.jina.ai`) should be deprecated as a primary tier due to severe rate-limiting (16/50 `RATE_LIMITED_429` errors in benchmark testing). Replace with Scrapling HTTP.


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
