# Aegis Protocol — Trial Environment Validation Report

**Generated**: 2026-10-06 13:23:06 UTC
**Scope**: Controlled Head-to-Head Comparison of Baseline vs Trial Social Routing

## 1. Executive Performance Comparison

| Router Variant | Total Cases | Success Rate | Auth Blocked Rate | P50 Latency | P95 Latency | Avg Evidence Content (chars) |
|---|---:|---:|---:|---:|---:|---:|
| **`baseline_native`** | 12 | **58.3%** | 41.7% | 2197ms | 11343ms | 1444 |
| **`trial_candidate`** | 12 | **100.0%** | 0.0% | 753ms | 4657ms | 860 |

## 2. Key Empirical Results

### A. Reddit Improvements
- **Baseline NativeRouter**: In unauthenticated mode, Reddit reads via Jina Reader fail on client-side SPA rendering or return shallow shell text. Channel queries fall back to Google RSS.
- **Trial Candidate**: Routes direct post URLs (`/comments/<id>/`) to Arctic Shift (`arctic-shift-mirror`), successfully recovering 100% of post bodies and scores in ~1,800ms. Subreddit queries directly extract active post lists.

### B. X / Twitter Improvements
- **Baseline NativeRouter**: Reads on `x.com` status and profile URLs return empty or blocked content via web reader. Channel queries immediately hit `AUTH_REQUIRED_NO_SESSION` and trigger Google RSS.
- **Trial Candidate**: Routes status URLs and profile URLs to FxTwitter (`api.fxtwitter.com`), resolving rich tweet text, timestamps, and engagement counters in **400-650ms** with zero user cookies.

### C. Facebook Handling
- **Baseline NativeRouter**: Facebook queries immediately raise hard `AuthRequiredError` (0% success).
- **Trial Candidate**: Intercepts Facebook queries and executes an honest `PUBLIC_SEARCH_INDEX_ONLY` syndication fallback, returning relevant public headlines and links instead of hard crashes.

## 3. What We Need to Move from Trial to Production

Before merging this architecture into `backend/services/agent_reach/native/router.py`, we require the following 4 engineering decisions/inputs:

1. **Allowlist / Egress Security Approval**:
   - Formal confirmation to add `api.fxtwitter.com` and `arctic-shift.photon-reddit.com` to the outbound network allowlist in `backend/services/url_validator.py` and cloud firewall rules.

2. **TTL In-Memory Caching Strategy**:
   - Implementation of a 10-minute in-memory/Redis TTL cache for Arctic Shift and FxTwitter responses to prevent 429 rate-limiting during high-volume research bursts.

3. **Facebook Strategy Confirmation**:
   - Confirmation of whether Facebook should permanently rely on zero-cost `SEARCH_INDEX` fallback, or if the organization wants to provision an Apify token pool ($5-$20/month) for residential proxy scraping.

4. **Approval for NativeRouter Merge**:
   - Approval to replace lines 308–365 of `backend/services/agent_reach/native/router.py` with the validated specialist adapters.
