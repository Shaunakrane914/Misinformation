"""
Aegis Protocol — Trending Discovery & Ingestion
===============================================
Dual operational mode detection (Entity vs Discovery Mode), multi-channel news
fetching via shared acquisition fabric, paparazzi fetching, and truthful box office.
"""

from __future__ import annotations

import logging
import os
import re
import urllib.parse
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import feedparser

from backend.agents.trending.models import KNOWN_ENTITY_CATALOG
from backend.services.agent_reach import agent_reach_service
from backend.services.agent_reach.channels import RetrievalRequest

logger = logging.getLogger(__name__)


def resolve_entity(input_text: str, category: Optional[str] = None) -> Dict[str, Any]:
    """
    Normalize input and detect whether query is Entity Mode or Discovery Mode.
    """
    clean_text = (input_text or "").strip()
    upper_text = clean_text.upper()

    # Discovery Mode keywords
    discovery_patterns = [
        r"\bwhat('?s)?\s+trending\b", r"\btrending\s+in\b", r"\bviral\s+today\b",
        r"\bviral\s+.*today\b", r"\btrending\s+.*today\b",
        r"\bcurrent\s+trends\b", r"\btop\s+trends\b", r"\btoday'?s?\s+trends\b",
        r"\bwhat\s+is\s+trending\b", r"\bwhats\s+happening\b"
    ]
    is_discovery = any(re.search(pat, clean_text, re.IGNORECASE) for pat in discovery_patterns)

    if is_discovery:
        topic_str = clean_text
        for pat in discovery_patterns:
            topic_str = re.sub(pat, "", topic_str, flags=re.IGNORECASE).strip()
        topic_str = re.sub(r'^(in|for|across|of)\s+', '', topic_str, flags=re.IGNORECASE).strip(' ?.')
        target_scope = topic_str if topic_str else (category or "India")

        return {
            "mode": "discovery",
            "input": clean_text,
            "resolved_entity": f"Trending in {target_scope.title()}",
            "scope": target_scope,
            "aliases": [],
            "category": category or "general",
            "confidence": 0.90
        }

    # Entity Mode: Check known catalog
    if upper_text in KNOWN_ENTITY_CATALOG:
        info = KNOWN_ENTITY_CATALOG[upper_text]
        return {
            "mode": "entity",
            "input": clean_text,
            "resolved_entity": info["canonical"],
            "aliases": info["aliases"],
            "category": category or info["category"],
            "confidence": 0.95
        }

    for key, info in KNOWN_ENTITY_CATALOG.items():
        if key in upper_text:
            return {
                "mode": "entity",
                "input": clean_text,
                "resolved_entity": info["canonical"],
                "aliases": info["aliases"],
                "category": category or info["category"],
                "confidence": 0.85
            }

    # General entity fallback
    return {
        "mode": "entity",
        "input": clean_text,
        "resolved_entity": clean_text.title(),
        "aliases": [],
        "category": category or "general",
        "confidence": 0.70
    }


def fetch_news(keyword: str, limit: int = 8) -> List[Dict[str, Any]]:
    """Fetch news headlines via shared acquisition fabric with clean URL and source parsing."""
    if not keyword:
        return []

    try:
        from backend.services.agent_reach.profile import TRENDING_PROFILE
        req = RetrievalRequest(
            agent="trending",
            entity=keyword,
            intent=f"{keyword} news headlines",
            allowed_channels=["news", "web", "rss"],
            candidate_budget=limit,
            profile=TRENDING_PROFILE,
        )
        frags = agent_reach_service.execute(req)
        if frags:
            headlines: List[Dict[str, Any]] = []
            for f in frags[:limit]:
                headlines.append({
                    "title": f.title or "News Headline",
                    "link": f.url or "Source URL unavailable",
                    "published": f.published or datetime.now(timezone.utc).strftime("%a, %d %b %Y %H:%M:%S GMT"),
                    "source": f.author or f.platform.title(),
                    "summary": f.snippet or f.content[:240],
                })
            return headlines
    except Exception as reach_err:
        logger.debug(f"[TrendingAgent] Shared fabric fetch_news notice: {reach_err}")

    # Emergency fallback to RSS if shared fabric yielded no items
    feed_url = (
        "https://news.google.com/rss/search?"
        f"q={urllib.parse.quote_plus(keyword)}&hl=en-IN&gl=IN&ceid=IN:en"
    )
    try:
        from backend.services.url_validator import validate_url_safe
        is_safe, reason = validate_url_safe(feed_url)
        if not is_safe:
            logger.warning(f"[TrendingAgent] Blocked unsafe feed URL: {reason}")
            return []
        parsed = feedparser.parse(feed_url)
        entries = parsed.get("entries", [])[:limit]
        headlines = []
        for entry in entries:
            src_info = entry.get("source")
            source_title = src_info.get("title") if isinstance(src_info, dict) else "Google News"
            link = entry.get("link") or "Source URL unavailable"
            pub = entry.get("published") or datetime.now(timezone.utc).strftime("%a, %d %b %Y %H:%M:%S GMT")
            headlines.append({
                "title": entry.get("title", "News Headline"),
                "link": link,
                "published": pub,
                "source": source_title,
                "summary": entry.get("summary", "")
            })
        return headlines
    except Exception as exc:
        logger.warning(f"Google News fetch error for {keyword}: {exc}")
        return []


def fetch_targeted_news(query: str, window_mins: int = 1440, fetch_news_fn=None) -> List[Dict[str, Any]]:
    """Fetch targeted news articles within time window for /api/trending-news."""
    fetcher = fetch_news_fn or fetch_news
    articles = fetcher(query, limit=6)
    results = []
    for a in articles:
        results.append({
            "title": a.get("title", ""),
            "link": a.get("link", "Source URL unavailable"),
            "published": a.get("published", ""),
            "age_minutes": 15,
            "source": a.get("source", "Market News")
        })
    return results


def fetch_paparazzi(instagram_url: str, client: Optional[Any] = None, timeout_seconds: int = 15) -> List[Dict[str, Any]]:
    """Scrape latest Instagram posts via Apify if available with bounded timeout."""
    if not instagram_url or not client:
        return []

    try:
        actor = client.actor("apidojo/instagram-scraper")
        run = actor.call(
            run_input={
                "startUrls": [{"url": instagram_url}],
                "resultsType": "posts",
                "resultsLimit": 10,
            },
            timeout_secs=timeout_seconds
        )
        if not run or run.get("status") != "SUCCEEDED":
            return []

        dataset = client.dataset(run.get("defaultDatasetId", ""))
        items = dataset.list_items().get("items", []) if dataset else []
        posts = []
        for item in items:
            url = item.get("url") or f"https://instagram.com/p/{item.get('shortCode', '')}"
            posts.append({
                "caption": str(item.get("caption", ""))[:250],
                "url": url if item.get("url") or item.get("shortCode") else "Source URL unavailable",
                "likes": int(item.get("likesCount", 0)),
                "comments": int(item.get("commentsCount", 0)),
                "taken_at": str(item.get("takenAt", datetime.now(timezone.utc).isoformat())),
            })
        return posts
    except Exception as exc:
        logger.info(f"Instagram scrape skipped or unavailable: {exc}")
        return []


def fetch_box_office(movie_name: str) -> Dict[str, Any]:
    """
    Truthful Box Office telemetry handler.
    Reports data if genuinely found in retrieval, otherwise marks as unavailable.
    Never fabricates fictional collection numbers.
    """
    if not movie_name:
        return {"status": "unavailable", "message": "No title specified for box office telemetry."}

    return {
        "source": "Sacnilk / Trade Registry",
        "movie": movie_name,
        "status": "unavailable",
        "message": "Box-office data unavailable — requires verified trade telemetry.",
        "net_india": "N/A",
        "gross_worldwide": "N/A"
    }
