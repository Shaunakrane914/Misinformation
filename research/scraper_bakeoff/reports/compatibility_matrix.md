# Aegis Protocol — Compatibility & Normalization Contract

## 1. Clean Insertion Boundary in Aegis Architecture

```
                 External Specialized Project
      (twscrape, PRAW, instaloader, yt-dlp, Scrapling)
                             │
                             ▼
                 [Platform Adapter Translator]
           (translates platform AST to EvidenceFragment)
                             │
                             ▼
                    [EvidenceFragment]
                             │
                             ▼
                    [AgentReachService]
               (Enforces timeout, security, deduplication)
                             │
                             ▼
                    [NativeRouter]
                             │
                             ▼
                    [ResearchEngine]
```

### Critical Architectural Principle:
- **Zero changes to AgentReach data structures.** Every external project outputs raw records that are immediately converted into Aegis's standard `EvidenceFragment` dataclass.
- **ResearchEngine and RelevanceGate remain completely untouched.** They consume normalized `EvidenceFragment` instances regardless of whether the evidence originated from twscrape, PRAW, or Google News RSS.

---

## 2. Normalization Contract Mapping Table

| Project Field | EvidenceFragment Canonical Field | Normalization Transformation Rule |
| :--- | :--- | :--- |
| `tweet.id_str` / `post.id` | `evidence_id` | `f"{platform}:{raw_id}"` |
| `tweet.rawContent` / `post.selftext` | `content` | Verbatim text; unescape HTML entities. |
| `tweet.user.displayname` | `author` | Screen name or handle. |
| `tweet.url` / `submission.permalink` | `url` | Fully qualified canonical HTTPS URL. |
| `tweet.date` / `post.created_utc` | `published` | ISO-8601 UTC string (`YYYY-MM-DDTHH:MM:SSZ`). |
| `len(content) > 500` | `content_depth` | `FULL_ARTICLE` if >500 chars, else `DIRECT_CONTENT`. |
| `backend_name` | `native_backend_id` | Identifier string (e.g. `twscrape`, `praw`, `scrapling`). |
| `platform` | `requested_channel` | Channel key (e.g. `twitter`, `reddit`, `instagram`). |
| `platform` | `actual_retrieval_channel` | Channel key confirming direct platform acquisition. |
| `"direct_api"` / `"direct_stealth"` | `retrieval_mode` | Accurate mode classification from `RetrievalMode` enum. |
| `raw_dict` | `raw_metadata` | Preserves original GraphQL / REST AST for forensics. |

---

## 3. License, Maintenance & Risk Review (Section 5)

| Project | License | License Classification | Maintenance Status | Integration Risk | Breakage Risk / Notes |
| :--- | :---: | :---: | :---: | :---: | :--- |
| **Playwright** | Apache-2.0 | **LICENSE_SAFE** | ACTIVE | **LOW** | Backed by Microsoft; extremely stable API. |
| **Scrapling** | MIT | **LICENSE_SAFE** | ACTIVE | **LOW** | Modern Python 3.10+ architecture; active updates. |
| **Crawlee** | Apache-2.0 | **LICENSE_SAFE** | ACTIVE | **MEDIUM** | Large dependency surface; higher memory footprint. |
| **Scrapy** | BSD-3 | **LICENSE_SAFE** | ACTIVE | **HIGH** | Twisted event loop conflicts with native AsyncIO. |
| **PRAW** | BSD-2 | **LICENSE_SAFE** | ACTIVE | **LOW** | Official OAuth2 API; zero scraping breakage risk. |
| **twscrape** | MIT | **LICENSE_SAFE** | ACTIVE | **LOW** | Unofficial GraphQL API; account pool handles rotation. |
| **yt-dlp** | The Unlicense | **LICENSE_SAFE** | ACTIVE | **LOW** | Fast upstream hotfix cycle for YouTube anti-bot changes. |
| **Instaloader** | MIT | **LICENSE_SAFE** | MAINTAINED | **MEDIUM** | Unofficial API; requires valid session cookies. |
| **TikTok-Api** | MIT | **LICENSE_SAFE** | MAINTAINED | **MEDIUM** | Dependent on Playwright signing script (`ms_token`). |
| **linkedin_scraper** | MIT | **LICENSE_SAFE** | ACTIVE | **MEDIUM** | Playwright based; strict LinkedIn anti-bot monitoring. |
| **facebook-scraper** | MIT | **LICENSE_SAFE** | STALE | **HIGH** | Legacy unmaintained codebase; dependency conflicts. |
