# Aegis Protocol — Architectural Decision Record (V2)

**Status**: APPROVED BASED ON AUDITED EMPIRICAL MEASUREMENTS  
**Date**: 2026-10-06  

## 1. Concrete Technology Selection Per Platform

1. **General Web** -> **Scrapling HTTP (`Fetcher`)**
   - *Evidence*: 90.0% availability (vs 80.0% for requests and Playwright), 698ms P50 latency, 7MB memory RSS delta. Statistically superior to plain requests under McNemar's test.

2. **Dynamic / JS-Heavy Web** -> **Playwright Headless (Secondary Fallback Only)**
   - *Evidence*: 420ms startup cost, 2,778ms P50 latency. Only invoked when Scrapling detects client-side rendering requirements.

3. **Reddit** -> **Dual-Tier: PRAW (if OAuth keys present) -> Search Syndication Fallback (`site:reddit.com`)**
   - *Evidence*: Unauthenticated REST is 0% (HTTP 403). Fallback delivers 100% availability with 490ms P50 latency.

4. **X / Twitter** -> **Dual-Tier: Direct Profile Card -> Search Syndication Fallback (`site:x.com`)**
   - *Evidence*: Direct HTTP gets author bio/follower metadata without timeline. Search fallback retrieves post context.

5. **YouTube** -> **`yt-dlp` In-Process Python Import**
   - *Evidence*: 92.0% overall success (100% of live videos), 100% metadata completeness, eliminates 848ms CLI subprocess spawning overhead.

6. **GitHub** -> **Native REST API (`api.github.com`)**
   - *Evidence*: 100.0% availability, 476ms P50 latency, zero external scraping dependencies required.

7. **Instagram, TikTok, Facebook, LinkedIn, Bilibili** -> **Search Syndication Fallback as Primary Zero-Config Route**
   - *Evidence*: Unauthenticated direct scrapers are 100% blocked by auth walls or cryptographic signatures in 2026.

## 2. Target Retrieval Cascade

```
                    AEGIS RETRIEVAL INGESTION
                                │
                           NativeRouter
                                │
         ┌──────────────────────┼──────────────────────┐
         ▼                      ▼                      ▼
     Native APIs        Specialist Adapters         Web Stack
    (GitHub, etc.)     (yt-dlp in-process)              │
         │              [PRAW / twscrape]               ▼
         │               (Credentialed Only)        Scrapling HTTP
         │                      │                   (curl_cffi TLS)
         │                      │                       │
         │                      ▼ (on Auth Wall)        ▼ (on JS Shell)
         │               Search Fallback            Playwright
         │               (site:platform.com)        (Secondary)
         └──────────────────────┼───────────────────────┘
                                ▼
                         EvidenceFragment
                                ▼
                          RelevanceGate
                                ▼
                         ResearchEngine
```
