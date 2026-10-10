# Aegis Protocol — Phase 6.6: Live Acquisition Failure Root-Cause Analysis

**Audit Run ID:** `2026-10-10_12-45-00`  
**Date:** October 10, 2026  
**Evaluation Mode:** Genuine Live Network I/O (Zero Frozen Mock Substitution)

---

## 1. Executive Failure Taxonomy

Every non-successful retrieval operation observed during live execution was investigated to isolate the proven root cause rather than theoretical assumptions.

| Channel | Operation | Measured Failure / Limitation | Proven Root Cause Category | Exact Code Location / External Service |
|---|---|---|---|---|
| **Reddit** | `search`, `post`, `comments` | Read timeout (>8.0s) / HTTP 403 Forbidden | External Mirror Unreachable / Deprecated | `https://arctic-shift.photon-reddit.com/api` (Timed out in 8.0s) |
| **GitHub** | `github.search_gh_cli` | Subprocess exit code 1 | Incorrect Request Parameter | `backend/services/agent_reach/native/executor.py:192` (`stargazerCount` instead of `stargazersCount`) |
| **GitHub** | `github.read_gh_cli` | Subprocess exit code 1 | Incorrect Request Parameter | `backend/services/agent_reach/native/executor.py:229` (`--json ... readme` is not a valid `gh repo view` field) |
| **YouTube** | `youtube.comments` | Not executed | Operation Not Implemented | `backend/services/agent_reach/native/executor.py` (Missing `execute_youtube_comments`) |
| **Bilibili** | `hot`, `rank`, `read` | Not executed | Operation Not Implemented | `backend/services/agent_reach/native/executor.py` (Missing methods) |
| **Twitter / X** | `twitter.search` | Degraded to Bing search index snippets | Architectural Mirror Limitation | FxTwitter is an embed mirror, not a search engine; search discovery fell back to Bing index |
| **Twitter / X** | `twitter.profile` | Bio metadata only (no user timeline tweets) | Upstream API Surface Limitation | FxTwitter `/user` endpoint does not expose status feeds |
| **Walled Gardens (7)** | `xueqiu`, `linkedin`, `xiaohongshu`, `facebook`, `instagram`, `boss`, `xiaoyuzhou` | AUTH_REQUIRED (0 evidence items) | Credential Gated / Walled Garden | `backend/infrastructure/acquisition/routing/standard_handlers.py:168` (Session cookies/keys absent) |
| **Web** | `web.read_bot_protected` | HTTP 403 Forbidden on protected domains (e.g. `thehill.com`) | Anti-Bot / Cloudflare Challenge | Scrapling HTTP Fetcher lacks automated JS challenge solver for aggressive Cloudflare domains |

---

## 2. In-Depth Forensic Diagnoses

### A. The Reddit Crisis: Arctic Shift Outage & Bing Snippet Degeneration
- **Observed Behavior:** Direct requests to `https://arctic-shift.photon-reddit.com/api/posts/search` and `/posts/ids` time out after 8.0s or return connection resets.
- **Cascade Effect:** Because Arctic Shift is unresponsive, `SocialChannelHandlers._execute_reddit` fails all mirror lookups and falls back to `_indexed_fallback` via Bing Search (`site:reddit.com ...`).
- **Data Quality Consequence:** The returned evidence consists entirely of 150–250 character Bing search snippets (`INDEX_ONLY`), not authentic Reddit submissions or discussion threads. When searching for `"r/technology"`, Bing even returned `r-project.org` statistical software manuals due to lexical confusion.
- **Doctor Health Falsehood:** Despite Arctic Shift being completely unreachable on the real network, `NativeDoctor.get_channel_status("reddit")` hardcodes `status="ok"`, claiming `Zero-auth public retrieval available via Arctic Shift`.

### B. The GitHub CLI Parameter Bugs
- **Bug 1 (`github.search`):** `NativeExecutor.execute_github_search` calls `gh search repos ... --json fullName,description,url,stargazerCount,updatedAt`. In GitHub CLI 2.97.0, the schema parameter is `stargazersCount` (with an 's'). The command exits with code 1.
- **Bug 2 (`github.read`):** `NativeExecutor.execute_github_read` calls `gh repo view ... --json name,description,readme,...`. `gh repo view` does not support `readme` in its `--json` argument list. The command exits with code 1.
- **Resilient Fallback Saving Grace:** `StandardChannelHandlers._execute_github` catches the `gh CLI` exception and falls back to `_fallback_github_rest` via `https://api.github.com/search/repositories`, which succeeds with HTTP 200 in 340ms.

### C. FxTwitter Capabilities vs Over-Advertising
- **Profile Shell Limitation:** FxTwitter `/NASA` returns HTTP 200 with name and bio, but does not provide timeline statuses. The router annotates this as `PARTIAL_CONTENT`.
- **Search Absence:** FxTwitter does not support keyword search queries. The router's search discovery attempts to extract concrete tweet URLs via Bing, but when search indices lack direct status URLs, it falls back to Bing search snippets (`INDEX_ONLY`).

### D. Walled Garden Enforcement
- All 7 gated platforms (`xueqiu`, `linkedin`, `xiaohongshu`, `facebook`, `instagram`, `boss`, `xiaoyuzhou`) correctly abort and report `AUTH_REQUIRED` without fabricating data or leaking secrets.
- Facebook and Instagram direct URL fetches proved that direct HTTP requests to profiles without cookies either serve obfuscated empty JavaScript shells (Facebook) or full login walls (Instagram).
