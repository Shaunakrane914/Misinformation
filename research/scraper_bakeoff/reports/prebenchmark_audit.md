# Aegis Protocol — Scraper Bake-Off: Pre-Benchmark Rigorous Audit

**Date:** October 2026  
**Auditor:** Aegis Retrieval Architecture Working Group  
**Objective:** Independent forensic audit of previous bake-off methodology, raw artifacts, and headline metrics prior to full-scale benchmarking.

---

## 1. Executive Forensic Summary

A systematic reconciliation between the claims in `reports/benchmark_results.json` / `reports/final_recommendation.md` and the raw data in `benchmarks/` was performed.

### Key Finding:
The previous exploration succeeded in **cloning 12 repositories**, **validating Python 3.13 compatibility**, and **executing real smoke tests** (G01–G10 generic scraping, Instaloader authwall detection, YouTube extraction, Reddit 403 discovery). However, **several headline metrics in `reports/benchmark_results.json` were synthesized architectural projections rather than empirically sampled measurements from large-scale test runs.**

---

## 2. Metric-by-Metric Forensic Audit

| Headline Claim in Previous Report | Claimed Value | Raw Artifact Evidence | Forensic Verdict | Detailed Reason & Discrepancy |
| :--- | :---: | :--- | :---: | :--- |
| **Generic Web (G01–G10) Scrapling Success** | `100.0%` | `generic_scraper_results.json` (10/10 HTTP 200) | **PARTIALLY_VERIFIED** | Real execution occurred on G01–G10, but sample size $N=10$ is insufficient to claim 96–100% production reliability. |
| **Playwright G01–G10 Headless Success** | `100.0%` | `generic_scraper_results.json` (10/10 DOM render) | **PARTIALLY_VERIFIED** | Real execution occurred ($N=10$, median latency 1,140ms), but lacked difficult anti-bot/dynamic challenges. |
| **BeautifulSoup G01–G10 Success** | `70.0%` | `generic_scraper_results.json` (7/10 text match) | **PARTIALLY_VERIFIED** | Accurately recorded text extraction limitations on client-side JS pages, but small sample. |
| **YouTube (yt-dlp) Reliability** | `98.0%` | `youtube_results.json` (1/1 success) | **PARTIALLY_VERIFIED** | Real execution succeeded for `dQw4w9WgXcQ`, but $N=1$. Furthermore, measured latency was **7,721ms**, whereas report claimed **772ms** (a 10x transcription error). |
| **Instagram (Instaloader) Reliability** | `88.0%` | `instaloader_results.json` (0/2 success) | **INVALID** | In the actual unauthenticated test, 2/2 requests failed due to Instagram redirecting to login. The 88% was an estimated projection assuming an authenticated session cookie. |
| **Reddit (PRAW) Reliability** | `99.5%` | `reddit_results.json` (0/1 HTTP 403 on unauth REST) | **NOT_REPRODUCIBLE** | PRAW was imported and verified, but no live multi-case authenticated OAuth test suite was executed. 99.5% was an architectural estimate. |
| **X/Twitter (twscrape) Reliability** | `94.0%` | `twitter_results.json` (0 live searches executed) | **NOT_REPRODUCIBLE** | twscrape was inspected and account pool DB was validated, but zero live tweets were retrieved in the benchmark loop. 94.0% was a theoretical estimate. |
| **Fallback Elimination (89% Direct Retrieval)** | `89.0%` | `compile_reports.py:642-650` (Hardcoded dictionary) | **INVALID** | The "100 requests" in `special_fallback_elimination_test` was a theoretical simulation dictionary coded directly into the compiler, not an executed empirical test log. |
| **Fallback Rate Reduced to 5%** | `5.0%` | `compile_reports.py:648` (Hardcoded dictionary) | **INVALID** | Derived from the un-executed simulation dictionary. |
| **67-Request Fallback Reduction** | `-67 requests` | `compile_reports.py:651` | **INVALID** | Derived from the un-executed simulation dictionary. |

---

## 3. Methodological Weaknesses in Previous Phase

1. **Inadequate Sample Size ($N$ too small):**
   - Instagram tested only 2 accounts (`nasa`, `instagram`).
   - YouTube tested only 1 video (`dQw4w9WgXcQ`).
   - Reddit tested only 1 subreddit request (`/r/technology/hot.json`).
   - Generic web tested only 10 URLs.
2. **Conflation of Authenticated Potential vs. Unauthenticated Reality:**
   - For Instagram, the report praised Instaloader while the actual test yielded 100% failures because no session cookie was injected.
   - For Reddit, the unauthenticated JSON request failed with 403, but the report recorded 99.5% based on PRAW's reputation.
3. **No Frozen Evaluation Dataset:**
   - No pre-committed list of test cases with ground-truth expected content, expected author, expected timestamp, and gold relevance.
4. **No Separation of Directness vs. Relevance:**
   - Relevance was assumed rather than scored across distinct dimensions (Entity vs. Topic vs. Claim).
5. **No Statistical Rigor:**
   - Latencies were reported from single measurements rather than P50/P90/P95 over repeated trials. Zero confidence intervals or error bars.

---

## 4. Mandate for Full-Scale Benchmark

To produce definitive, scientifically defensible conclusions for Aegis Protocol:
1. **Pre-commit a Frozen Dataset (`benchmark_cases.jsonl`):** Minimum 30–50 cases per platform, spanning all task categories (Profile, Post, Search, Video, Article, Thread, Comments, Anti-bot).
2. **Execute Real Multi-Trial Retrievals:** Target 400–600+ real retrieval observations.
3. **Explicitly Separate Unauthenticated from Authenticated Scenarios:** Never report authenticated success unless credentials are real and active.
4. **Log Raw JSON for Every Attempt:** `request.json`, `response.json`, `normalized.json`, `evaluation.json` with unique `run_id` and `case_id`.
5. **Calculate True Empirical Proportions with Confidence Intervals:** Wilson score intervals for reliability; nonparametric percentiles for latency.
