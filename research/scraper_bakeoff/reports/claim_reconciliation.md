# Aegis Protocol — Claim Reconciliation: Bake-Off Projections vs Ground Truth

This document reconciles earlier multi-repository scraper bake-off projections with empirical results from the full-scale live benchmark.

| Channel / Claim | Previous Bake-Off Projection | Empirical Ground Truth (Live Benchmark) | Statistical Delta | Root Cause Reconciliation |
|---|---|---|---|---|
| **Reddit Direct Unauth** | 99.5% Success (Projected via PRAW/old RSS) | **0.0% Success** (100% `HTTP_403: Blocked`) | -99.5% | Reddit permanently blocked unauthenticated public JSON API in 2026. Only OAuth2 or syndication works. |
| **X / Twitter Direct** | 94.0% Direct Retrieval | **0.0% Direct API / 42.0% Profile Shell** | -52.0% to -94.0% | Public timeline JSON endpoints require session authentication (`ct0`/`auth_token`). Direct HTTP gets only static shell; twscrape requires account pool. |
| **Instagram Unauthenticated** | 88.0% Profile Ingestion | **0.0% Direct Profile JSON** (100% Login Redirect) | -88.0% | Instagram redirects unauthenticated `web_profile_info` requests to `/accounts/login/` on 100% of calls. |
| **General Web Scraping** | 92.0% Success | **96.0% Success** (Scrapling HTTP) | +4.0% | Scrapling TLS/JA4 fingerprint impersonation (`curl_cffi`) reliably bypasses standard Cloudflare bot-guards where urllib fails. |
| **YouTube Extraction** | 98.0% Direct Metadata | **98.0% Success** (`yt-dlp` import) | 0.0% | `yt-dlp` direct Python extraction is confirmed rock-solid for video metadata without browser overhead. |
| **GitHub Direct** | 95.0% Direct API | **100.0% Success** (Native REST) | +5.0% | Public GitHub API operates cleanly without tokens within standard IP rate limits. |
| **Bilibili Native** | 85.0% Direct Retrieval | **0.0% Unauth API** (`HTTP 412: Precondition Failed`) | -85.0% | Bilibili requires WBI signed query tokens or browser cookies; unauthenticated direct API is blocked. |
