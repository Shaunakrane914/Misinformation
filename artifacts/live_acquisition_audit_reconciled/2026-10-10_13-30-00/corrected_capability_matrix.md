# Aegis Protocol — Corrected 16-Channel Capability Matrix

**Audit Run ID:** `2026-10-10_13-30-00`  
**Date:** October 10, 2026  
**Standard:** Strictly Reconciled Real-Network Empirical Reality (Explicit Denominators)

---

## 1. Summary Outcome Distribution (Explicit Denominators: N = 32 Tested Operations)

| Outcome Category | Count | Percentage | Forensic & Architectural Meaning |
|---|---:|---:|---|
| **DIRECT_CONTENT** | **8** | **25.0%** | Authentic source body/text extracted without mock or index substitution |
| **DIRECT_METADATA** | **4** | **12.5%** | Authentic structured metadata extracted (repos, video info, issues) |
| **PARTIAL_CONTENT** | **1** | **3.1%** | Shell/bio metadata without full status feed (e.g., Twitter profile bio) |
| **INDEX_ONLY** | **3** | **9.4%** | Search engine snippet fallback (Bing / Google search index) |
| **BLOCKED** | **1** | **3.1%** | Anti-bot / Cloudflare challenge blocked direct extraction (e.g. The Hill) |
| **AUTH_REQUIRED** | **7** | **21.9%** | Disconnected credential guard cleanly aborted due to absent keys/cookies |
| **NOT_IMPLEMENTED** | **4** | **12.5%** | Advertised in capability matrix but missing backend method implementation |
| **FAILED** | **4** | **12.5%** | Implementation bug (`gh CLI` typos) or external mirror timeout (Arctic Shift) |

**Total Authentic Evidence Fragments Acquired:** **162 items**

---

## 2. Reconciled Channel-by-Channel Scorecard

| # | Channel | Tested Ops | Active Backend Selected | Direct Body | Direct Meta | Partial | Indexed | Blocked | Auth Req | Unimpl | Failed | Reconciled Status |
|---|---|---:|---|---:|---:|---:|---:|---:|---:|---:|---:|---|
| 1 | **web** | 2 | Scrapling HTTP | 1 | 0 | 0 | 0 | 1 | 0 | 0 | 0 | **VERIFIED_WORKING (1 Blocked)** |
| 2 | **web_search** | 1 | Bing Search (Base64 URL) | 0 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | **VERIFIED_WORKING (Indexed)** |
| 3 | **github** | 4 | GitHub REST (`gh CLI` failed) | 1 | 1 | 0 | 0 | 0 | 0 | 0 | 2 | **PARTIALLY_WORKING (REST Active)** |
| 4 | **youtube** | 4 | `yt-dlp` (in-process + CLI) | 1 | 2 | 0 | 0 | 0 | 0 | 1 | 0 | **VERIFIED_WORKING (Comments Unimpl)** |
| 5 | **bilibili** | 4 | Bilibili Public Search API | 0 | 1 | 0 | 0 | 0 | 0 | 3 | 0 | **PARTIALLY_WORKING (Search Only)** |
| 6 | **v2ex** | 3 | V2EX Public REST API | 3 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | **VERIFIED_WORKING (100% Direct)** |
| 7 | **rss** | 1 | `feedparser` | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | **VERIFIED_WORKING (100% Direct)** |
| 8 | **reddit** | 3 | Bing Index (Arctic Shift down) | 0 | 0 | 0 | 1 | 0 | 0 | 0 | 2 | **FALLBACK_ONLY (Mirror Dead)** |
| 9 | **twitter** | 3 | FxTwitter + Bing Index | 1 | 0 | 1 | 1 | 0 | 0 | 0 | 0 | **PARTIALLY_WORKING (Status/Profile)** |
| 10 | **xueqiu** | 1 | OpenCLI (Disconnected Guard) | 0 | 0 | 0 | 0 | 0 | 1 | 0 | 0 | **DISCONNECTED_GUARD** |
| 11 | **linkedin** | 1 | `mcp-server-linkedin` (Guard) | 0 | 0 | 0 | 0 | 0 | 1 | 0 | 0 | **DISCONNECTED_GUARD** |
| 12 | **xiaohongshu** | 1 | OpenCLI (Disconnected Guard) | 0 | 0 | 0 | 0 | 0 | 1 | 0 | 0 | **DISCONNECTED_GUARD** |
| 13 | **facebook** | 1 | OpenCLI (Disconnected Guard) | 0 | 0 | 0 | 0 | 0 | 1 | 0 | 0 | **DISCONNECTED_GUARD** |
| 14 | **instagram** | 1 | OpenCLI (Disconnected Guard) | 0 | 0 | 0 | 0 | 0 | 1 | 0 | 0 | **DISCONNECTED_GUARD** |
| 15 | **boss** | 1 | `boss-agent-cli` (CDP Guard) | 0 | 0 | 0 | 0 | 0 | 1 | 0 | 0 | **DISCONNECTED_GUARD** |
| 16 | **xiaoyuzhou** | 1 | `groq-whisper` (API Key Guard)| 0 | 0 | 0 | 0 | 0 | 1 | 0 | 0 | **DISCONNECTED_GUARD** |
