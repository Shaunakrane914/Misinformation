# Aegis Protocol — Final Retrieval Architecture Recommendations

Based on the 340-case empirical benchmark executed across 16 CPU threads, here are the concrete decisions for Aegis Protocol:

## 1. Selected Technology Per Platform

1. **General Web** -> **Scrapling HTTP (`Fetcher`)**
   - *Verdict*: Top Fit Score (92.4). Outperforms plain requests and avoids the heavy RAM/process footprint of Playwright. Excellent TLS/JA4 fingerprinting.
2. **YouTube** -> **`yt-dlp` Python Import**
   - *Verdict*: Top Fit Score (96.5). Flawless metadata extraction with sub-400ms latency.
3. **Reddit** -> **Hybrid Dual Cascade: PRAW (if keys present) -> Search Fallback (`site:reddit.com`)**
   - *Verdict*: Unauthenticated direct REST is permanently dead (0% success). Fallback achieves 100% availability with 82% topic relevance.
4. **X / Twitter** -> **Search Fallback (`site:x.com`) + Optional twscrape Account Pool**
   - *Verdict*: Direct unauthenticated requests cannot fetch post timelines. Search syndication provides reliable signal.
5. **Instagram** -> **Search Fallback (`site:instagram.com`)**
   - *Verdict*: Instaloader without active session cookies is blocked by Instagram login wall.
6. **GitHub** -> **Native REST API (`api.github.com`)**
   - *Verdict*: Top Fit Score (97.2). Clean, reliable, zero scraper dependency needed.
7. **Bilibili** -> **Search Fallback / Jina Web Reader**
   - *Verdict*: API returns HTTP 412 without WBI signatures.

## 2. Implementation Boundaries & Isolation
- Keep all research isolated in `research/scraper_bakeoff/`.
- DO NOT modify `backend/services/agent_reach/` or `NativeRouter` until explicit production migration track is approved.
