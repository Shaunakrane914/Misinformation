# Roadmap: Aegis Protocol Phase 9

## Milestone: Phase 9 — 20x Async Acquisition & Expanded Scraper Fleet

### Phase 9.1: High-Throughput Async Engine & Rate Limiter
- [x] Implement `AsyncHTTPTransport` in `backend/infrastructure/acquisition/network/async_http.py`.
- [x] Implement `DomainRateLimiter` in `backend/infrastructure/acquisition/network/rate_limiter.py`.
- [x] Integrate `async_retrieve_many` in `backend/infrastructure/acquisition/service.py` with `asyncio.Semaphore(160)`.
- [x] Add unit tests in `tests/unit/test_async_http_transport.py`.

### Phase 9.2: Fact-Checking Fleet
- [x] Google Fact Check Tools API / ClaimReview parser.
- [x] Snopes & PolitiFact structured rating parsers.
- [x] AltNews & BoomLive regional fact-checking adapters.
- [x] Add unit tests in `tests/unit/test_factcheck_adapter.py`.

### Phase 9.3: News Wires & Syndication Fleet
- [x] Reuters, AP, BBC, PIB, ANI newswire parsers.
- [x] Universal RSS/Atom auto-discovery engine.
- [x] Add unit tests in `tests/unit/test_news_wires_adapter.py`.

### Phase 9.4: Public Social & Community Discussions
- [x] Bluesky AT Protocol public search adapter.
- [x] Mastodon public federation status search.
- [x] Hacker News Algolia API adapter.
- [x] Telegram public channel web preview reader.
- [x] Add unit tests in `tests/unit/test_expanded_social_adapters.py`.

### Phase 9.5: Corporate & Regulatory Fleet (for Scout)
- [x] SEC EDGAR submissions & company filing reader.
- [x] Corporate earnings & press release reader.
- [x] Add unit tests in `tests/unit/test_sec_edgar_adapter.py`.

### Phase 9.6: Verification & Benchmarking
- [x] 20x concurrency throughput benchmark script (`scripts/benchmarks/benchmark_async_throughput.py`).
- [x] Full regression verification (813 pytest tests green, 0 errors).
