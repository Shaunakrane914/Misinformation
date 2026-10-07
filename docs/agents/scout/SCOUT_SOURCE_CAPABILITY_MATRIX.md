# SCOUT SOURCE CAPABILITY MATRIX
**Aegis Protocol — Agent 1: Scout Proprietary Source Acquisition Engine**
*Empirical Capability Matrix Derived from the 348-Case Zero-Auth Transport Audit & 200-Case Semantic Retrieval Benchmark*

---

## 1. Zero-Auth Empirical Capability Hierarchy

Based on **348 audited cases / 696 paired observations** under strictly verified zero-authentication conditions (no OAuth, no personal cookies, no user session tokens, no CT0):

| Platform / Source | Source Type | Direct Access | Structured API | Public Mirror | Search Fallback | Authentication Required | Primary Adapter | Measured Completeness | Known Failure Modes |
|---|---|---|---|---|---|---|---|---|---|
| **GitHub** | Code / Commits / Issues | Yes | Yes (`gh` CLI / REST) | N/A | None needed | **No** (Zero-Auth public) | `GitHubAdapter` | 100% Complete | Rate limiting on unauthenticated IPs |
| **Reddit** | Submissions / Comments | No (Walled HTML) | No | **Yes (Arctic Shift)** | Yes (Bing/RSS) | **No** (Public Mirror) | `RedditAdapter` | 95%+ Content | Burst 422 errors, transient mirror latency |
| **X / Twitter** | Statuses / Profiles | No (Walled HTML) | No | **Yes (FxTwitter)** | Yes (Bing search) | **No** (Public Mirror) | `XAdapter` | 90%+ Metadata/Text | 404 on very brand-new statuses (<5 min) |
| **YouTube** | Video Metadata / Transcripts | Yes | Yes (`yt-dlp`) | N/A | Yes | **No** (Zero-Auth public) | `YouTubeAdapter` | 85%+ Transcripts | Disabled automated captions on some videos |
| **General Web / News** | Articles / Reports | Yes | Yes (JSON-LD) | N/A | Yes | **No** | `GenericWebAdapter` | ~90% Complete | Heavy JS rendering, anti-bot Cloudflare |
| **V2EX** | Public Discussions | Yes | Yes (REST API) | N/A | None needed | **No** | Native API | 100% Complete | Topic pagination |
| **News RSS / Wires** | Syndicated Reporting | Yes | Yes (`feedparser`) | N/A | Direct | **No** | `RSSAdapter` | 95%+ Headlines/Snippets | Truncated RSS descriptions |
| **SEC EDGAR / Company IR** | 10-K, 10-Q, 8-K, Releases | Yes | Yes (EDGAR REST) | N/A | Yes | **No** | `PrimaryFilingAdapter`| 100% Disclosures | User-Agent policy compliance required |
| **Instagram** | Posts / Profiles | No (Walled) | No | No | **Yes (Search-Only)** | **Yes (Blocked)** | Search Syndication | Snippet-Only | Login wall on direct requests |
| **Facebook** | Public Pages | No (Walled) | No | No | **Yes (Search-Only)** | **Yes (Blocked)** | Search Syndication | Snippet-Only | Aggressive login interceptors |
| **TikTok** | Videos / Profiles | No (Walled) | No | No | **Yes (Search-Only)** | **Yes (Blocked)** | Search Syndication | Snippet-Only | Heavy mobile app redirection |
| **LinkedIn** | Posts / Profiles | No (Walled) | No | No | **Yes (Search-Only)** | **Yes (Blocked)** | Search Syndication | Snippet-Only | Auth wall on direct profile access |
| **Xiaohongshu** | Notes | No (Walled) | No | No | **Yes (Search-Only)** | **Yes (Blocked)** | Search Syndication | Snippet-Only | QR login modal |
| **Xueqiu** | Financial Posts | No (Walled) | No | No | **Yes (Search-Only)** | **Yes (Blocked)** | Search Syndication | Snippet-Only | Cookie requirement |
| **Boss直聘** | Job Listings | No (Walled) | No | No | **Yes (Search-Only)** | **Yes (Blocked)** | Search Syndication | Snippet-Only | Phone verification wall |

---

## 2. Strategic Routing Rules

1. **Native / Mirror Priority**:
   - Never use generic HTML scraping for Reddit when **Arctic Shift** is online.
   - Never use generic HTML scraping for X when **FxTwitter** is available.
   - Never use browser rendering for GitHub when **GitHub REST** provides 100% verified structured data.
2. **Search-Only Fallback Boundary**:
   - For walled platforms (Instagram, Facebook, LinkedIn, TikTok, Xiaohongshu), Scout **immediately** routes to search-index discovery without attempting brute-force scraping or credential collection.
   - The provenance explicitly flags `retrieval_mode = "unauthenticated_syndicated_fallback"` and `fallback_reason = "AUTH_REQUIRED_NO_SESSION"`.
3. **Escalation Ladder for General Web**:
   ```text
   Direct HTTP + JSON-LD / HTML5
         ↓ (if JS-heavy or truncated <200 chars)
   Scrapling DOM Extraction
         ↓ (if obfuscated or DOM parsing fails)
   Jina Reader Markdown (r.jina.ai)
         ↓ (if dynamic single-page application)
   Playwright Dynamic Rendering (bounded 8s)
         ↓ (if blocked)
   Search Snippet Fallback
   ```
4. **Zero-Auth Integrity Guarantee**:
   All operations run with `is_authenticated = False`. No passwords, personal cookies, or credentials are ever requested or injected.
