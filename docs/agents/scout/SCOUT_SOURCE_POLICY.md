# SCOUT SOURCE POLICY SPECIFICATION
**Aegis Protocol — Agent 1: Scout Proprietary Source Acquisition Engine**
*Phase 3 Deliverable — Source Hierarchy, Acquisition Cascade & Zero-Auth Constraints*

---

## 1. Source-Quality Hierarchy

For trading and news intelligence, sources are stratified into a strict quality hierarchy.
This hierarchy governs ranking weights and corroboration requirements:

```text
Tier 1 — Primary Official Disclosures (Weight: 1.00)
    • SEC / regulatory filings (10-K, 10-Q, 8-K, Form 4)
    • Stock exchange announcements (BSE, NSE, NYSE, NASDAQ)
    • Company Investor Relations (press releases, investor presentations)
    • Government agencies & central banks (FED, RBI, SEC, DOJ, FTC)
    • Verified executive public statements

Tier 2 — High-Quality Financial Journalism (Weight: 0.80)
    • Established global financial press (Bloomberg, Reuters, Financial Times, WSJ)
    • Reputable market reporters (CNBC, MarketWatch, Barron's)
    • Respected regional business press (Economic Times, Livemint, Business Standard)

Tier 3 — Sector-Specific & Specialist Publications (Weight: 0.65)
    • Semiconductor/Tech: SemiAnalysis, AnandTech, Tom's Hardware
    • Auto/EV: Electrek, Automotive News
    • Healthcare/Bio: BioSpace, Endpoints News
    • Legal/Regulatory: Law360, CourtListener

Tier 4 — Public Social & Community Discourse (Weight: 0.40)
    • X / Twitter public threads (authorities, analysts, journalists)
    • Reddit public investment communities (r/stocks, r/investing, r/wallstreetbets)
    • YouTube financial breakdown transcripts
    • Public developer channels (GitHub repositories, commit logs)

Tier 5 — Search & Syndicated Aggregators (Weight: 0.25)
    • News search index snippets
    • Yahoo Finance / MSN aggregated wire reprints
    • RSS headline summaries
```

> **Policy Rule**: Social sources (Tier 4) are valuable early-warning signals for developing rumors, breaking controversies, or retail sentiment, but can NEVER outrank or overturn official Tier 1 regulatory filings.

---

## 2. Acquisition Cascade Policy

Scout employs a deterministic acquisition cascade designed to prioritize speed, cost efficiency, and reliability:

```text
1. Native REST / API Discovery
   • Direct structured endpoints (SEC EDGAR, Arctic Shift, FxTwitter, GitHub REST).
   • Fastest, cheapest, zero HTML overhead.

2. Zero-Auth Public Mirrors
   • Arctic Shift for Reddit submissions/comments.
   • FxTwitter for X/Twitter statuses and profiles.
   • Completely eliminates need for user authentication or rate-limited official tokens.

3. Direct HTTP Extraction
   • Persistent HTTP connection pool with browser headers.
   • Fetches HTML directly for structured parsing (JSON-LD, OpenGraph, HTML5 article tags).

4. Scrapling DOM Parser
   • Employed when simple HTTP responses are obstructed or require specialized DOM traversal.
   • High speed, low memory footprint.

5. Jina Reader Markdown
   • Used selectively for JavaScript-heavy, SPA, or messy commercial article pages.
   • Generates clean token-efficient markdown.

6. Playwright Dynamic Rendering
   • Strictly restricted to complex interactive pages requiring full browser DOM evaluation.
   • Enforces bounded timeout (8s) and process cleanup.

7. Syndication & Search Snippet Fallback
   • Activated when the source is deleted, behind paywall, or blocked.
   • Records content_depth="SNIPPET" and provenance fallback reasons.

8. Structured Rejection
   • Fails explicitly with typed ScoutFailureCode.
```

---

## 3. Zero-Auth Security Policy

Scout operates under strict ethical and security guidelines:
1. **Zero Credential Collection**: Scout NEVER requests, stores, or utilizes user credentials, passwords, session tokens, cookies (`ct0`, `auth_token`), or API secrets for social platforms.
2. **No Circumvention**: Scout does NOT implement CAPTCHA solvers, bot-detection bypassers, or unauthorized penetration techniques.
3. **Public Access Only**: Content is acquired exclusively from publicly accessible endpoints, public mirrors, or compliant search indices.
4. **SSRF Hardening**: All target URLs pass strict IP, port, and scheme validation via `backend.services.url_validator.validate_url_safe` before any network connection is opened. Disallowed schemes (`file://`, `gopher://`, `ftp://`), loopback addresses (`127.0.0.1`), private RFC1918 subnets, and cloud metadata services (`169.254.169.254`) are immediately rejected.

---

## 4. Hard Rejection Gates

A candidate source must be immediately rejected before acquisition if it triggers any of the following hard gates:

1. **Platform Scope Mismatch**:
   - Example: Requested `r/investing` but candidate is from `r/privacy` or `r/gaming`.
   - Action: Immediate rejection (`SOURCE_SCOPE_MISMATCH`).
2. **Invalid URL Structure**:
   - Reddit searches must link to `/comments/<id>` (unless explicitly searching for a subreddit overview).
   - X searches must link to `/status/<id>` (unless explicitly searching for a profile handle).
   - Generic search pages (`/search?q=...`), settings, or homepages are rejected (`INVALID_URL_STRUCTURE`).
3. **Domain Blacklist / Scope Violation**:
   - Corporate landing pages (`nvidia.com`, `apple.com`) are rejected when public social discourse is requested.
   - Non-social domains are rejected from social pipelines (`DOMAIN_MISMATCH`).
4. **Anti-Token-Cheat Protection**:
   - Single-name tokens for multi-token entities (e.g. "Satya" for "Satya Nadella", "Sam" for "Sam Altman", "Jensen" for "Jensen Huang") are REJECTED unless contextual co-occurrence terms (e.g. "Microsoft", "OpenAI", "Nvidia") appear within the candidate text.
