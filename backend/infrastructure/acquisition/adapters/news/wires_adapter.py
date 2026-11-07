"""Aegis Protocol — Global & Regional Newswire Platform Adapter.

High-throughput specialized adapter for tier-1 news organizations:
- Reuters & Reuters Wire
- Associated Press (AP)
- BBC News (World, Business, Technology)
- CNN (Top, World, Technology)
- Bloomberg
- The Guardian (World, Business, Technology)
- New York Times (World, Business, Technology)
- Washington Post
- Wall Street Journal (World, Business)
- CNBC (Business, World)
- Financial Times
- Al Jazeera
- France 24
- Deutsche Welle (DW)
- Euronews
- The Independent
- The Telegraph
- Press Information Bureau (PIB India)
- The Hindu (National, Business)
- Indian Express
- NDTV (Top, Profit)
- Times of India & Indiatimes (Top, India, Tech)
- Hindustan Times
- India Today
- Zee News & News18
- Livemint & Business Standard
- The Print & The Wire & Scroll
- ANI News
- Moneycontrol & Economic Times
"""

import concurrent.futures
import html
import logging
import re
import urllib.parse
from typing import Any, Dict, List, Optional

from bs4 import BeautifulSoup

from backend.infrastructure.acquisition.adapters.expansion_safety import GuardedExpansionAdapter as PlatformAdapter
from backend.infrastructure.acquisition.adapters.news.feed_discovery import UniversalFeedDiscovery
from backend.infrastructure.acquisition.adapters.expansion_safety import safe_fetch as fetch_public_http
from backend.infrastructure.acquisition.adapters.web.page_extraction import extract_readable_page
from backend.services.agent_reach.channels import (
    CandidateSource,
    ContentDepth,
    EvidenceFragment,
    FetchedDocument,
    RetrievalMode,
    RetrievalRequest,
)
from backend.services.url_validator import validate_url_safe

logger = logging.getLogger(__name__)


class NewswireAdapter(PlatformAdapter):
    """Acquires and normalizes newswire dispatches, live broadcasts, and official press releases."""

    NEWSWIRE_DOMAINS = {
        "reuters.com": "reuters",
        "reutersagency.com": "reuters",
        "apnews.com": "associated_press",
        "bbc.com": "bbc",
        "bbc.co.uk": "bbc",
        "bbci.co.uk": "bbc",
        "cnn.com": "cnn",
        "bloomberg.com": "bloomberg",
        "theguardian.com": "the_guardian",
        "nytimes.com": "nytimes",
        "washingtonpost.com": "washington_post",
        "wsj.com": "wall_street_journal",
        "dj.com": "wall_street_journal",
        "ft.com": "financial_times",
        "cnbc.com": "cnbc",
        "aljazeera.com": "al_jazeera",
        "nbcnews.com": "nbc_news",
        "cbsnews.com": "cbs_news",
        "abcnews.go.com": "abc_news",
        "sky.com": "sky_news",
        "france24.com": "france24",
        "dw.com": "deutsche_welle",
        "euronews.com": "euronews",
        "independent.co.uk": "independent",
        "telegraph.co.uk": "telegraph",
        "thehindu.com": "the_hindu",
        "indianexpress.com": "indian_express",
        "ndtv.com": "ndtv",
        "timesofindia.indiatimes.com": "times_of_india",
        "indiatimes.com": "indiatimes",
        "hindustantimes.com": "hindustan_times",
        "indiatoday.in": "india_today",
        "zeenews.india.com": "zee_news",
        "news18.com": "news18",
        "livemint.com": "livemint",
        "business-standard.com": "business_standard",
        "moneycontrol.com": "moneycontrol",
        "economictimes.indiatimes.com": "economic_times",
        "theprint.in": "the_print",
        "thewire.in": "the_wire",
        "scroll.in": "scroll_in",
        "deccanherald.com": "deccan_herald",
        "aninews.in": "ani",
        "pib.gov.in": "pib_india",
        "ddnews.gov.in": "dd_news",
        "google.com": "google_news",
        "news.google.com": "google_news",
        "bing.com": "bing_news",
    }

    OFFICIAL_FEEDS = {
        "bbc_world": "https://feeds.bbci.co.uk/news/world/rss.xml",
        "bbc_business": "https://feeds.bbci.co.uk/news/business/rss.xml",
        "bbc_technology": "https://feeds.bbci.co.uk/news/technology/rss.xml",
        "cnn_top": "http://rss.cnn.com/rss/edition.rss",
        "cnn_world": "http://rss.cnn.com/rss/edition_world.rss",
        "cnn_tech": "http://rss.cnn.com/rss/edition_technology.rss",
        "guardian_world": "https://www.theguardian.com/world/rss",
        "guardian_business": "https://www.theguardian.com/business/rss",
        "guardian_tech": "https://www.theguardian.com/technology/rss",
        "nyt_world": "https://rss.nytimes.com/services/xml/rss/nyt/World.xml",
        "nyt_business": "https://rss.nytimes.com/services/xml/rss/nyt/Business.xml",
        "nyt_tech": "https://rss.nytimes.com/services/xml/rss/nyt/Technology.xml",
        "wsj_world": "https://feeds.a.dj.com/rss/RSSWorldNews.xml",
        "wsj_business": "https://feeds.a.dj.com/rss/WSJcomUSBusiness.xml",
        "ft_world": "https://www.ft.com/world?format=rss",
        "cnbc_business": "https://www.cnbc.com/id/10001147/device/rss/rss.html",
        "cnbc_world": "https://www.cnbc.com/id/100727362/device/rss/rss.html",
        "aljazeera": "https://www.aljazeera.com/xml/rss/all.xml",
        "france24": "https://www.france24.com/en/rss",
        "dw": "https://rss.dw.com/rdf/rss-en-all",
        "thehindu_national": "https://www.thehindu.com/news/national/feeder/default.rss",
        "thehindu_business": "https://www.thehindu.com/business/feeder/default.rss",
        "indianexpress": "https://indianexpress.com/section/india/feed/",
        "ndtv_top": "https://feeds.feedburner.com/ndtvnews-top-stories",
        "ndtv_profit": "https://feeds.feedburner.com/ndtvprofit-latest",
        "timesofindia": "https://timesofindia.indiatimes.com/rssfeedstopstories.cms",
        "timesofindia_india": "https://timesofindia.indiatimes.com/rssfeeds/-2128936835.cms",
        "timesofindia_tech": "https://timesofindia.indiatimes.com/rssfeeds/66949542.cms",
        "hindustantimes": "https://www.hindustantimes.com/feeds/rss/india-news/rssfeed.xml",
        "indiatoday": "https://www.indiatoday.in/rss/home",
        "livemint": "https://www.livemint.com/rss/news",
        "livemint_companies": "https://www.livemint.com/rss/companies",
        "business_standard": "https://www.business-standard.com/rss/latest.rss",
        "news18": "https://www.news18.com/commonfeeds/v1/eng/rss/india.xml",
        "news18_tech": "https://www.news18.com/commonfeeds/v1/eng/rss/tech.xml",
        "theprint": "https://theprint.in/category/india/feed/",
        "pib_delhi": "https://pib.gov.in/RssMain.aspx?ModId=6&Lang=1",
    }
    FEED_SECTIONS = {
        'bbc_world': 'world', 'bbc_business': 'business', 'bbc_technology': 'technology',
        'cnn_top': 'world', 'cnn_world': 'world', 'cnn_tech': 'technology',
        'guardian_world': 'world', 'guardian_business': 'business', 'guardian_tech': 'technology',
        'nyt_world': 'world', 'nyt_business': 'business', 'nyt_tech': 'technology',
        'wsj_world': 'world', 'wsj_business': 'business',
        'ft_world': 'world', 'cnbc_business': 'business', 'cnbc_world': 'world',
        'thehindu_national': 'national', 'thehindu_business': 'business', 'indianexpress': 'national',
        'ndtv_top': 'top', 'ndtv_profit': 'business', 'timesofindia': 'top',
        'timesofindia_india': 'national', 'timesofindia_tech': 'technology',
        'hindustantimes': 'national', 'indiatoday': 'top',
        'livemint': 'business', 'livemint_companies': 'business', 'business_standard': 'business',
        'news18': 'national', 'news18_tech': 'technology', 'theprint': 'national',
        'pib_delhi': 'national', 'aljazeera': 'world', 'france24': 'world', 'dw': 'world',
    }
    CATEGORY_QUERIES = {
        'world': {'world', 'world news', 'international news'},
        'business': {'business', 'business news', 'finance', 'finance news', 'market', 'economy', 'sales', 'revenue'},
        'technology': {'technology', 'technology news', 'tech', 'tech news', 'ai', 'semiconductor'},
    }
    MAX_FEEDS_PER_DISCOVER = 8

    @property
    def platform(self) -> str:
        return "news"

    @property
    def backend_id(self) -> str:
        return "newswire_wire_engine"

    def can_handle(self, candidate: CandidateSource) -> bool:
        url = (candidate.canonical_url or candidate.url).lower()
        if candidate.platform.lower() in ("news", "newswire", "pib", "reuters", "ap", "bbc", "cnn", "ndtv"):
            return True
        return any(d in url for d in self.NEWSWIRE_DOMAINS)

    def _feed_priority(self, feed_name: str, clean_q: str, section: Optional[str]) -> int:
        """Score feed affinity based on query topic and regional specificity."""
        sec = self.FEED_SECTIONS.get(feed_name, "")
        pri = 10
        is_indian = any(k in clean_q for k in (
            'india', 'indian', 'tata', 'modi', 'bse', 'nse', 'delhi', 'mumbai',
            'rupee', 'isro', 'sebi', 'infosys', 'adani', 'reliance', 'bihar', 'bengal'
        ))
        is_business = any(k in clean_q for k in (
            'business', 'market', 'stock', 'sales', 'revenue', 'profit', 'economy',
            'financial', 'gdp', 'inflation', 'shares', 'quarter', 'earnings'
        ))
        is_tech = any(k in clean_q for k in (
            'tech', 'technology', 'ai', 'gpu', 'chip', 'semiconductor', 'apple',
            'google', 'microsoft', 'nvidia', 'intel', 'deal', 'deals', 'launch'
        ))

        if is_indian and any(h in feed_name for h in (
            'thehindu', 'indianexpress', 'ndtv', 'timesofindia', 'hindustantimes',
            'indiatoday', 'livemint', 'business_standard', 'news18', 'theprint', 'pib'
        )):
            pri -= 5
        elif not is_indian and any(h in feed_name for h in (
            'bbc', 'cnn', 'guardian', 'nyt', 'wsj', 'ft', 'cnbc', 'aljazeera', 'dw', 'france24'
        )):
            pri -= 4

        if is_business and sec == 'business':
            pri -= 3
        if is_tech and sec == 'technology':
            pri -= 3
        if section and sec == section:
            pri -= 2

        return pri

    def discover(self, query: str, limit: int = 5) -> List[CandidateSource]:
        """Discover live newswire stories matching the query via official feeds and direct news search."""
        candidates: List[CandidateSource] = []
        seen = set()
        clean_q = ' '.join(re.findall(r'\w+', query.casefold()))
        if not clean_q or limit <= 0:
            return candidates

        section = next((name for name, labels in self.CATEGORY_QUERIES.items() if clean_q in labels), None)
        category_words = {word for labels in self.CATEGORY_QUERIES.values() for label in labels for word in label.split()}
        tokens = {word for word in clean_q.split() if len(word) > 2}
        meaningful = tokens - category_words - {'latest', 'updates', 'update', 'the', 'and', 'for', 'about'}

        # 1. Prioritize and concurrently fetch top official channel feeds
        sorted_feeds = sorted(
            self.OFFICIAL_FEEDS.items(),
            key=lambda row: self._feed_priority(row[0], clean_q, section)
        )
        target_feeds = sorted_feeds[:self.MAX_FEEDS_PER_DISCOVER]

        def _fetch_one_feed(item):
            w_name, f_url = item
            try:
                resp = fetch_public_http(f_url, timeout=3.5)
                if resp.status_code == 200:
                    frags = UniversalFeedDiscovery.parse_feed_content(
                        resp.body.decode("utf-8", errors="replace"),
                        f_url,
                        limit=30,
                    )
                    return w_name, f_url, frags
            except Exception as exc:
                logger.debug(f"[NewswireAdapter] Discovery error for {w_name}: {type(exc).__name__}")
            return w_name, f_url, []

        with concurrent.futures.ThreadPoolExecutor(max_workers=min(8, len(target_feeds))) as executor:
            feed_results = list(executor.map(_fetch_one_feed, target_feeds))

        for wire_name, feed_url, frags in feed_results:
            if len(candidates) >= limit:
                break
            for f in frags:
                identity = (f.url or '').split('#', 1)[0]
                if not identity or identity in seen:
                    continue
                text_to_match = set(re.findall(r'\w+', f"{f.title} {f.snippet}".casefold()))
                topic_section = section and self.FEED_SECTIONS.get(wire_name) == section
                overlap = len(meaningful & text_to_match) / max(1, len(meaningful)) if meaningful else 0.0
                token_match = (
                    (overlap >= 0.35) or
                    (len(meaningful) >= 3 and len(meaningful & text_to_match) >= 2) or
                    (len(meaningful) < 3 and bool(meaningful & text_to_match))
                )

                if topic_section or token_match:
                    seen.add(identity)
                    publisher_name = f.raw_metadata.get("publisher") or wire_name.replace("_", " ").title()
                    candidates.append(
                        CandidateSource(
                            url=f.url,
                            platform="news",
                            title=f.title,
                            snippet=f.snippet,
                            search_engine=f"{wire_name}_wire",
                            metadata={
                                "wire": wire_name,
                                "feed_url": feed_url,
                                "publisher_section": self.FEED_SECTIONS.get(wire_name),
                                "publisher_name": publisher_name,
                                "publisher_source_url": f.raw_metadata.get("publisher_source_url", f.url),
                                "discovery_match_basis": 'PUBLISHER_TOPIC_SECTION' if topic_section else 'TITLE_OR_SNIPPET_TOKENS',
                                "discovery_only": True,
                                "linked_article_retrieved": False,
                                "publication_time_basis": "PUBLISHER_FEED_DECLARATION",
                                "published": f.published,
                                "author": f.author or publisher_name,
                                "full_content": f.content,
                                "is_official_wire": True,
                            },
                        )
                    )
                    if len(candidates) >= limit:
                        break

        # 2. Targeted live news search via Bing News RSS with direct URL unwrapping
        if len(candidates) < limit:
            try:
                b_url = f"https://www.bing.com/news/search?q={urllib.parse.quote_plus(clean_q)}&format=rss"
                resp = fetch_public_http(b_url, timeout=3.5)
                if resp.status_code == 200:
                    frags = UniversalFeedDiscovery.parse_feed_content(
                        resp.body.decode("utf-8", errors="replace"),
                        b_url,
                        limit=limit * 2,
                    )
                    for f in frags:
                        raw_u = f.url or ""
                        parsed_u = urllib.parse.urlsplit(raw_u)
                        if "bing.com" in (parsed_u.hostname or "").lower() and "apiclick" in parsed_u.path:
                            qs = urllib.parse.parse_qs(parsed_u.query)
                            direct_u = qs.get("url", [None])[0]
                            if direct_u:
                                raw_u = direct_u
                        identity = raw_u.split("#", 1)[0]
                        if not identity or identity in seen:
                            continue
                        seen.add(identity)
                        publisher_name = f.raw_metadata.get("publisher") or "Major News Wire"
                        candidates.append(
                            CandidateSource(
                                url=raw_u,
                                platform="news",
                                title=f.title,
                                snippet=f.snippet,
                                search_engine="bing_news_rss",
                                metadata={
                                    "wire": publisher_name.lower().replace(" ", "_"),
                                    "feed_url": b_url,
                                    "publisher_name": publisher_name,
                                    "publisher_source_url": raw_u,
                                    "discovery_match_basis": "BING_NEWS_SEARCH",
                                    "discovery_only": True,
                                    "linked_article_retrieved": False,
                                    "publication_time_basis": "PUBLISHER_FEED_DECLARATION",
                                    "published": f.published,
                                    "author": f.author or publisher_name,
                                    "full_content": f.content,
                                    "is_official_wire": True,
                                },
                            )
                        )
                        if len(candidates) >= limit:
                            break
            except Exception as exc:
                logger.debug(f"[NewswireAdapter] Bing News discovery error: {type(exc).__name__}")

        # 3. Google News RSS discovery fallback for additional candidate depth
        if len(candidates) < limit:
            try:
                is_indian = any(k in clean_q for k in ('india', 'indian', 'tata', 'modi', 'bse', 'nse', 'delhi', 'mumbai', 'rupee', 'isro', 'sebi', 'infosys'))
                hl_gl = 'hl=en-IN&gl=IN&ceid=IN:en' if is_indian else 'hl=en-US&gl=US&ceid=US:en'
                url = f"https://news.google.com/rss/search?q={urllib.parse.quote_plus(clean_q)}+when:14d&{hl_gl}"
                resp = fetch_public_http(url, timeout=3.5)
                if resp.status_code == 200:
                    frags = UniversalFeedDiscovery.parse_feed_content(
                        resp.body.decode("utf-8", errors="replace"),
                        url,
                        limit=limit * 2,
                    )
                    for f in frags:
                        identity = (f.url or '').split('#', 1)[0]
                        if not identity or identity in seen:
                            continue
                        seen.add(identity)
                        publisher = f.raw_metadata.get("publisher") or "Major News Channel"
                        candidates.append(
                            CandidateSource(
                                url=f.url,
                                platform="news",
                                title=f.title,
                                snippet=f.snippet,
                                search_engine="google_news_rss",
                                metadata={
                                    "wire": publisher.lower().replace(" ", "_"),
                                    "feed_url": url,
                                    "publisher_name": publisher,
                                    "publisher_source_url": f.raw_metadata.get("publisher_source_url", ""),
                                    "discovery_match_basis": "AGGREGATED_NEWS_SEARCH",
                                    "discovery_only": True,
                                    "linked_article_retrieved": False,
                                    "publication_time_basis": "PUBLISHER_FEED_DECLARATION",
                                    "published": f.published,
                                    "author": f.author or publisher,
                                    "full_content": f.content,
                                    "is_official_wire": True,
                                },
                            )
                        )
                        if len(candidates) >= limit:
                            break
            except Exception as exc:
                logger.debug(f"[NewswireAdapter] Aggregated discovery error: {type(exc).__name__}")

        return candidates

    def acquire(self, candidate: CandidateSource, request: RetrievalRequest) -> FetchedDocument:
        target_url = candidate.canonical_url or candidate.url
        is_safe, reason = validate_url_safe(target_url)
        if not is_safe:
            return FetchedDocument(
                url=target_url,
                status="BLOCKED",
                backend_id=self.backend_id,
                retrieval_mode=RetrievalMode.WEB_READER.value,
                failure_reason=f"SSRF policy blocked URL: {reason}",
            )

        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
        }
        try:
            resp = fetch_public_http(target_url, headers=headers, timeout=5.0, max_bytes=1_000_000)
            body_str = resp.body.decode("utf-8", errors="replace")
            return FetchedDocument(
                url=target_url,
                status="SUCCESS" if resp.status_code == 200 else "FAILED",
                backend_id=self.backend_id,
                retrieval_mode=RetrievalMode.WEB_READER.value,
                raw_content=body_str,
                latency_ms=resp.latency_ms,
            )
        except Exception as exc:
            return FetchedDocument(
                url=target_url,
                status="FAILED",
                backend_id=self.backend_id,
                retrieval_mode=RetrievalMode.WEB_READER.value,
                failure_reason=type(exc).__name__,
            )

    def normalize(
        self,
        document: FetchedDocument,
        candidate: CandidateSource,
        request: RetrievalRequest,
    ) -> List[EvidenceFragment]:
        if document.status != "SUCCESS":
            return []

        raw = document.raw_content
        title = candidate.title or "Newswire Dispatch"

        # Extract readable article prose via semantic page extractor
        clean_text = ""
        try:
            soup = BeautifulSoup(raw, "html.parser")
            title_node = soup.find("title")
            if title_node and title == "Newswire Dispatch":
                title = re.sub(r'\s+', ' ', title_node.get_text()).strip()

            readable_doc = extract_readable_page(soup)
            clean_text = readable_doc.get("text", "").strip()
        except Exception:
            clean_text = ""

        # Fallback to HTML tag stripping if parser yielded empty text
        if not clean_text:
            clean_text = re.sub(r'<[^>]+>', ' ', raw)
            clean_text = re.sub(r'\s+', ' ', clean_text).strip()[:4000]

        clean_text = clean_text[:4000]
        snippet = candidate.snippet or clean_text[:250]

        wire_name = candidate.metadata.get("wire") or "newswire"
        is_official = any(d in document.url.lower() for d in self.NEWSWIRE_DOMAINS) or candidate.metadata.get("is_official_wire", False)

        return [
            EvidenceFragment(
                platform="news",
                title=title,
                content=clean_text or snippet,
                url=document.url,
                author=candidate.metadata.get("author") or wire_name,
                published=candidate.metadata.get("published", ""),
                snippet=snippet,
                score=90.0 if is_official else 80.0,
                content_depth="FULL_ARTICLE" if len(clean_text) > 400 else "SYNDICATED_SUMMARY",
                retrieval_mode=RetrievalMode.WEB_READER.value,
                native_backend_id=self.backend_id,
                channel_name="news",
                raw_metadata={
                    "wire": wire_name,
                    "is_official_wire": is_official,
                    "publisher_name": candidate.metadata.get("publisher_name", wire_name),
                    "publisher_source_url": candidate.metadata.get("publisher_source_url", ""),
                    "publisher_section": candidate.metadata.get("publisher_section"),
                    "linked_article_retrieved": True,
                    "document_length_chars": len(clean_text),
                },
            )
        ]
