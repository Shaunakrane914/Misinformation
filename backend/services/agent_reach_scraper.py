"""
Agent-Reach Multi-Platform Zero-Cost Scraper Service
===================================================
Inspired by and compatible with Agent-Reach (Panniantong/agent-reach).
Provides zero-API-fee extraction across:
- Twitter/X (Targeted Streams, Syndication & Search)
- Reddit (Native Subreddit Feeds, Discussion Threads & JSON Streams)
- YouTube / Video Metadata (Video Transcripts & Discussions)
- Jina Reader (JS-Rendered Clean Markdown Parsing)
- Multi-Source Web & News Aggregation
"""

import json
import logging
import re
import urllib.parse
from typing import Any, Dict, List, Optional
import feedparser
import requests
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36 AegisReach/1.0"


class AgentReachScraper:
    """
    Unified multi-platform internet and social intelligence scraper.
    Bypasses expensive SaaS API subscriptions with zero-cost extractors.
    """

    def __init__(self, timeout: float = 12.0):
        self.timeout = timeout
        self.headers = {"User-Agent": USER_AGENT}

    # ─────────────────────────────────────────────────────────────────────────
    # 1. REDDIT ZERO-API EXTRACTOR
    # ─────────────────────────────────────────────────────────────────────────
    def search_reddit(
        self,
        query: str,
        subreddits: Optional[List[str]] = None,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Search Reddit discussions without Reddit API keys using public streams and RSS indexers.
        """
        results: List[Dict[str, Any]] = []
        clean_q = query.strip()
        encoded_q = urllib.parse.quote_plus(clean_q)

        # 1. Bing News RSS for Reddit (Fast, reliable, zero blocking)
        try:
            bing_url = f"https://www.bing.com/news/search?q={urllib.parse.quote_plus('reddit ' + clean_q)}&format=rss"
            resp = requests.get(bing_url, headers=self.headers, timeout=self.timeout)
            if resp.status_code == 200:
                feed = feedparser.parse(resp.content)
                for entry in feed.get("entries", [])[:limit]:
                    title = entry.get("title", "")
                    link = entry.get("link", "")
                    summary = entry.get("summary", "")
                    published = entry.get("published", "")

                    # Extract clean text from HTML summary
                    soup = BeautifulSoup(summary, "html.parser")
                    text_content = soup.get_text(separator=" ", strip=True)

                    results.append({
                        "platform": "Reddit",
                        "title": title,
                        "content": f"{title}\n{text_content[:300]}",
                        "url": link,
                        "author": "u/community",
                        "published": published,
                        "snippet": text_content[:200] or title,
                        "score": 25
                    })
                    if len(results) >= limit:
                        break
        except Exception as e:
            logger.debug(f"[AgentReach] Bing Reddit search failed: {e}")

        # 2. PullPush Public Reddit Archive (No Auth Required)
        if len(results) < limit:
            try:
                pp_url = f"https://api.pullpush.io/reddit/search/submission/?q={encoded_q}&size={limit}"
                resp = requests.get(pp_url, headers=self.headers, timeout=self.timeout)
                if resp.status_code == 200:
                    data = resp.json().get("data", [])
                    for post in data:
                        title = post.get("title", "")
                        selftext = post.get("selftext", "")
                        permalink = post.get("full_link") or f"https://reddit.com/r/{post.get('subreddit')}/comments/{post.get('id')}"
                        author = post.get("author", "redditor")
                        sub = post.get("subreddit", "all")

                        if not any(r.get("url") == permalink for r in results):
                            results.append({
                                "platform": "Reddit",
                                "subreddit": f"r/{sub}",
                                "title": title,
                                "content": f"{title}\n{selftext[:300]}",
                                "url": permalink,
                                "author": f"u/{author}",
                                "snippet": selftext[:200] or title,
                                "score": post.get("score", 10)
                            })
                            if len(results) >= limit:
                                break
            except Exception as pp_err:
                logger.debug(f"[AgentReach] PullPush Reddit search failed: {pp_err}")

        # 3. Direct Reddit RSS with Browser User-Agent
        if len(results) < limit:
            try:
                r_url = f"https://www.reddit.com/search.rss?q={encoded_q}&sort=new"
                r_resp = requests.get(r_url, headers=self.headers, timeout=5)
                if r_resp.status_code == 200:
                    feed = feedparser.parse(r_resp.content)
                    for entry in feed.get("entries", [])[:limit]:
                        title = entry.get("title", "")
                        link = entry.get("link", "")
                        summary = entry.get("summary", "")
                        author = entry.get("author", "u/reddit_user")

                        soup = BeautifulSoup(summary, "html.parser")
                        text_content = soup.get_text(separator=" ", strip=True)

                        if not any(r.get("url") == link for r in results):
                            results.append({
                                "platform": "Reddit",
                                "title": title,
                                "content": f"{title}\n{text_content[:300]}",
                                "url": link,
                                "author": author if author.startswith("u/") else f"u/{author}",
                                "published": entry.get("published", ""),
                                "snippet": text_content[:200] or title,
                                "score": 15
                            })
                            if len(results) >= limit:
                                break
            except Exception as r_err:
                logger.debug(f"[AgentReach] Direct Reddit RSS fallback: {r_err}")

        return results[:limit]

    # ─────────────────────────────────────────────────────────────────────────
    # 2. TWITTER / X ZERO-API EXTRACTOR
    # ─────────────────────────────────────────────────────────────────────────
    def search_twitter(
        self,
        query: str,
        vip_handle: Optional[str] = None,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Search Twitter/X mentions & discussions without paid Twitter API or Apify tokens.
        Queries live Twitter discussions and syndication feeds.
        """
        results: List[Dict[str, Any]] = []
        clean_handle = (vip_handle or "").lstrip("@")
        clean_q = query.strip()

        # 1. Search Google News Twitter streams (real-time, zero auth)
        try:
            feed_query = f'"{clean_q}" site:x.com OR site:twitter.com'
            if clean_handle:
                feed_query += f' -from:{clean_handle}'
            
            feed_url = f"https://news.google.com/rss/search?q={urllib.parse.quote_plus(feed_query)}&hl=en-US&gl=US&ceid=US:en"
            feed = feedparser.parse(feed_url)
            
            for entry in feed.get("entries", [])[:limit]:
                title = entry.get("title", "")
                link = entry.get("link", "")
                published = entry.get("published", "")
                
                # Clean up title formatting from Twitter feeds
                handle_match = re.search(r'(@[A-Za-z0-9_]+)', title)
                author = handle_match.group(1) if handle_match else "@user"

                results.append({
                    "platform": "Twitter/X",
                    "author": author,
                    "title": title,
                    "content": title,
                    "url": link,
                    "snippet": title,
                    "published": published,
                    "is_reply": "status" in link or "status" in title.lower()
                })
        except Exception as e:
            logger.debug(f"[AgentReach] Twitter stream fetch failed: {e}")

        # 2. Bing News RSS for Twitter/X
        if len(results) < limit:
            try:
                b_query = f"twitter {clean_q}"
                b_url = f"https://www.bing.com/news/search?q={urllib.parse.quote_plus(b_query)}&format=rss"
                resp = requests.get(b_url, headers=self.headers, timeout=self.timeout)
                if resp.status_code == 200:
                    feed = feedparser.parse(resp.content)
                    for entry in feed.get("entries", [])[:limit]:
                        title = entry.get("title", "")
                        link = entry.get("link", "")
                        if not any(r.get("url") == link for r in results):
                            results.append({
                                "platform": "Twitter/X",
                                "author": "@social_pulse",
                                "title": title,
                                "content": title,
                                "url": link,
                                "snippet": title,
                                "published": entry.get("published", ""),
                                "is_reply": False
                            })
                            if len(results) >= limit:
                                break
            except Exception as b_err:
                logger.debug(f"[AgentReach] Bing Twitter fallback failed: {b_err}")

        # 2. Check syndication timeline if handle provided
        if clean_handle and len(results) < limit:
            try:
                syn_url = f"https://syndication.twitter.com/srv/timeline-profile/screen-name/{clean_handle}"
                resp = requests.get(syn_url, headers=self.headers, timeout=self.timeout)
                if resp.status_code == 200 and "reactRoot" in resp.text:
                    tweet_matches = re.findall(r'<p class="timeline-Tweet-text"[^>]*>(.*?)</p>', resp.text)
                    for t_text in tweet_matches[:limit]:
                        clean_text = re.sub(r'<[^>]+>', '', t_text)
                        results.append({
                            "platform": "Twitter/X (Official Timeline)",
                            "author": f"@{clean_handle}",
                            "title": f"Post from @{clean_handle}",
                            "content": clean_text,
                            "url": f"https://x.com/{clean_handle}",
                            "snippet": clean_text,
                            "is_official": True
                        })
            except Exception as syn_err:
                logger.debug(f"[AgentReach] Twitter syndication error: {syn_err}")

        return results[:limit]

    # ─────────────────────────────────────────────────────────────────────────
    # 3. YOUTUBE / VIDEO METADATA ZERO-API EXTRACTOR
    # ─────────────────────────────────────────────────────────────────────────
    def search_youtube(self, query: str, limit: int = 6) -> List[Dict[str, Any]]:
        """
        Search YouTube videos and discussions without a YouTube Data API Key.
        """
        results: List[Dict[str, Any]] = []
        clean_q = query.strip()
        try:
            feed_query = f'site:youtube.com "{clean_q}"'
            feed_url = f"https://news.google.com/rss/search?q={urllib.parse.quote_plus(feed_query)}&hl=en-US&gl=US&ceid=US:en"
            feed = feedparser.parse(feed_url)
            
            for entry in feed.get("entries", [])[:limit]:
                title = entry.get("title", "")
                link = entry.get("link", "")
                published = entry.get("published", "")
                
                results.append({
                    "platform": "YouTube",
                    "title": title,
                    "channel": "YouTube Creator",
                    "url": link,
                    "content": f"[YouTube Video] {title}",
                    "snippet": title,
                    "published": published
                })
        except Exception as e:
            logger.debug(f"[AgentReach] YouTube stream query failed: {e}")

        if len(results) < limit:
            try:
                b_query = f"youtube {clean_q}"
                b_url = f"https://www.bing.com/news/search?q={urllib.parse.quote_plus(b_query)}&format=rss"
                resp = requests.get(b_url, headers=self.headers, timeout=self.timeout)
                if resp.status_code == 200:
                    feed = feedparser.parse(resp.content)
                    for entry in feed.get("entries", [])[:limit]:
                        title = entry.get("title", "")
                        link = entry.get("link", "")
                        if not any(r.get("url") == link for r in results):
                            results.append({
                                "platform": "YouTube",
                                "title": title,
                                "channel": "YouTube Video",
                                "url": link,
                                "content": f"[YouTube] {title}",
                                "snippet": title,
                                "published": entry.get("published", "")
                            })
                            if len(results) >= limit:
                                break
            except Exception as b_err:
                logger.debug(f"[AgentReach] Bing YouTube fallback failed: {b_err}")

        return results[:limit]

    # ─────────────────────────────────────────────────────────────────────────
    # 4. NEWS & WEB ZERO-API EXTRACTOR
    # ─────────────────────────────────────────────────────────────────────────
    def search_news(self, query: str, limit: int = 8) -> List[Dict[str, Any]]:
        """
        Search global news headlines and press releases without API keys.
        """
        results: List[Dict[str, Any]] = []
        clean_q = query.strip()
        try:
            feed_url = f"https://news.google.com/rss/search?q={urllib.parse.quote_plus(clean_q)}&hl=en-US&gl=US&ceid=US:en"
            feed = feedparser.parse(feed_url)
            for entry in feed.get("entries", [])[:limit]:
                source_title = None
                source = entry.get("source")
                if isinstance(source, dict):
                    source_title = source.get("title")
                    
                results.append({
                    "platform": "News RSS",
                    "title": entry.get("title", ""),
                    "source": source_title or "News Wire",
                    "url": entry.get("link", ""),
                    "published": entry.get("published", ""),
                    "snippet": entry.get("title", ""),
                    "content": f"{entry.get('title', '')} ({source_title or 'News Wire'})"
                })
        except Exception as e:
            logger.debug(f"[AgentReach] News search failed: {e}")

        # Bing News RSS Fallback
        if len(results) < limit:
            try:
                b_url = f"https://www.bing.com/news/search?q={urllib.parse.quote_plus(clean_q)}&format=rss"
                resp = requests.get(b_url, headers=self.headers, timeout=self.timeout)
                if resp.status_code == 200:
                    feed = feedparser.parse(resp.content)
                    for entry in feed.get("entries", [])[:limit]:
                        title = entry.get("title", "")
                        link = entry.get("link", "")
                        if not any(r.get("url") == link for r in results):
                            results.append({
                                "platform": "News RSS",
                                "title": title,
                                "source": "Global Wire",
                                "url": link,
                                "published": entry.get("published", ""),
                                "snippet": title,
                                "content": f"{title} (Global Wire)"
                            })
                            if len(results) >= limit:
                                break
            except Exception as b_err:
                logger.debug(f"[AgentReach] Bing News fallback failed: {b_err}")

        return results[:limit]

    # ─────────────────────────────────────────────────────────────────────────
    # 5. JINA READER CLEAN MARKDOWN EXTRACTOR
    # ─────────────────────────────────────────────────────────────────────────
    def read_article_markdown(self, url: str, max_chars: int = 4000) -> Dict[str, Any]:
        """
        Convert any complex, JS-rendered web page or news article into clean,
        token-efficient markdown for LLM consumption using Jina Reader.
        """
        clean_url = url.strip()
        if not clean_url:
            return {"status": "error", "url": "", "title": "Empty URL", "markdown": "", "char_count": 0}

        jina_url = f"https://r.jina.ai/{clean_url}"
        try:
            resp = requests.get(
                jina_url,
                headers={"User-Agent": USER_AGENT, "Accept": "text/plain"},
                timeout=self.timeout
            )
            if resp.status_code == 200 and len(resp.text) > 80:
                markdown_text = resp.text[:max_chars]
                title_match = re.search(r'^#\s+(.+)$', markdown_text, re.MULTILINE)
                title = title_match.group(1) if title_match else "Web Article"
                return {
                    "status": "success",
                    "url": clean_url,
                    "title": title,
                    "markdown": markdown_text,
                    "char_count": len(markdown_text)
                }
        except Exception as e:
            logger.debug(f"[AgentReach] Jina Reader direct failed: {e}")

        # Fallback: standard HTTP + BeautifulSoup
        try:
            resp = requests.get(clean_url, headers=self.headers, timeout=self.timeout)
            if resp.status_code == 200:
                soup = BeautifulSoup(resp.text, "html.parser")
                for s in soup(["script", "style", "nav", "footer", "header"]):
                    s.decompose()
                title = soup.title.string if soup.title else "Web Document"
                text = soup.get_text(separator=" ", strip=True)[:max_chars]
                return {
                    "status": "fallback_soup",
                    "url": clean_url,
                    "title": title,
                    "markdown": text,
                    "char_count": len(text)
                }
        except Exception as f_err:
            logger.debug(f"[AgentReach] Direct fetch fallback failed: {f_err}")

        return {
            "status": "error",
            "url": clean_url,
            "title": "Unavailable",
            "markdown": "",
            "char_count": 0
        }

    # ─────────────────────────────────────────────────────────────────────────
    # 6. UNIFIED MULTI-PLATFORM SCAN (COMBINED INTELLIGENCE)
    # ─────────────────────────────────────────────────────────────────────────
    def unified_scan(
        self,
        query: str,
        include_reddit: bool = True,
        include_twitter: bool = True,
        include_youtube: bool = True,
        include_news: bool = True,
        max_per_channel: int = 6
    ) -> Dict[str, Any]:
        """
        Execute parallel or coordinated scan across all zero-cost channels.
        """
        results: Dict[str, Any] = {
            "query": query,
            "channels": {},
            "total_signals": 0,
            "items": []
        }

        if include_reddit:
            reddit_items = self.search_reddit(query, limit=max_per_channel)
            results["channels"]["reddit"] = reddit_items
            results["items"].extend(reddit_items)

        if include_twitter:
            twitter_items = self.search_twitter(query, limit=max_per_channel)
            results["channels"]["twitter"] = twitter_items
            results["items"].extend(twitter_items)

        if include_youtube:
            youtube_items = self.search_youtube(query, limit=max_per_channel)
            results["channels"]["youtube"] = youtube_items
            results["items"].extend(youtube_items)

        if include_news:
            news_items = self.search_news(query, limit=max_per_channel)
            results["channels"]["news"] = news_items
            results["items"].extend(news_items)

        results["total_signals"] = len(results["items"])
        return results

    # ─────────────────────────────────────────────────────────────────────────
    # 7. DOCTOR / DIAGNOSTICS
    # ─────────────────────────────────────────────────────────────────────────
    def doctor(self) -> Dict[str, Any]:
        """
        Diagnostic health-check to verify reachability across zero-API channels.
        """
        diagnostics = {}
        
        # Test Reddit
        try:
            r = self.search_reddit("technology", limit=2)
            diagnostics["reddit"] = {"status": "ok" if r else "empty", "count": len(r)}
        except Exception as e:
            diagnostics["reddit"] = {"status": "error", "message": str(e)}

        # Test Twitter / X Web
        try:
            t = self.search_twitter("technology", limit=2)
            diagnostics["twitter"] = {"status": "ok" if t else "empty", "count": len(t)}
        except Exception as e:
            diagnostics["twitter"] = {"status": "error", "message": str(e)}

        # Test YouTube
        try:
            y = self.search_youtube("AI technology", limit=2)
            diagnostics["youtube"] = {"status": "ok" if y else "empty", "count": len(y)}
        except Exception as e:
            diagnostics["youtube"] = {"status": "error", "message": str(e)}

        # Test News
        try:
            n = self.search_news("technology", limit=2)
            diagnostics["news"] = {"status": "ok" if n else "empty", "count": len(n)}
        except Exception as e:
            diagnostics["news"] = {"status": "error", "message": str(e)}

        # Test Jina Reader
        try:
            j = self.read_article_markdown("https://example.com", max_chars=200)
            diagnostics["jina_reader"] = {"status": j.get("status", "error"), "chars": j.get("char_count", 0)}
        except Exception as e:
            diagnostics["jina_reader"] = {"status": "error", "message": str(e)}

        return diagnostics


# Global singleton instance
reach_scraper = AgentReachScraper()
