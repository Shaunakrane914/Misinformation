# Aegis Protocol — Full-Scale Retrieval Benchmark: Final Scorecard

**Execution Timestamp**: 2026-10-06T16:48:44.862779  
**Hardware Platform**: 13th Gen Intel Core i5-13450HX (16 logical threads, 16GB RAM)  
**Benchmark Scope**: 340 Frozen Cases | 740 Live Over-the-Wire Observations | Duration: 73.5s  

## 1. Candidate Performance Scorecard Across Platforms

| Platform | Candidate Technology | N | Success Rate (95% Wilson CI) | Direct Retr. | Avg Rel (0-3) | Comp (0-100) | P50 (ms) | P95 (ms) | Aegis Fit |
|---|---|---|---|---|---|---|---|---|---|
| `bilibili` | **aegis_native_bilibili** | 20 | 0.0% [0.0%, 16.1%] | 0.0% | 0.0 | 0.0 | 859.53 | 1043.97 | **13.9** |
| `facebook` | **facebook_live_http** | 15 | 100.0% [79.6%, 100.0%] | 100.0% | 0.0 | 50.0 | 1495.08 | 1774.21 | **81.6** |
| `general_web` | **scrapling_http** | 50 | 90.0% [78.6%, 95.7%] | 90.0% | 1.9 | 82.0 | 697.88 | 1989.23 | **85.7** |
| `general_web` | **beautifulsoup_requests** | 50 | 80.0% [67.0%, 88.8%] | 80.0% | 1.68 | 70.2 | 866.9 | 1973.42 | **77.8** |
| `general_web` | **playwright_headless** | 50 | 80.0% [67.0%, 88.8%] | 80.0% | 1.68 | 72.4 | 2778.48 | 4730.95 | **75.1** |
| `general_web` | **current_aegis_reader** | 50 | 48.0% [34.8%, 61.5%] | 48.0% | 1.2 | 46.6 | 1485.68 | 6438.68 | **54.7** |
| `github` | **aegis_native_github** | 25 | 100.0% [86.7%, 100.0%] | 100.0% | 2.92 | 75.2 | 476.54 | 1443.46 | **92.4** |
| `instagram` | **instagram_bing_fallback** | 50 | 100.0% [92.9%, 100.0%] | 0.0% | 1.9 | 77.6 | 381.18 | 539.55 | **68.5** |
| `instagram` | **instaloader_unauth** | 50 | 0.0% [0.0%, 7.1%] | 0.0% | 0.0 | 0.0 | 1210.64 | 3728.36 | **13.0** |
| `linkedin` | **linkedin_live_http** | 15 | 0.0% [0.0%, 20.4%] | 0.0% | 0.0 | 0.0 | 424.68 | 525.89 | **14.3** |
| `reddit` | **reddit_bing_fallback** | 50 | 100.0% [92.9%, 100.0%] | 0.0% | 3.0 | 80.0 | 490.97 | 802.17 | **70.6** |
| `reddit` | **praw_oauth** | 50 | 0.0% [0.0%, 7.1%] | 100.0% | 0.0 | 0.0 | 12.01 | 12.01 | **34.2** |
| `reddit` | **reddit_unauth_json** | 50 | 0.0% [0.0%, 7.1%] | 0.0% | 0.0 | 0.0 | 303.85 | 1062.31 | **14.4** |
| `tiktok` | **tiktok_live_http** | 15 | 100.0% [79.6%, 100.0%] | 100.0% | 0.0 | 48.7 | 433.42 | 551.27 | **82.0** |
| `twitter` | **twitter_direct** | 50 | 80.0% [67.0%, 88.8%] | 76.0% | 1.3 | 65.2 | 1376.82 | 1862.31 | **74.2** |
| `twitter` | **twitter_bing_fallback** | 50 | 100.0% [92.9%, 100.0%] | 0.0% | 3.0 | 80.0 | 512.22 | 1038.75 | **70.6** |
| `youtube` | **youtube_bing_fallback** | 50 | 100.0% [92.9%, 100.0%] | 0.0% | 3.0 | 80.0 | 402.05 | 711.7 | **70.7** |
| `youtube` | **ytdlp_python_import** | 50 | 92.0% [81.2%, 96.9%] | 92.0% | 0.12 | 42.4 | 5566.65 | 23876.23 | **66.1** |

## 2. Failure Mode Taxonomy & Breakdown

| Platform | Candidate | Failure Modes Encountered |
|---|---|---|
| `bilibili` | `aegis_native_bilibili` | `HTTP_ERROR_412`: 20 |
| `facebook` | `facebook_live_http` | None (100% Transport Success) |
| `general_web` | `scrapling_http` | `UNKNOWN_FAILURE`: 3, `HTTP_ERROR_403`: 2 |
| `general_web` | `beautifulsoup_requests` | `HTTP_ERROR_403`: 7, `UNKNOWN_FAILURE`: 3 |
| `general_web` | `playwright_headless` | `HTTP_ERROR_403`: 7, `UNKNOWN_FAILURE`: 3 |
| `general_web` | `current_aegis_reader` | `HTTP_ERROR_403`: 7, `UNKNOWN_FAILURE`: 1, `RATE_LIMITED_429`: 16, `TIMEOUT`: 2 |
| `github` | `aegis_native_github` | None (100% Transport Success) |
| `instagram` | `instagram_bing_fallback` | None (100% Transport Success) |
| `instagram` | `instaloader_unauth` | `AUTH_REQUIRED`: 50 |
| `linkedin` | `linkedin_live_http` | `UNKNOWN_FAILURE`: 15 |
| `reddit` | `reddit_bing_fallback` | None (100% Transport Success) |
| `reddit` | `praw_oauth` | `AUTH_REQUIRED`: 50 |
| `reddit` | `reddit_unauth_json` | `HTTP_ERROR_403`: 45, `UNKNOWN_FAILURE`: 5 |
| `tiktok` | `tiktok_live_http` | None (100% Transport Success) |
| `twitter` | `twitter_direct` | `UNKNOWN_FAILURE`: 10 |
| `twitter` | `twitter_bing_fallback` | None (100% Transport Success) |
| `youtube` | `youtube_bing_fallback` | None (100% Transport Success) |
| `youtube` | `ytdlp_python_import` | `UNKNOWN_FAILURE`: 4 |
