# Project Specification: Aegis Protocol Phase 9

**Status:** FINALIZED
**System:** Aegis Protocol (Autonomous Misinformation Intelligence System)
**Date:** 2026-10-24

---

## 1. Problem Statement
The current Aegis Protocol acquisition fabric relies on synchronous `urllib` threads capped at 8 workers, which constrains throughput and limits concurrent multi-domain evidence harvesting. To verify viral narratives and corporate anomalies at enterprise scale, the system needs to expand scraping throughput by $\ge 20\times$ and ingest signals across fact-checkers, wire services, public social networks, regulatory disclosures, and universal RSS feeds.

---

## 2. Requirements & Must-Haves
1. **Hybrid Async Architecture**:
   - `httpx.AsyncClient` with persistent connection pooling (`max_connections=200`, `max_keepalive=50`).
   - Concurrency bounded by `asyncio.Semaphore(160)`.
   - Adaptive per-domain token bucket rate limiting to prevent HTTP 429 rate limits.
   - Non-blocking async DNS resolution with pre-connect IP pinning (preventing DNS rebinding / TOCTOU SSRF attacks).
   - Strict 1 MB response caps and deadline budgets.
2. **5-Category Scraper Fleet**:
   - **Fact-Checking Registries**: Google Fact Check Tools API / ClaimReview, Snopes, PolitiFact, Full Fact, AltNews.
   - **Wire Services & Mainstream News**: Reuters, Associated Press (AP), BBC News, PIB India, ANI.
   - **Public Social & Community**: Bluesky (AT Protocol public endpoints), Mastodon public instance APIs, Hacker News Algolia/Firebase API, Telegram public web previews.
   - **Corporate & Regulatory**: SEC EDGAR filing & submission search engine for Scout.
   - **Broad Web Syndication**: Universal RSS/Atom auto-discovery engine.
3. **Non-Negotiable Invariants**:
   - 100% preservation of all 16 recovered operations.
   - Zero modifications to frozen benchmark datasets.
   - Zero deletion or mutation of historical dossiers.
   - Full backward compatibility for synchronous callers.

---

## 3. Success Verification
- Throughput benchmark proving $\ge 20\times$ speedup over the 8-worker thread pool.
- Full regression suite passing with 0 errors.
