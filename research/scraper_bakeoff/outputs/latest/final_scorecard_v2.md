# Aegis Protocol — Full-Scale Retrieval Benchmark: Final Scorecard (V2)

**Generated**: 2026-10-06T17:10:59.153942  
**Source Data**: Canonical raw observations from `all_observations_fullscale_live_1791285451.json` (740 live tasks)  
**Hardware Platform**: 13th Gen Intel Core i5-13450HX (16 logical threads, 16GB RAM)  

## 1. Measured Performance Scorecard Across Platforms & Conditions

| Candidate | Platform | Condition | N | Success | CI95 | Direct Success | Relevance | Completeness | P50 (ms) | P95 (ms) | Failure |
|---|---|---|---:|---:|---|---:|---:|---:|---:|---:|---:|
| **`aegis_native_bilibili`** | `bilibili` | `ZERO_CONFIG` | 20 | 0.0% | [0.0%, 16.1%] | 0.0% | 0.0 | 0.0 | 859.53 | 1043.97 | HTTP_ERROR_412:20 |
| **`facebook_live_http`** | `facebook` | `PUBLIC_HTTP` | 15 | 100.0% | [79.6%, 100.0%] | 0.0% | 0.0 | 50.0 | 1495.08 | 1774.21 | None |
| **`scrapling_http`** | `general_web` | `PUBLIC_HTTP` | 50 | 90.0% | [78.6%, 95.7%] | 90.0% | 2.11 | 91.1 | 697.88 | 1989.23 | UNKNOWN_FAILURE:3, HTTP_ERROR_403:2 |
| **`beautifulsoup_requests`** | `general_web` | `PUBLIC_HTTP` | 50 | 80.0% | [67.0%, 88.8%] | 80.0% | 2.1 | 87.8 | 866.9 | 1973.42 | HTTP_ERROR_403:7, UNKNOWN_FAILURE:3 |
| **`playwright_headless`** | `general_web` | `PUBLIC_BROWSER` | 50 | 80.0% | [67.0%, 88.8%] | 80.0% | 2.1 | 90.5 | 2778.48 | 4730.95 | HTTP_ERROR_403:7, UNKNOWN_FAILURE:3 |
| **`current_aegis_reader`** | `general_web` | `ZERO_CONFIG` | 50 | 48.0% | [34.8%, 61.5%] | 48.0% | 2.5 | 97.1 | 1485.68 | 6438.68 | HTTP_ERROR_403:7, UNKNOWN_FAILURE:1, RATE_LIMITED_429:16, TIMEOUT:2 |
| **`aegis_native_github`** | `github` | `ZERO_CONFIG` | 25 | 100.0% | [86.7%, 100.0%] | 100.0% | 2.92 | 75.2 | 476.54 | 1443.46 | None |
| **`instagram_bing_fallback`** | `instagram` | `ZERO_CONFIG` | 50 | 100.0% | [92.9%, 100.0%] | 0.0% | 1.9 | 77.6 | 381.18 | 539.55 | None |
| **`instaloader_unauth`** | `instagram` | `ZERO_CONFIG` | 50 | 0.0% | [0.0%, 7.1%] | 0.0% | 0.0 | 0.0 | 1210.64 | 3728.36 | AUTH_REQUIRED:50 |
| **`linkedin_live_http`** | `linkedin` | `ZERO_CONFIG` | 15 | 0.0% | [0.0%, 20.4%] | 0.0% | 0.0 | 0.0 | 424.68 | 525.89 | UNKNOWN_FAILURE:15 |
| **`reddit_bing_fallback`** | `reddit` | `ZERO_CONFIG` | 50 | 100.0% | [92.9%, 100.0%] | 0.0% | 3.0 | 80.0 | 490.97 | 802.17 | None |
| **`praw_oauth`** | `reddit` | `ZERO_CONFIG` | 50 | 0.0% | [0.0%, 7.1%] | 0.0% | 0.0 | 0.0 | 12.01 | 12.01 | AUTH_REQUIRED:50 |
| **`reddit_unauth_json`** | `reddit` | `ZERO_CONFIG` | 50 | 0.0% | [0.0%, 7.1%] | 0.0% | 0.0 | 0.0 | 303.85 | 1062.31 | HTTP_ERROR_403:45, UNKNOWN_FAILURE:5 |
| **`tiktok_live_http`** | `tiktok` | `PUBLIC_HTTP` | 15 | 100.0% | [79.6%, 100.0%] | 0.0% | 0.0 | 48.7 | 433.42 | 551.27 | None |
| **`twitter_bing_fallback`** | `twitter` | `ZERO_CONFIG` | 50 | 100.0% | [92.9%, 100.0%] | 0.0% | 3.0 | 80.0 | 512.22 | 1038.75 | None |
| **`twitter_direct`** | `twitter` | `PUBLIC_HTTP` | 50 | 80.0% | [67.0%, 88.8%] | 0.0% | 1.62 | 81.5 | 1376.82 | 1862.31 | UNKNOWN_FAILURE:10 |
| **`youtube_bing_fallback`** | `youtube` | `ZERO_CONFIG` | 50 | 100.0% | [92.9%, 100.0%] | 0.0% | 3.0 | 80.0 | 402.05 | 711.7 | None |
| **`ytdlp_python_import`** | `youtube` | `ZERO_CONFIG` | 50 | 92.0% | [81.2%, 96.9%] | 92.0% | 0.13 | 46.1 | 5566.65 | 23876.23 | UNKNOWN_FAILURE:4 |

## 2. Capability vs. Validated Success Separation

This table separates what an engine *can theoretically do* from what was *empirically validated* under zero-config testing.

| Candidate | Platform | Capability | Auth Required | Auth Used | Direct Content Capability | Validated Direct Success |
|---|---|---|---|---|---|---:|
| **`aegis_native_bilibili`** | `bilibili` | `BLOCKED_WBI` | FALSE | FALSE | `INDEX_ONLY` | **0.0%** |
| **`facebook_live_http`** | `facebook` | `SUPPORTED` | FALSE | FALSE | `PARTIAL_CONTENT` | **0.0%** |
| **`scrapling_http`** | `general_web` | `SUPPORTED` | FALSE | FALSE | `DIRECT_CONTENT` | **90.0%** |
| **`beautifulsoup_requests`** | `general_web` | `SUPPORTED` | FALSE | FALSE | `DIRECT_CONTENT` | **80.0%** |
| **`playwright_headless`** | `general_web` | `SUPPORTED` | FALSE | FALSE | `DIRECT_CONTENT` | **80.0%** |
| **`current_aegis_reader`** | `general_web` | `SUPPORTED` | FALSE | FALSE | `INDEX_ONLY` | **48.0%** |
| **`aegis_native_github`** | `github` | `SUPPORTED` | FALSE | FALSE | `DIRECT_CONTENT` | **100.0%** |
| **`instagram_bing_fallback`** | `instagram` | `SUPPORTED` | FALSE | FALSE | `INDEX_ONLY` | **0.0%** |
| **`instaloader_unauth`** | `instagram` | `SUPPORTED` | TRUE | FALSE | `INDEX_ONLY` | **0.0%** |
| **`linkedin_live_http`** | `linkedin` | `SUPPORTED` | TRUE | FALSE | `INDEX_ONLY` | **0.0%** |
| **`reddit_bing_fallback`** | `reddit` | `SUPPORTED` | FALSE | FALSE | `INDEX_ONLY` | **0.0%** |
| **`praw_oauth`** | `reddit` | `SUPPORTED` | TRUE | FALSE | `DIRECT_CONTENT` | **0.0%** |
| **`reddit_unauth_json`** | `reddit` | `SUPPORTED` | FALSE | FALSE | `INDEX_ONLY` | **0.0%** |
| **`tiktok_live_http`** | `tiktok` | `SUPPORTED` | FALSE | FALSE | `PARTIAL_CONTENT` | **0.0%** |
| **`twitter_bing_fallback`** | `twitter` | `SUPPORTED` | FALSE | FALSE | `INDEX_ONLY` | **0.0%** |
| **`twitter_direct`** | `twitter` | `SUPPORTED` | FALSE | FALSE | `DIRECT_METADATA` | **0.0%** |
| **`youtube_bing_fallback`** | `youtube` | `SUPPORTED` | FALSE | FALSE | `INDEX_ONLY` | **0.0%** |
| **`ytdlp_python_import`** | `youtube` | `SUPPORTED` | FALSE | FALSE | `DIRECT_CONTENT` | **92.0%** |

## 3. Controlled Head-to-Head Validation & Resource Footprint

### A. General Web Engine Resource Benchmark (Common Targets)

| Engine | Avg Latency (ms) | RSS Memory Delta (MB) | Child Processes | Startup Cost (ms) | Cloudflare Bypass Rate |
|---|---:|---:|---:|---:|---:|
| **Scrapling HTTP (`curl_cffi`)** | **365.3** | **7.06** | **0** | **1.2** | **90.0%** |
| **BeautifulSoup / urllib** | 567.12 | 35.7 | 0 | 0.5 | 80.0% (7 Cloudflare 403s) |
| **Playwright Chromium** | 976.53 | 9.43 | 3 | 420.78 | 80.0% (4x slower latency) |

### B. YouTube In-Process Import vs. Subprocess CLI (Identical Targets)

- **In-Process Python Import Latency**: 2191.49 ms  
- **Subprocess CLI (`subprocess.run(['yt-dlp', ...])`) Latency**: 3040.35 ms  
- **Subprocess Process Spawning Overhead**: **+848.86 ms** (In-process import eliminates nearly 1 full second of process spawning!)  
- **Metadata Field Completeness**: 100.0% across all available videos for both modes.  