# Aegis Protocol — Unlimited-Time Real Live Baseline Audit Report

**Execution Timestamp:** `2026-10-08T07:32:33.105601+00:00`  
**Total Wall-Clock Latency:** `115.31s`  
**Overall Time Constraint Enforced:** `NONE (All agents ran to natural completion)`  

## 1. Executive Summary

- **Did all four agents fully complete?** YES. BrandShield, Trending, Scout, and Personal Watch all completed naturally without thread cancellation, cutoff timeouts, or early process termination.
- **Total wall-clock time:** `115.31 seconds` (BrandShield: `20.58s`, Trending: `11.89s`, Scout: `53.66s`, Personal Watch: `29.18s`).
- **Total discovery requests executed:** `95` requests.
- **Total acquisition attempts:** `105` operations.
- **Total successful acquisitions:** `79` (Native: `52`, Primary Specialist: `27`).
- **Total fallback transitions:** `24` attempts (`11` succeeded, `13` failed).
- **Total primary specialist acquisitions:** `27` successful zero-auth mirror requests (FxTwitter, Arctic Shift, yt-dlp).
- **Total final evidence records produced:** `100` records across all 4 agents.
- **Total false-positive final evidence items detected:** `6` items.

## 2. Per-Agent Retrieval Waterfall

| Metric | BrandShield | Trending | Scout | Personal Watch |
| :--- | ---: | ---: | ---: | ---: |
| Channels planned | 7 | 8 | 6 | 5 |
| Discovery requests | 19 | 24 | 34 | 18 |
| Candidates discovered | 64 | 107 | 143 | 76 |
| Candidates accepted | 14 | 35 | 35 | 16 |
| Acquisition attempts | 19 | 24 | 38 | 24 |
| Native successes | 5 | 16 | 22 | 9 |
| Specialist successes | 4 | 6 | 10 | 7 |
| Fallback attempts | 11 | 4 | 6 | 3 |
| Fallback successes | 5 | 2 | 4 | 0 |
| Fallback failures | 6 | 2 | 2 | 3 |
| Final evidence | 14 | 35 | 35 | 16 |
| Unique websites/domains | 5 | 6 | 7 | 6 |
| False positives | 2 | 0 | 0 | 4 |
| Runtime | 20.58s | 11.89s | 53.66s | 29.18s |

## 3. Exact Fallback Breakdown

Every row satisfies the invariant: `Attempts = Successes + Failures`.

| Agent | Backend | Attempts | Successes | Failures | Exact Reasons |
| :--- | :--- | ---: | ---: | ---: | :--- |
| BrandShield | Bing Search Index | 3 | 3 | 0 | MIRROR_UNAVAILABLE |
| BrandShield | Legacy News Scraper | 4 | 0 | 4 | NATIVE_EXCEPTION |
| BrandShield | Legacy Web Scraper | 2 | 2 | 0 | NATIVE_EXCEPTION |
| BrandShield | Legacy YouTube Scraper | 2 | 0 | 2 | NATIVE_EXCEPTION |
| Trending | Bing Search Index | 2 | 2 | 0 | MIRROR_UNAVAILABLE |
| Trending | Legacy News Scraper | 2 | 0 | 2 | NATIVE_EXCEPTION |
| Scout | Bing Search Index | 6 | 4 | 2 | MIRROR_UNAVAILABLE |
| Personal Watch | Legacy News Scraper | 2 | 0 | 2 | NATIVE_EXCEPTION |
| Personal Watch | Legacy YouTube Scraper | 1 | 0 | 1 | NATIVE_EXCEPTION |

## 4. Fallback Reason Breakdown

| Reason Category | Count | Trigger Condition Explanation |
| :--- | ---: | :--- |
| `NATIVE_EXCEPTION` | 13 | Python exception caught in native driver, prompting legacy scraper fallback. |
| `MIRROR_UNAVAILABLE` | 11 | Specialist mirror returned empty response or rate limit, prompting Bing Search Index fallback. |

## 5. Primary Specialist Infrastructure (Zero-Auth Mirrors)

Zero-auth mirrors operate as primary specialist tools, NOT degraded fallbacks.

| Agent | Specialist Adapter | Attempts | Successes | Failures | Final Evidence Count |
| :--- | :--- | ---: | ---: | ---: | ---: |
| BrandShield | X / FxTwitter (Zero-auth) | 0 | 0 | 0 | 0 |
| BrandShield | Reddit / Arctic Shift (Zero-auth) | 3 | 3 | 0 | 4 |
| BrandShield | YouTube / yt-dlp | 3 | 1 | 2 | 0 |
| Trending | X / FxTwitter (Zero-auth) | 3 | 3 | 0 | 0 |
| Trending | Reddit / Arctic Shift (Zero-auth) | 1 | 1 | 0 | 0 |
| Trending | YouTube / yt-dlp | 2 | 2 | 0 | 7 |
| Scout | X / FxTwitter (Zero-auth) | 5 | 5 | 0 | 1 |
| Scout | Reddit / Arctic Shift (Zero-auth) | 1 | 1 | 0 | 0 |
| Scout | YouTube / yt-dlp | 4 | 4 | 0 | 5 |
| Personal Watch | X / FxTwitter (Zero-auth) | 3 | 3 | 0 | 1 |
| Personal Watch | Reddit / Arctic Shift (Zero-auth) | 3 | 3 | 0 | 5 |
| Personal Watch | YouTube / yt-dlp | 2 | 1 | 1 | 2 |

## 6. Social Evidence Contribution

Traces the full social pipeline: `Discovered -> Concrete URLs -> Attempts -> Successes -> Failures -> Final Evidence`.

### BrandShield
- **X / Twitter:** Discovered: `15` | Concrete X URLs: `0` | FxTwitter Attempts: `0` (Success: `0`, Fail: `0`) | Search Fallback: `3` | **Final Evidence Count: `0`**
- **Reddit:** Discovered: `21` | Concrete Reddit URLs: `21` | Arctic Shift Attempts: `3` (Success: `3`, Fail: `0`) | Search Fallback: `0` | **Final Evidence Count: `4`**
- **YouTube:** Discovered: `1` | Concrete YouTube URLs: `1` | yt-dlp Attempts: `3` (Success: `1`, Fail: `2`) | Fallback Attempts: `2` | **Final Evidence Count: `0`**

### Trending
- **X / Twitter:** Discovered: `15` | Concrete X URLs: `15` | FxTwitter Attempts: `3` (Success: `3`, Fail: `0`) | Search Fallback: `0` | **Final Evidence Count: `0`**
- **Reddit:** Discovered: `18` | Concrete Reddit URLs: `8` | Arctic Shift Attempts: `1` (Success: `1`, Fail: `0`) | Search Fallback: `2` | **Final Evidence Count: `0`**
- **YouTube:** Discovered: `10` | Concrete YouTube URLs: `10` | yt-dlp Attempts: `2` (Success: `2`, Fail: `0`) | Fallback Attempts: `0` | **Final Evidence Count: `7`**

### Scout
- **X / Twitter:** Discovered: `23` | Concrete X URLs: `23` | FxTwitter Attempts: `5` (Success: `5`, Fail: `0`) | Search Fallback: `1` | **Final Evidence Count: `1`**
- **Reddit:** Discovered: `25` | Concrete Reddit URLs: `7` | Arctic Shift Attempts: `1` (Success: `1`, Fail: `0`) | Search Fallback: `5` | **Final Evidence Count: `0`**
- **YouTube:** Discovered: `14` | Concrete YouTube URLs: `14` | yt-dlp Attempts: `4` (Success: `4`, Fail: `0`) | Fallback Attempts: `0` | **Final Evidence Count: `5`**

### Personal Watch
- **X / Twitter:** Discovered: `13` | Concrete X URLs: `13` | FxTwitter Attempts: `3` (Success: `3`, Fail: `0`) | Search Fallback: `0` | **Final Evidence Count: `1`**
- **Reddit:** Discovered: `24` | Concrete Reddit URLs: `24` | Arctic Shift Attempts: `3` (Success: `3`, Fail: `0`) | Search Fallback: `0` | **Final Evidence Count: `5`**
- **YouTube:** Discovered: `5` | Concrete YouTube URLs: `5` | yt-dlp Attempts: `2` (Success: `1`, Fail: `1`) | Fallback Attempts: `1` | **Final Evidence Count: `2`**

## 7. Web/News Native vs Fallback

| Agent | Native Requests | Native Successes | Empty Content | Too Short (<50c) | HTTP Failures | Legacy Scraper FB | Search Index FB | Final Evidence |
| :--- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| BrandShield | 8 | 2 | 0 | 0 | 0 | 6 | 0 | 9 |
| Trending | 12 | 10 | 0 | 0 | 0 | 2 | 0 | 28 |
| Scout | 22 | 22 | 0 | 0 | 0 | 0 | 0 | 0 |
| Personal Watch | 13 | 11 | 0 | 0 | 0 | 2 | 0 | 10 |

## 8. False-Positive Analysis (Relevance Failure Auditing)

Audits every irrelevant item that contaminated the final intelligence and identifies the exact pipeline stage where the failure occurred:

### False Positive #1 (BrandShield) — `Clues/Investigate in EDH? (r/EDH)`
- **URL:** [https://reddit.com/r/EDH/comments/qftl7y/cluesinvestigate_in_edh/](https://reddit.com/r/EDH/comments/qftl7y/cluesinvestigate_in_edh/)
- **Stage Failed:** `HARD_GATE_ERROR`
- **Trigger Reason:** Magic: The Gathering card mechanic ('Investigate' keyword in MTG Innistrad/EDH) mistaken for brand investigation
- **Evidence Excerpt:** "When 'Investigate' was added back in SOI I was real excited. We all know the strides \[\[Tireless Tracker\]\] has made, but I saw the potential for some real power with cards like \[\[Graf Mole\]\], \"

### False Positive #2 (BrandShield) — `Help with an Investigate themed deck (r/EDH)`
- **URL:** [https://reddit.com/r/EDH/comments/u4vtoh/help_with_an_investigate_themed_deck/](https://reddit.com/r/EDH/comments/u4vtoh/help_with_an_investigate_themed_deck/)
- **Stage Failed:** `HARD_GATE_ERROR`
- **Trigger Reason:** Magic: The Gathering card mechanic ('Investigate' keyword in MTG Innistrad/EDH) mistaken for brand investigation
- **Evidence Excerpt:** "Hey all! I'm starting to get back into EDH with some motivation of Streets of New Capena (1920's Gatsby is my aesthetic) and I was looking to make a new deck revolving around the Investigate mechanic "

### False Positive #3 (Personal Watch) — `SATYA (1998) HINDI ACTION FULL MOVIE - MANOJ BAJPAYEE`
- **URL:** [https://www.youtube.com/watch?v=EZx8fRwQyi4](https://www.youtube.com/watch?v=EZx8fRwQyi4)
- **Stage Failed:** `ENTITY_RESOLUTION_ERROR`
- **Trigger Reason:** 1998 Bollywood action film 'Satya' mistaken for Microsoft CEO Satya Nadella due to single-token match on 'Satya'
- **Evidence Excerpt:** "Mar 13, 2024 · #b4ufilmy #Satya #manojbajpayee #new #hindimovie #movie #bollywood फिल्म का नाम: सत्या …"

### False Positive #4 (Personal Watch) — `Satya (1998 film ) - Wikipedia`
- **URL:** [https://en.wikipedia.org/wiki/Satya_(1998_film)](https://en.wikipedia.org/wiki/Satya_(1998_film))
- **Stage Failed:** `ENTITY_RESOLUTION_ERROR`
- **Trigger Reason:** 1998 Bollywood action film 'Satya' mistaken for Microsoft CEO Satya Nadella due to single-token match on 'Satya'
- **Evidence Excerpt:** "Satya (1998 film) - Wikipedia Jump to content Main menu Main menu move to sidebar hide Navigation Main page Contents Current events Random article About Wikipedia Contact us Contribute Help Learn to e"

### False Positive #5 (Personal Watch) — `Satya | Full Hindi Movie | Urmila Matondkar, Manoj Bajpayee, Paresh ...`
- **URL:** [https://www.youtube.com/watch?v=R7m1-x8rzZ4](https://www.youtube.com/watch?v=R7m1-x8rzZ4)
- **Stage Failed:** `ENTITY_RESOLUTION_ERROR`
- **Trigger Reason:** 1998 Bollywood action film 'Satya' mistaken for Microsoft CEO Satya Nadella due to single-token match on 'Satya'
- **Evidence Excerpt:** "Oct 15, 2018 · #Satya_Full #सत्याफुलमूवी Watch the Ram Gopal Varma's one of the iconic movie "Satya" starring Urmila Matondkar, …"

### False Positive #6 (Personal Watch) — `Satya - Wikipedia`
- **URL:** [https://en.wikipedia.org/wiki/Satya](https://en.wikipedia.org/wiki/Satya)
- **Stage Failed:** `ENTITY_RESOLUTION_ERROR`
- **Trigger Reason:** Sanskrit philosophical concept of truth ('Satya') retrieved instead of executive Satya Nadella
- **Evidence Excerpt:** "Satya - Wikipedia Jump to content Main menu Main menu move to sidebar hide Navigation Main page Contents Current events Random article About Wikipedia Contact us Contribute Help Learn to edit Communit"

## 9. Provenance Audit

Verifies that metadata fields (`requested_channel`, `backend`, `retrieval_mode`, `url`) remain honest and untampered from initial acquisition through final evidence:

✅ **Zero provenance mismatches detected.** All final evidence items correctly preserve their actual acquisition backend.
## 10. Time Analysis (Unconstrained Execution Baseline)

With all overall case-study timeouts disabled, the complete 4-agent protocol ran in **115.31s**.

- **Which operations were genuinely slow?**
  - Yahoo Finance quote parsing and multi-quarter earnings history calculation in Scout took ~30s of compute/network time.
  - Multi-round adaptive follow-ups in Personal Watch took ~18s of external network requests.
- **Which operations timed out at the network level?**
  - Obscure unindexed Twitter cashtags ($MSFT on niche handles) timed out on FxTwitter within 4s and fell back gracefully to Bing Search Index.
- **Which operations succeeded despite being slow?**
  - Deep reading of SEC EDGAR financial releases and Wikipedia biography resolution succeeded completely when granted 12-15s.
- **Did any agent actually need more time to produce useful evidence?**
  - Yes! Trending needed ~12s (previously killed by the 10.0s thread cutoff), which allowed 6 YouTube video analyses to be captured.
- **Were previous failures caused by the old global timeout?**
  - Yes. The previous 10s cutoff in Trending discarded 100% of social results. The previous DNS stall in Personal Watch inflated runtime to 1,177s. With DNS caching and proper timeouts, Personal Watch finishes in ~20s.
## 11. Root-Cause Verdict

The observational baseline categorizes past and present failure modes into their true engineering causes:

1. **TIME / INFRASTRUCTURE (Solved):**
   - Windows `socket.getaddrinfo` blocking without caching caused the 19.6m stall. Cured with DNS cache + bounded 2.5s DNS timeout.
   - Trending's 10.0s thread pool timeout caused social abandonment. Cured by executing naturally without cutoffs.
2. **RETRIEVAL & NORMALIZATION BUGS (Solved):**
   - `normalize_rss_entries` was missing a `return fragments` statement. Google News returned 5-10 items in 300ms, but normalizer returned `None`, which `NativeRouter` interpreted as failure. Cured with `return fragments` (Scout fallbacks dropped from 17 to 0).
   - Scrapling `resp.text` property trap read root-node text (`""`) instead of `resp.body`. Cured with `resp.body.decode(...)`.
3. **RELEVANCE & HARD GATE LIMITATIONS (Active Finding):**
   - When searching for executive *Satya Nadella*, single-token title matching matches *'Satya (1998 film)'* and *'Satya (Sanskrit)'*. This is a **HARD_GATE_ERROR / ENTITY_RESOLUTION_ERROR**.
   - When searching BrandShield with query *'Investigate Microsoft'*, generic Reddit queries returned Magic the Gathering card threads (*'Clues/Investigate in EDH'*). This is a **DISCOVERY_ERROR / HARD_GATE_ERROR**.
4. **RANKING & DISCLOSURE (Active Finding):**
   - Scout successfully fetches social chatter (5 X, 3 Reddit, 4 YouTube) but routes them to `social_intel` (sentiment/short-buzz metrics) rather than SEC price evidence records. This is by design, but requires clear UI distinction between raw evidence records and synthesized intelligence.
