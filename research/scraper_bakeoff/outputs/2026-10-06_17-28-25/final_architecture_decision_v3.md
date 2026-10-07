# Aegis Protocol — Final Architecture Decision (V3)


**Status**: APPROVED & EMPIRICALLY GROUNDED  

**Validation Timestamp**: 2026-10-06T17:28:31.564172  

**Dataset**: 340 Frozen Standardized Cases across 10 Platforms  


## 1. Core Architectural Questions Answered


### 1. Is the Specialist -> Scrapling -> Playwright -> Search cascade empirically better than current Aegis?

Policy D preserves the retrieval outcome of Policy B at 67.35% useful evidence while improving routing efficiency and reducing median latency. Relative to the current Aegis baseline (Policy A), it substantially increases first-party direct evidence from **7.35%** (25/340) to **20.59%** direct body (70/340) and **34.12%** direct + metadata (116/340) (continuity-corrected McNemar chi2 = 43.0222, exact p = 5.41e-11), while reducing search fallback dependency from **85.59%** down to **65.88%**. However, it does not improve the aggregate useful-evidence rate (67.35% vs 73.24%) under the current evaluation definition.


### 2. What is the actual case-level direct evidence rate?

- **First-Party Direct Body Content**: **20.59%** (70/340 cases: GitHub API 25 + Scrapling web 45)

- **First-Party Direct + Metadata**: **34.12%** (116/340 cases: GitHub API 25 + Scrapling web 45 + `yt-dlp` YouTube metadata 46)

- **Indexed / Search Syndication Fallback**: **65.88%** (224/340 cases: auth-walled social platforms + 5 web fallbacks + 4 deleted YouTube fallbacks)

- **Unresolved**: **0.0%** (0/340 cases: all cases successfully resolved through direct routes or search syndication fallback)


### 3. What is the actual fallback dependency in zero-config deployments?

Policy D has 65.9% fallback dependency in zero-config mode and 0% unresolved benchmark cases. In the absence of credentials, Reddit, Twitter, Instagram, TikTok, Facebook, LinkedIn, and Bilibili cannot be scraped directly without encountering authentication walls. Search fallback provides the necessary syndication and indexing, resolving all fallback cases with zero unresolvable drops. The 4 deleted/geo-blocked YouTube videos were also successfully resolved through search syndication fallback.


### 4. Which platforms benefit most from specialist adapters?

**YouTube** benefits most. In-process `yt-dlp` import achieves 92.0% direct retrieval success (46/50) with 100% metadata field completeness on available videos, and eliminates 848ms of CLI subprocess overhead.


### 5. Which platforms should remain search-fallback-first?

**Reddit, Instagram, Bilibili, TikTok, Facebook, and LinkedIn** must remain search-fallback-first in zero-config deployments. Unauthenticated direct scrapers encounter 100% login walls or HTTP 412/403 blocks. Bypassing doomed direct scraping requests via a zero-config credential gate saves 44 wasted requests per 100 social cases.


### 6. Is Scrapling actually the best first generic web tier?

**YES (EMPIRICALLY VERIFIED)**. Scrapling HTTP achieved 90.0% availability (45/50) with 698ms P50 latency and 7MB RSS delta, bypassing Cloudflare anti-bot checks where standard urllib failed (80.0%) and running 4x faster than Playwright.


### 7. How should YouTube retrieval be evaluated across tasks?

YouTube evaluation must distinguish between metadata retrieval and semantic claim evidence. The benchmark contains `VIDEO_METADATA` and `VIDEO_SEARCH` tasks:

- **Metadata Transport Success**: 46/50 = 92.0%

- **Metadata Field Completeness**: 100% on available videos (46/46) across title, channel, description, upload date, and duration.

- **Search Fallback Rate**: 4/50 = 8.0% (for deleted or region-restricted videos).

- **Task-Specific Useful Evidence**: 10/50 = 20.0% when evaluated strictly against generic semantic claim support criteria.

**Crucial Distinction**: 46/50 successful metadata retrievals does NOT automatically mean 46/50 'useful claim evidence'. Video metadata retrieval fulfills technical metadata tasks completely, but requires dedicated transcript extraction for text claim verification.


### 8. Is Playwright actually necessary as a fallback?

Playwright is retained as a secondary rescue capability for JS/client-side rendered pages, but it was not selected as the final route in this frozen 340-case benchmark (0/340 selected final routes). Do NOT call Playwright empirically necessary based solely on this benchmark. Its invocation incurs a 420ms startup penalty and ~85MB RSS memory overhead, so it must remain strictly secondary to Scrapling HTTP.


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

Policy D is the preferred production routing policy because it preserves the retrieval outcomes of Policy B while reducing average route attempts and median latency. Relative to the current Aegis baseline, it substantially increases first-party direct evidence and reduces fallback dependency, but it does not improve the aggregate useful-evidence rate.


**Baseline Comparison**:

- **Current Policy A**: useful = 73.2%, direct body = 7.4%, fallback = 85.6%

- **Policy D**: useful = 67.3%, direct body = 20.6%, direct + metadata = 34.1%, fallback = 65.9%


**Frozen Production Pipeline**:

NativeRouter: GitHub API (Native REST) -> YouTube (yt-dlp in-process) -> General Web (Scrapling HTTP -> Playwright secondary rescue on JS challenge) -> Social Walled Gardens (Zero-Config Credential Gate -> Bing Search Fallback) -> EvidenceFragment -> RelevanceGate -> ResearchEngine.


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
