# Production Migration Report: Zero-Authentication Reddit & X Retrieval

**Date**: 2026-10-06  
**Status**: COMPLETED & VALIDATED  
**Scope**: Promotion of zero-auth public retrieval adapters from `research/trial_env_20261006_184700/` into production Aegis architecture (`backend/services/agent_reach/native/router.py`).

---

## 1. Files Changed

1. **`backend/services/agent_reach/channels.py`**:
   - Added `ZERO_AUTH_PUBLIC_MIRROR = "zero_auth_public_mirror"` enum value to `RetrievalMode`.
2. **`backend/services/agent_reach/native/channel_capabilities.py`**:
   - Updated `reddit` capability: `tier=0`, `auth_mode="none"`, `cloud_safe=True`, `backend="Arctic Shift (Zero-Auth Mirror)"`.
   - Updated `twitter` capability: `tier=0`, `auth_mode="none"`, `cloud_safe=True`, `backend="FxTwitter (Zero-Auth Mirror)"`.
3. **`backend/services/agent_reach/native/doctor.py`**:
   - Added specialized zero-auth health status reporting in `NativeDoctor`:
     - Reddit: `zero_auth="AVAILABLE"`, `backend="Arctic Shift"`, `auth_required=False`.
     - X/Twitter: `zero_auth="AVAILABLE"`, `backend="FxTwitter"`, `auth_required=False`.
4. **`backend/services/agent_reach/native/normalizer.py`**:
   - Added `normalize_arctic_shift_posts()`: Maps Arctic Shift post payloads into `EvidenceFragment`.
   - Added `normalize_arctic_shift_comments()`: Maps Arctic Shift comment threads into `EvidenceFragment` list.
   - Added `normalize_fxtwitter_tweet()`: Maps FxTwitter tweet JSON into `EvidenceFragment` with engagement counters and media URLs preserved in metadata.
   - Added `normalize_fxtwitter_profile()`: Maps FxTwitter user profile JSON into `EvidenceFragment`.
5. **`backend/services/agent_reach/native/router.py`**:
   - Integrated bounded in-memory cache (`_social_cache`, default TTL 600s via `AEGIS_SOCIAL_CACHE_TTL`).
   - Implemented helper methods: `_fetch_arctic_shift_post`, `_fetch_arctic_shift_search`, `_fetch_arctic_shift_comments`, `_fetch_fxtwitter_status`, `_fetch_fxtwitter_profile`.
   - Replaced old auth-blocking branches in `execute_channel_query` for `reddit` and `twitter` with zero-auth retrieval followed by graceful web search index fallback.
   - In `execute_channel_read()`, added specialist routing for Reddit post URLs (`/comments/<id>`) and Twitter/X status (`/status/<id>`) and profile URLs.
6. **`backend/services/url_validator.py`**:
   - Added `APPROVED_SOCIAL_MIRROR_HOSTNAMES = {"api.fxtwitter.com", "arctic-shift.photon-reddit.com"}` to allowlist for egress traffic without weakening SSRF protections against internal IPs.
7. **`tests/unit/test_zero_auth_social_retrieval.py`**:
   - Added 14 comprehensive unit test cases verifying URL parsing, query routing, comment lookup, timeout/malformed fallback, provenance tagging, doctor output, SSRF rules, and caching.
8. **`tests/smoke_test_social_production.py`**:
   - Added live smoke test script verifying live endpoint retrieval.
9. **`tests/unit/test_agent_reach_native.py`**:
   - Updated `test_native_executor_auth_guard` to target Facebook (which retains authentic session requirements).

---

## 2. Files Intentionally Not Changed

1. **`backend/services/agent_reach_scraper.py`**:
   - Facebook session handling and scraping fallback code was strictly untouched.
2. **`research/scraper_bakeoff/` & Frozen Benchmark Files**:
   - Historical ground truth, 340-case test fixtures, scoring methodology, and raw measurement logs were preserved untouched.
3. **Facebook Router Behavior**:
   - Facebook remains auth-gated (`auth_mode="session_or_cookie"`, requiring `FACEBOOK_COOKIE`) and degrades gracefully to search indexing without attempting scraping.

---

## 3. Reddit Architecture (Arctic Shift)

- **Base Endpoint**: `https://arctic-shift.photon-reddit.com`
- **Authentication**: Zero authentication required. No Reddit OAuth, no client secrets, no cookies.
- **Operations Supported**:
  - **Post URL / ID Lookup**: `GET /api/posts/ids?ids=<id>`
  - **Subreddit & Query Search**: `GET /api/posts/search?subreddit=<sub_name>&q=<query>&limit=<limit>`
  - **Post Comments Lookup**: `GET /api/comments/search?link_id=t3_<id>&limit=<limit>&sort=desc`
- **Evidence Normalization**:
  - Preserves title, selftext body, subreddit, author, UTC timestamps, comment counts, and upvote score.
  - Links to external articles do not fabricate submission selftext.
  - Provenance tagged with `retrieval_mode="zero_auth_public_mirror"`, `native_backend_id="arctic_shift"`, and `is_authenticated=False`.

---

## 4. X / Twitter Architecture (FxTwitter)

- **Base Endpoint**: `https://api.fxtwitter.com`
- **Authentication**: Zero authentication required. No Twitter API bearer tokens, no cookies (`auth_token`, `ct0`), no browser session.
- **Operations Supported**:
  - **Status URL Read**: `GET https://api.fxtwitter.com/<screen_name>/status/<id>`
  - **Profile URL / Lookup**: `GET https://api.fxtwitter.com/<screen_name>`
  - **Broad Keyword Discovery**: Retains search index discovery (`site:x.com <query>` / Bing) rather than scraping.
- **Evidence Normalization**:
  - Preserves tweet text, author name and screen name, creation timestamps, like/retweet/reply counts, view counts, and media URLs.
  - Provenance tagged with `retrieval_mode="zero_auth_public_mirror"`, `native_backend_id="fxtwitter"`, and `is_authenticated=False`.

---

## 5. Fallback Architecture

If an upstream mirror experiences downtime, timeouts, 4xx/5xx responses, or malformed data:
1. Structured debug telemetry logs the failure without throwing unhandled exceptions.
2. The router transitions to `WEB_SEARCH_INDEX` fallback (`Bing Search Index` / `Jina Reader`).
3. Evidence fragments are created with explicit fallback lineage:
   - `retrieval_mode = "web_search_index"`
   - `native_backend_id = "bing-search-index"`
   - `fallback_reason = "ARCTIC_SHIFT_UNAVAILABLE"` or `"FXTWITTER_UNAVAILABLE"`
   - `is_authenticated = False`
4. The ResearchAgent and EvidenceGate proceed without crashing.

---

## 6. Provenance Examples

### Reddit Post Retrieval
```json
{
  "platform": "reddit",
  "requested_channel": "reddit",
  "actual_retrieval_channel": "reddit",
  "retrieval_mode": "zero_auth_public_mirror",
  "native_backend_id": "arctic_shift",
  "is_authenticated": false,
  "retrieval_lineage": [
    {
      "channel": "reddit",
      "requested_channel": "reddit",
      "retrieval_mode": "zero_auth_public_mirror",
      "backend_id": "arctic_shift",
      "is_authenticated": false,
      "retrieved_at": "2026-10-06T13:43:53.692394"
    }
  ],
  "raw_metadata": {
    "backend": "arctic_shift",
    "post_id": "z1c9z",
    "subreddit": "IAmA",
    "score": 14755.0,
    "source_tier": "SPECIALIST_MIRROR",
    "mirror_backend": "arctic-shift"
  }
}
```

### X Status Retrieval
```json
{
  "platform": "twitter",
  "requested_channel": "twitter",
  "actual_retrieval_channel": "twitter",
  "retrieval_mode": "zero_auth_public_mirror",
  "native_backend_id": "fxtwitter",
  "is_authenticated": false,
  "retrieval_lineage": [
    {
      "channel": "twitter",
      "requested_channel": "twitter",
      "retrieval_mode": "zero_auth_public_mirror",
      "backend_id": "fxtwitter",
      "is_authenticated": false,
      "retrieved_at": "2026-10-06T13:44:41.120031"
    }
  ],
  "raw_metadata": {
    "backend": "fxtwitter",
    "tweet_id": "20",
    "likes": 190000,
    "retweets": 120000,
    "source_tier": "SPECIALIST_MIRROR",
    "mirror_backend": "fxtwitter"
  }
}
```

---

## 7. Test Results

### Unit & Integration Suite
Ran `pytest tests/unit/test_zero_auth_social_retrieval.py tests/unit/test_agent_reach_native.py -v`:
- Total tests: **27 passed**, 0 failed (100% pass rate).
- Key unit checks validated:
  - `test_reddit_url_read_arctic_shift`: PASSED
  - `test_reddit_post_id_arctic_shift`: PASSED
  - `test_reddit_query_search_arctic_shift`: PASSED
  - `test_reddit_comments_search_arctic_shift`: PASSED
  - `test_reddit_arctic_shift_timeout_falls_back_to_search_index`: PASSED
  - `test_reddit_arctic_shift_malformed_response_fallback`: PASSED
  - `test_x_status_url_read_fxtwitter`: PASSED
  - `test_x_profile_lookup_fxtwitter`: PASSED
  - `test_x_broad_query_falls_back_to_search_index`: PASSED
  - `test_x_fxtwitter_404_falls_back_gracefully`: PASSED
  - `test_facebook_channel_remains_unchanged`: PASSED
  - `test_doctor_reports_zero_auth_availability`: PASSED
  - `test_ssrf_allowlist_preserves_public_mirrors`: PASSED
  - `test_in_memory_social_cache`: PASSED
  - Native regression suite (GitHub, YouTube, Bilibili, V2EX, RSS, News, Web): ALL PASSED

---

## 8. Live Smoke Results

Live execution of `tests/smoke_test_social_production.py` against production endpoints:

| Case | Provider | Backend | Authenticated | Retrieval Mode | Content Length | Latency (ms) | Fallback Used |
|---|---|---|:---:|---|---:|---:|:---:|
| Obama Reddit AMA Post Read | `reddit` | `arctic_shift` | `False` | `zero_auth_public_mirror` | 1,260 chars | 1,815 ms | `False` |
| `r/technology` Query | `reddit` | `arctic_shift` | `False` | `zero_auth_public_mirror` | 933 chars | 2,486 ms | `False` |
| Reddit Comments `comments:z1c9z` | `reddit` | `arctic_shift` | `False` | `zero_auth_public_mirror` | 39 chars | 1,586 ms | `False` |
| Jack Dorsey Tweet #20 Read | `twitter` | `fxtwitter` | `False` | `zero_auth_public_mirror` | 24 chars | 456 ms | `False` |
| NASA Profile Read | `twitter` | `fxtwitter` | `False` | `zero_auth_public_mirror` | 44 chars | 512 ms | `False` |

---

## 9. Deviations from Trial Implementation

1. **Schema Strictness**: In trial, `raw_metadata` and fragment attributes varied slightly from production `EvidenceFragment`. In production, all fields strictly conform to the dataclass definition in `backend/services/agent_reach/channels.py`.
2. **Comment ID Formatting**: The trial did not explicitly test the Pushshift/Arctic Shift requirement that `link_id` must use the Reddit fullname format `t3_<id>`. In production, `router.py` automatically normalizes `clean_pid` to `t3_<clean_pid>` to prevent 422 Unprocessable Entity responses.
3. **Facebook Separation**: The trial candidate had an experimental `search_index` intercept for Facebook queries. In production, Facebook was kept strictly on its original code path and credentials guard, ensuring zero side-effects on existing Facebook policies.
4. **SSRF Guard**: Provider hostnames (`api.fxtwitter.com`, `arctic-shift.photon-reddit.com`) were explicitly added to `backend/services/url_validator.py` under `APPROVED_SOCIAL_MIRROR_HOSTNAMES`, preserving strict SSRF checking against RFC 1918 private subnets.

---

## 10. Unresolved Issues

None. All 21 criteria in the migration checklist are satisfied.
- Both Arctic Shift and FxTwitter are operational without API keys or cookies.
- Honest provenance is emitted for all zero-auth mirror and fallback retrievals.
- Graceful fallback to search indexing is validated and functional.
- Facebook behavior and benchmark ground truths remain completely untouched.
