"""
Aegis Protocol — Scout Structured Metadata Extractor
=====================================================
Extracts JSON-LD schemas, OpenGraph, Twitter Cards, schema.org microdata,
and semantic HTML tags from raw web documents.
"""

import json
import logging
import re
from typing import Any, Dict, List, Optional
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)


class StructuredMetadataExtractor:
    """
    Extracts rich structured metadata from HTML.
    Prioritizes JSON-LD > OpenGraph > Twitter Cards > HTML5 elements.
    """

    def extract(self, html: str, base_url: str = "") -> Dict[str, Any]:
        result = {
            "title": "",
            "description": "",
            "author": "",
            "publisher": "",
            "published_at": "",
            "modified_at": "",
            "canonical_url": "",
            "body": "",
            "json_ld": [],
            "keywords": []
        }
        if not html:
            return result

        try:
            soup = BeautifulSoup(html, "html.parser")
        except Exception:
            return result

        # 1. JSON-LD Extraction
        for script in soup.find_all("script", type=lambda t: t and "ld+json" in t.lower()):
            try:
                data = json.loads(script.string or "")
                if isinstance(data, dict):
                    result["json_ld"].append(data)
                elif isinstance(data, list):
                    result["json_ld"].extend([d for d in data if isinstance(d, dict)])
            except Exception:
                continue

        # Inspect JSON-LD items for NewsArticle, Article, Report
        for ld in result["json_ld"]:
            t = ld.get("@type", "")
            if isinstance(t, list):
                t = " ".join(t)
            if any(k in str(t).lower() for k in ("article", "news", "report", "posting", "page")):
                if not result["title"] and ld.get("headline"):
                    result["title"] = str(ld.get("headline")).strip()
                if not result["description"] and ld.get("description"):
                    result["description"] = str(ld.get("description")).strip()
                if not result["published_at"] and ld.get("datePublished"):
                    result["published_at"] = str(ld.get("datePublished")).strip()
                if not result["modified_at"] and ld.get("dateModified"):
                    result["modified_at"] = str(ld.get("dateModified")).strip()
                if not result["author"]:
                    auth = ld.get("author")
                    if isinstance(auth, dict) and auth.get("name"):
                        result["author"] = str(auth.get("name")).strip()
                    elif isinstance(auth, list) and auth and isinstance(auth[0], dict):
                        result["author"] = str(auth[0].get("name", "")).strip()
                    elif isinstance(auth, str):
                        result["author"] = auth.strip()
                if not result["publisher"]:
                    pub = ld.get("publisher")
                    if isinstance(pub, dict) and pub.get("name"):
                        result["publisher"] = str(pub.get("name")).strip()

        # 2. OpenGraph & Meta Tags fallback
        def _get_meta(prop_names: List[str]) -> Optional[str]:
            for name in prop_names:
                tag = soup.find("meta", attrs={"property": name}) or soup.find("meta", attrs={"name": name})
                if tag and tag.get("content"):
                    return str(tag.get("content")).strip()
            return None

        if not result["title"]:
            result["title"] = _get_meta(["og:title", "twitter:title"]) or (soup.title.string.strip() if soup.title and soup.title.string else "")
        if not result["description"]:
            result["description"] = _get_meta(["og:description", "twitter:description", "description"]) or ""
        if not result["published_at"]:
            result["published_at"] = _get_meta([
                "article:published_time", "og:pubdate", "publication_date",
                "date", "dc.date", "sailthru.date", "parsely-pub-date"
            ]) or ""
        if not result["modified_at"]:
            result["modified_at"] = _get_meta(["article:modified_time", "og:updated_time", "last-modified"]) or ""
        if not result["author"]:
            result["author"] = _get_meta(["article:author", "author", "twitter:creator", "byl"]) or ""
        if not result["publisher"]:
            result["publisher"] = _get_meta(["og:site_name", "twitter:site", "publisher"]) or ""

        # Canonical Link
        can_link = soup.find("link", rel="canonical")
        if can_link and can_link.get("href"):
            result["canonical_url"] = str(can_link.get("href")).strip()

        # 3. Clean Content Body Extraction
        # Remove noisy elements
        for unwanted in soup.find_all(["script", "style", "nav", "footer", "aside", "noscript", "svg", "form", "iframe"]):
            unwanted.decompose()

        # Try semantic article containers first
        article_elem = soup.find("article") or soup.find("main") or soup.find("div", class_=lambda c: c and any(k in c.lower() for k in ("article-body", "story-body", "post-content", "entry-content")))
        target_container = article_elem if article_elem else soup.body or soup

        paragraphs = [p.get_text(separator=" ", strip=True) for p in target_container.find_all(["p", "h2", "h3", "li"])]
        clean_paragraphs = [p for p in paragraphs if len(p) > 20 and not any(k in p.lower() for k in ("cookie", "subscribe", "newsletter", "sign in", "all rights reserved"))]
        result["body"] = "\n\n".join(clean_paragraphs) if clean_paragraphs else target_container.get_text(separator=" ", strip=True)

        return result


structured_metadata_extractor = StructuredMetadataExtractor()
