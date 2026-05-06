"""
RSS Ingestion Service
Runs as a background task inside the FastAPI process on Render.
Every 15 minutes it fetches financial/misinformation news from Google News RSS
and submits each headline as a claim to be fact-checked by the agent pipeline.
"""

import asyncio
import hashlib
import logging
import os
import xml.etree.ElementTree as ET
from typing import List, Dict

import httpx

logger = logging.getLogger(__name__)

# ── RSS feeds to monitor ──────────────────────────────────────────────────────
RSS_FEEDS = [
    # Financial fraud / market crashes
    "https://news.google.com/rss/search?q=stock+market+crash+OR+bankruptcy+OR+fraud+OR+scandal&hl=en-IN&gl=IN&ceid=IN:en",
    # Misinformation / fake news
    "https://news.google.com/rss/search?q=misinformation+OR+fake+news+OR+hoax+OR+debunked&hl=en&gl=US&ceid=US:en",
    # Health misinformation
    "https://news.google.com/rss/search?q=health+misinformation+OR+vaccine+misinformation+OR+medical+hoax&hl=en&gl=US&ceid=US:en",
]

INTERVAL_SECONDS = int(os.getenv("RSS_INTERVAL_SECONDS", "900"))  # 15 min default
MAX_ITEMS_PER_FEED = int(os.getenv("RSS_MAX_ITEMS", "5"))


def _parse_rss(xml_text: str) -> List[Dict]:
    """Parse RSS XML and return list of {title, link} dicts."""
    items = []
    try:
        root = ET.fromstring(xml_text)
        ns = {"atom": "http://www.w3.org/2005/Atom"}
        for item in root.findall(".//item"):
            title_el = item.find("title")
            link_el  = item.find("link")
            if title_el is not None and title_el.text:
                items.append({
                    "title": title_el.text.strip(),
                    "link":  link_el.text.strip() if link_el is not None and link_el.text else ""
                })
    except ET.ParseError as e:
        logger.warning(f"[RSS] XML parse error: {e}")
    return items[:MAX_ITEMS_PER_FEED]


async def _fetch_feed(client: httpx.AsyncClient, url: str) -> List[Dict]:
    try:
        r = await client.get(url, timeout=15, follow_redirects=True)
        r.raise_for_status()
        return _parse_rss(r.text)
    except Exception as e:
        logger.warning(f"[RSS] Failed to fetch {url}: {e}")
        return []


async def _submit_claim(client: httpx.AsyncClient, title: str, link: str) -> bool:
    """Submit a single claim to the backend pipeline."""
    # Import here to avoid circular imports at module load time
    from backend.db import database as db
    from backend.agents.claim_ingestion_agent import ClaimIngestionAgent
    from backend.workers.claim_worker import process_claim

    try:
        # Deduplicate by hash before hitting the DB
        claim_hash = hashlib.sha256(title.lower().strip().encode()).hexdigest()

        existing = db.get_claim_by_hash(claim_hash)
        if existing:
            logger.debug(f"[RSS] Duplicate skipped: {title[:60]}")
            return False

        # Ingest
        agent = ClaimIngestionAgent()
        result = agent.ingest(claim_text=title, source_url=link)
        normalized = result.get("normalized_text", title)

        inserted = db.insert_claim(
            claim_hash=claim_hash,
            claim_text=title,
            normalized_text=normalized,
        )
        claim_id = str(inserted["id"])
        logger.info(f"[RSS] Inserted claim {claim_id}: {title[:70]}")

        # Process in background (non-blocking)
        asyncio.create_task(_run_worker(claim_id))
        return True

    except Exception as e:
        logger.error(f"[RSS] Error submitting claim '{title[:60]}': {e}")
        return False


async def _run_worker(claim_id: str):
    """Run the synchronous claim worker in a thread pool so it doesn't block the event loop."""
    loop = asyncio.get_event_loop()
    try:
        await loop.run_in_executor(None, _sync_process, claim_id)
    except Exception as e:
        logger.error(f"[RSS] Worker error for {claim_id}: {e}")


def _sync_process(claim_id: str):
    from backend.workers.claim_worker import process_claim
    process_claim(claim_id)


async def rss_ingestion_loop():
    """
    Infinite loop that runs inside the FastAPI process.
    Fetches RSS feeds and submits new claims every INTERVAL_SECONDS.
    """
    logger.info(f"[RSS] Ingestion loop started — interval={INTERVAL_SECONDS}s, feeds={len(RSS_FEEDS)}")

    # Wait 30s after startup so the server is fully ready before first run
    await asyncio.sleep(30)

    while True:
        logger.info("[RSS] Starting ingestion cycle...")
        submitted = 0
        skipped = 0

        async with httpx.AsyncClient(headers={"User-Agent": "AegisProtocol/1.0"}) as client:
            for feed_url in RSS_FEEDS:
                items = await _fetch_feed(client, feed_url)
                logger.info(f"[RSS] Feed returned {len(items)} items: {feed_url[:60]}...")
                for item in items:
                    ok = await _submit_claim(client, item["title"], item["link"])
                    if ok:
                        submitted += 1
                    else:
                        skipped += 1
                    # Small delay between submissions to avoid hammering Gemini
                    await asyncio.sleep(2)

        logger.info(f"[RSS] Cycle complete — submitted={submitted} skipped(dup)={skipped}")
        logger.info(f"[RSS] Next cycle in {INTERVAL_SECONDS}s")
        await asyncio.sleep(INTERVAL_SECONDS)
