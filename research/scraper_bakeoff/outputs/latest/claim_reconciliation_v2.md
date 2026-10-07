# Aegis Protocol — Claim Reconciliation: Historic Projections vs. Ground Truth (V2)

Every past headline metric is reconciled below against the verified 740 raw observations.

| Headline Claim | Previous Bake-Off Value | Current Raw Value | Corrected Metric & Condition | Reproducible? | Root Cause Explanation |
|---|:---:|:---:|---|:---:|---|
| **Reddit Direct Retrieval** | 99.5% | 0.0% (0/50) | **0.0%** (`PRAW_ZERO_CONFIG`) | **NO (Unauth)** | Reddit permanently blocks unauthenticated public JSON endpoints with HTTP 403 in 2026. PRAW works only under `AUTHENTICATED` condition. |
| **Twitter Direct Retrieval** | 94.0% | 0.0% API / 76% Shell | **0.0% Direct Body / 76% Profile Shell** | **NO (Unauth)** | Direct unauth requests cannot fetch tweet threads or search results. twscrape requires an active account pool. |
| **Instagram Profile Scraping** | 88.0% | 0.0% (0/50) | **0.0%** (`Instaloader_UNAUTH`) | **NO** | Instagram redirects unauthenticated `web_profile_info` queries to `/accounts/login/` on 100% of calls. |
| **Scrapling Web Success** | 96.0% | 90.0% (45/50) | **90.0%** (Wilson CI [78.6%, 95.7%]) | **YES (Corrected)** | Scrapling bypasses Cloudflare where standard requests fail, but real web rate is 90%, not 96%. |
| **YouTube Video Extraction** | 98.0% | 92.0% (46/50) | **92.0%** (100% of available videos) | **YES** | 4 targets were deleted/unavailable on YouTube. For all valid targets, `yt-dlp` achieved 100% field extraction. |
| **GitHub Direct API** | 95.0% | 100.0% (25/25) | **100.0%** (Native REST) | **YES** | Public GitHub REST API operates cleanly with zero rate limits for the benchmark workload. |
| **Bilibili Native Retrieval** | 85.0% | 0.0% (0/20) | **0.0%** (100% `HTTP 412: Precondition Failed`) | **NO (Unauth)** | Bilibili requires cryptographic WBI query signatures (`w_rid`, `wts`). |
| **Overall Direct Retrieval** | 89.0% | 48.2% | **48.2% Measured Across All Platforms** | **NO** | Previous 89% assumed working credentials across all platforms. In zero-config reality, direct retrieval is 48.2%. |
| **Fallback Dependency** | 5.0% | 51.8% | **51.8% in Zero-Config Deployments** | **NO** | Search syndication fallback is required for ~52% of platforms when zero API keys are provisioned. |