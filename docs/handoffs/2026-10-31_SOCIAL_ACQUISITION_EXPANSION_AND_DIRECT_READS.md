# Social Acquisition Expansion & Direct URL Reading Verification — 2026-10-31

**Date:** 2026-10-31  
**Milestone:** Phase 8A (Real Acquisition Proof)  
**Target:** Direct Subreddit and Twitter/X acquisition, query verb sanitization, zero-auth direct reading verification, and regression test maintenance.  
**Branch:** `feat/phase8-real-acquisition-proof` (Uncommitted worktree).  

---

## 1. Executive Summary

In response to the requirement to maximize social coverage where misinformation spreads rapidly (Reddit and X/Twitter), this cycle accomplished two key goals:
1. **Verified Direct Channel & URL Reading**: Confirmed and repaired direct URL reading for Subreddits (`https://reddit.com/r/...` and shorthand `r/...`), Reddit posts/comments, Twitter/X profiles (`https://x.com/...` and `@handle`), and individual tweet permalinks (`https://x.com/.../status/...`) with zero authentication keys required.
2. **Eliminated Social Starvation in Free-Form Scans**: Fixed the 3 root causes that previously caused general investigation prompts (e.g. *"Investigate fake Nike shoe scams"*) to search for entities named `"Investigate"` or require full-string token matches in Reddit titles, resulting in zero social evidence.

---

## 2. Technical Mechanisms for Direct Reads (0 Auth Keys Required)

| Platform | Target Input Format | Zero-Auth Resolution Path | Acquisition Engine |
| :--- | :--- | :--- | :--- |
| **Reddit Subreddit** | `https://www.reddit.com/r/{sub}` or `r/{sub}` | Open Atom/RSS Syndication (`reddit.com/r/{sub}/.rss`) with Arctic Shift search mirror fallback | `NativeRouter._fetch_reddit_subreddit_rss()` |
| **Reddit Post & Comments** | `https://www.reddit.com/r/{sub}/comments/{id}/...` | Arctic Shift zero-auth REST mirror (`/posts/ids?ids={id}` and `/comments/search?link_id=t3_{id}`) | `RedditAdapter.fetch_thread_with_comments()` |
| **Twitter / X Profile** | `https://x.com/{handle}` or `@handle` | FxTwitter profile gateway API (`https://api.fxtwitter.com/{user}`) | `NativeRouter._fetch_twitter_profile()` |
| **Twitter / X Status** | `https://x.com/{user}/status/{id}` | FxTwitter status gateway API (`https://api.fxtwitter.com/{user}/status/{id}`) | `NativeRouter._fetch_twitter_status()` |

---

## 3. Root Cause Diagnostics & Code Remediations

### Regression A: Subreddit URLs Misrouted in `NativeRouter.execute_channel_read()`
- **Diagnosis**: `execute_channel_read()` previously parsed any Reddit URL, extracted the post ID or subreddit, but passed the subreddit name to Arctic Shift's `posts/ids` endpoint. This caused a 404/empty response and fell back to generic web scraping.
- **Repair**: Added explicit detection in `backend/infrastructure/acquisition/routing/router.py`:
  ```python
  if red_src.source_type == "subreddit":
      return self._fetch_reddit_subreddit_rss(red_src.subreddit, limit=10)
  ```
- **Proof**: `https://www.reddit.com/r/technology` retrieves 5,749 characters of live community posts, timestamps, authors, and permalinks in 1.1s.

### Regression B: Prompt Instruction Verb Choking Entity Resolution
- **Diagnosis**: Prompts starting with `"Investigate..."`, `"Verify..."`, `"Check..."`, or `"Find..."` caused `SourcePlanningEngine._infer_entity()` to extract `"Investigate"` as the capitalized target entity. As a result, Wikidata and social handle resolvers attempted to look up `@Investigate` and `r/Investigate`.
- **Repair**: Added `PROMPT_PREFIX_VERBS` regex filtering in `backend/services/agent_reach/source_planner.py` to strip imperative prefixes before entity extraction. Prompts like `"Investigate fake Nike shoe scams"` now cleanly resolve the entity as `"Nike"`.

### Regression C: Shorthand `r/...` and `@...` Planning Bypass
- **Diagnosis**: Direct URL handling in `SourcePlanningEngine._direct_url_action()` only checked for `https?://` schemes. Shorthands like `r/wallstreetbets` or `@OpenAI` were ignored and subjected to broad keyword searches.
- **Repair**: Added regex matching for `r/[a-zA-Z0-9_]+` and `@[a-zA-Z0-9_]+` in `_direct_url_action()`, directly mapping them to priority 0 channel read actions.

### Regression D: Domain Qualifier Over-Filtering in Reddit Ranked Posts
- **Diagnosis**: In `backend/infrastructure/acquisition/resolution/social_resolver.py`, `_extract_clean_entity()` did not strip domain terms like `claims`, `revenue`, `short`, `seller`, `scam`, `counterfeit`, `impersonation`. When querying Reddit posts, `filter_and_rank_posts()` enforced strict token matching, disqualifying relevant discussions.
- **Repair**: Expanded the stop-word sanitization filter in `social_resolver.py` to strip all analytical qualifiers before title token matching.

### Regression E: Golden Replay Hash Protection in Relevance Gate
- **Diagnosis**: In `backend/services/research/relevance_gate.py`, injecting `temporal_fresh` unconditionally into `item.metadata` modified the Phase 4 golden replay checksum.
- **Repair**: Gated `temporal_fresh` inside `if assessment.temporal_status:` to maintain 100% bitwise invariance for Phase 4 replay tests while preserving 48h temporal freshness metadata for live investigations.

---

## 4. Verification Evidence

### 1. Fast Regression Suites
```bash
pytest tests/unit tests/chaos tests/security -q
# Result: 868 passed in 32.00s
```

### 2. Flake8 Static Analysis
```bash
flake8 backend tests scripts --count --select=E9,F63,F7,F82 --show-source --statistics
# Result: 0 errors
```

### 3. Golden Replay Fixtures
```bash
pytest tests/unit/test_research_pipeline_golden.py -q
# Result: 12 passed in 1.48s
```

### 4. Live Direct URL Reading Proof (`scratch/verify_direct_reads.py`)
- `https://www.reddit.com/r/technology`: `status=success`, `backend=reddit-rss`, `char_count=5749`
- `https://x.com/jack/status/20`: `status=success`, `backend=fxtwitter`, `char_count=24` ("just setting up my twttr")
- `https://x.com/OpenAI`: `status=success`, `backend=fxtwitter`, `char_count=129`

---

## 5. Instructions for User / Operator

To directly scrape Subreddits or X channels, enter any of the following formats directly into any agent's prompt field:
1. **Subreddit URL**: `https://www.reddit.com/r/stocks`
2. **Subreddit shorthand**: `r/stocks` or `r/technology`
3. **Twitter/X profile URL**: `https://x.com/elonmusk` or `https://x.com/OpenAI`
4. **Twitter/X handle shorthand**: `@OpenAI`
5. **Tweet status permalink**: `https://x.com/jack/status/20`
6. **Entity investigation**: `Investigate fake Nike shoe scams` (automatically expands to both `r/stocks`/`r/wallstreetbets` and `@Nike` searches).

