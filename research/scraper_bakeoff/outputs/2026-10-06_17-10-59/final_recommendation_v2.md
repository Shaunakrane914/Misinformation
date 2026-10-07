# Aegis Protocol — Final Retrieval Architecture Recommendations (V2)

Derived strictly from empirical head-to-head validation and raw observation records.

## 1. Platform Decision Summary

| Platform | Primary Engine | Secondary Engine | Fallback Tier | Verdict Classification |
|---|---|---|---|---|
| **General Web** | **Scrapling HTTP (`Fetcher`)** | Playwright Headless | Search Fallback (Bing) | **PRIMARY** (Best latency, low RAM, TLS bypass) |
| **GitHub** | **Native REST API (`api.github.com`)** | Web Scraper | Search Fallback | **PRIMARY** (100% success, sub-500ms, zero extra deps) |
| **YouTube** | **`yt-dlp` In-Process Import** | `yt-dlp` CLI Subprocess | Search Fallback | **PRIMARY** (Subprocess overhead avoided, 100% field completeness) |
| **Reddit** | **Search Fallback (`site:reddit.com`)** | PRAW (Authenticated only) | N/A | **DUAL CASCADE** (Direct unauth is 0% / 100% 403) |
| **Twitter / X** | **Search Fallback (`site:x.com`)** | Direct Profile Header | `twscrape` (Pool only) | **DUAL CASCADE** (Direct HTTP gets bio only; syndication gets context) |
| **Instagram** | **Search Fallback (`site:instagram.com`)** | N/A | Playwright Auth Session | **FALLBACK** (Unauth Instaloader is 0% / login wall) |
| **TikTok** | **Search Fallback (`site:tiktok.com`)** | Direct HTTP (Card only) | Mobile API (ms_token) | **FALLBACK** (Deep comments require session) |
| **Facebook** | **Search Fallback (`site:facebook.com`)** | N/A | N/A | **FALLBACK** (`facebook-scraper` is broken/deprecated) |
| **Bilibili** | **Search Fallback (`site:bilibili.com`)** | Web Reader | WBI Signed Client | **FALLBACK** (Unauth direct API is 0% / HTTP 412) |
| **LinkedIn** | **Search Fallback (`site:linkedin.com`)** | N/A | Playwright Session Cookie | **FALLBACK** (Unauthenticated is gated by auth-wall) |

## 2. Hard Architectural Invariants for Aegis Protocol

1. **Do Not Trust Unauthenticated Social Scrapers in Production**: Direct scrapers for Reddit, Instagram, and Bilibili fail 100% without credentials or signatures. Aegis must never rely on direct zero-config scrapers as single points of failure.
2. **Adopt Scrapling for General Web**: Scrapling HTTP outperforms both urllib and Playwright on availability (90.0% vs 80.0%), memory footprint (7MB RSS delta vs 35MB for BeautifulSoup), and execution speed (698ms vs 2,778ms).
3. **Embed `yt-dlp` In-Process**: Do not invoke `yt-dlp` via CLI subprocess. In-process Python import eliminates 848ms of subprocess overhead per call while extracting identical metadata.