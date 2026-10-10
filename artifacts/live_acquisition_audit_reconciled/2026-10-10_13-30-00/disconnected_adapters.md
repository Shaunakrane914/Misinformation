# Aegis Protocol — Forensic Diagnosis of Seven Disconnected Channels

**Audit Run ID:** `2026-10-10_13-30-00`  
**Focus:** Instagram, Facebook, LinkedIn, Xiaohongshu, Xueqiu, Boss, Xiaoyuzhou

---

## 1. The Core Architectural Discovery

In `backend/infrastructure/acquisition/routing/standard_handlers.py`, seven platforms reach `_execute_authenticated()`:

```python
def _execute_authenticated(self, platform: str, telemetry: Dict[str, Any]) -> List[EvidenceFragment]:
    env_var = self.AUTH_ENVIRONMENT[platform]
    try:
        self.router.executor.guard_authenticated_channel(platform=platform, backend=telemetry["backend"], env_var=env_var)
        telemetry["status"] = "SUCCESS"
    except AuthRequiredError as error:
        telemetry.update(status="AUTH_REQUIRED", error=str(error))
    return []
```

### Critical Flaws Identified:
1. **Unconditional Empty Return:** `_execute_authenticated()` contains **zero scraper execution code**. Even if `INSTAGRAM_COOKIE`, `FACEBOOK_COOKIE`, or `LINKEDIN_COOKIE` is provided, it unconditionally returns `[]`.
2. **False `SUCCESS` Reporting:** When credentials pass the guard check, line 90 sets `telemetry["status"] = "SUCCESS"`, despite returning exactly **zero evidence fragments**.
3. **No Downstream Adapter Invocation:** The shared dispatcher never invokes `OpenCLI`, `mcp-server-linkedin`, `xiaohongshu-mcp`, or any actual extraction script. These channels are currently **only credential guards**.

---

## 2. Investigation of Unauthenticated Scraper Feasibility

We tested existing imported tools and live network endpoints to determine whether unauthenticated public retrieval is actually feasible on these platforms:

### A. Instagram
- **Tested Implementation:** `instaloader` version 4.15.3 (installed in environment).
- **Live Test Probe:** Attempted public profile query on `nasa`:
  `instaloader.Profile.from_username(context, 'nasa')`
- **Measured Result:** Failed with `ConnectionException: JSON Query to api/v1/users/web_profile_info/: Expecting value: line 1 column 1 (char 0)`.
- **Root Cause:** Instagram in 2026 completely blocks unauthenticated `web_profile_info` REST calls. HTTP requests from datacenter and residential IPs receive HTML login redirects (`/accounts/login/?next=...`).
- **Conclusion:** Unauthenticated direct Instagram scraping is **dead upstream**. Without an authenticated `sessionid` cookie, public retrieval cannot succeed directly.

### B. Facebook
- **Tested Implementation:** `facebook_scraper` version 0.2.59 (installed in environment).
- **Live Test Probe:** Attempted public page posts query on `Google`:
  `facebook_scraper.get_posts('Google', pages=1)`
- **Measured Result:** Returned exactly `0` posts.
- **Root Cause:** Facebook mbasic / mobile HTML endpoints now require authenticated sessions (`c_user` and `xs` cookies). Furthermore, `facebook_scraper` relies on legacy `pyppeteer`, which is unmaintained and broken on Python 3.13.
- **Conclusion:** Unauthenticated direct Facebook scraping is **dead upstream**.

### C. LinkedIn
- **Tested Implementation:** `linkedin_scraper` (cloned in `research/scraper_bakeoff/repos/linkedin_scraper`).
- **Status:** Not installed in active Python environment.
- **Root Cause:** LinkedIn enforces strict auth walls on all profile URLs (`li_at` cookie required). Public unauthenticated HTTP requests receive HTTP 999 or login redirects.
- **Conclusion:** Strictly requires authenticated session.

### D. Xiaohongshu, Xueqiu, Boss
- **Historical Ground Truth:** In the October 6 benchmark (`research/full_noauth_benchmark_20261006_195500/report.md` line 137):
  `- **Xiaohongshu / Boss / Xueqiu**: **C** (Search/Index Only)`
  All cases were resolved via Bing Search Index (`content_length: 125`).
- **Conclusion:** These platforms have never had working direct scrapers in Aegis. They were always search-indexed fallbacks.

### E. Xiaoyuzhou
- **Architectural Scope:** Advertised in matrix as `transcribe` via Groq Whisper (`GROQ_API_KEY`).
- **Conclusion:** This is a multimedia speech-to-text service, not an HTML website scraper. Without `GROQ_API_KEY`, it cleanly requires authentication.

---

## 3. Disconnection Reconciliation Summary

| Platform | Current Dispatcher Behavior | Tested Public Scraper | Does Public Unauth Work? | Required Fix in Phase 6.7 |
|---|---|---|:---:|---|
| **Instagram** | Empty guard stub | Instaloader 4.15.3 | **NO** (Login Redirect) | Route to Bing Search Index for public mentions; require `INSTAGRAM_COOKIE` for direct |
| **Facebook** | Empty guard stub | facebook_scraper | **NO** (Login Redirect) | Route to Bing Search Index for public mentions; require `FACEBOOK_COOKIE` for direct |
| **LinkedIn** | Empty guard stub | linkedin_scraper | **NO** (HTTP 999 Wall) | Route to Bing Search Index / Jina for public profiles; require `LINKEDIN_COOKIE` for direct |
| **Xiaohongshu**| Empty guard stub | OpenCLI | **NO** (Session Wall) | Route to Bing Search Index |
| **Xueqiu** | Empty guard stub | Xueqiu API | **NO** (Cookie Required)| Wire Xueqiu public quote API if available, else route to Bing Search Index |
| **Boss** | Empty guard stub | CDP CLI | **NO** (Anti-Bot CDP) | Require CDP session port or route to search index |
| **Xiaoyuzhou** | Empty guard stub | Groq Whisper | **NO** (API Key Req) | Wire Groq Whisper client when key present; ban false SUCCESS status |
