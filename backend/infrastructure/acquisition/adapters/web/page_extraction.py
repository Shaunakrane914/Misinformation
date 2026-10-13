"""Bounded observations from a fetched HTML page, never verified claims.

The caller owns the already-fetched, SSRF-validated document. Links and
publisher-declared JSON-LD are retained for inspection only; this module
neither follows them nor promotes them to independent corroboration.
"""

from __future__ import annotations

import json
import re
from urllib.parse import urljoin, urlsplit, urlunsplit


_CORRECTION_PATTERN = re.compile(r"\b(?:correction|editor['’]s note|updated on)\b", re.I)
_DECLARED_FIELDS = ("@type", "headline", "datePublished", "dateModified", "description")


def _text(node, limit: int) -> str:
    return node.get_text(" ", strip=True)[:limit]


def _http_link(base_url: str, href: str) -> str:
    if len(href) > 1000:
        return ""
    try:
        parsed = urlsplit(urljoin(base_url, href.strip()))
        if parsed.scheme.lower() not in ("http", "https") or not parsed.hostname:
            return ""
        if parsed.username or parsed.password:
            return ""
        return urlunsplit((parsed.scheme, parsed.netloc, parsed.path, parsed.query, ""))[:1000]
    except ValueError:
        return ""


def _declared_json_ld(soup) -> list[dict[str, str]]:
    declarations: list[dict[str, str]] = []
    for script in soup.find_all("script", attrs={"type": "application/ld+json"}, limit=6):
        source = script.string or script.get_text()
        if not source or len(source) > 20_000:
            continue
        try:
            decoded = json.loads(source)
        except (TypeError, ValueError):
            continue
        nodes = decoded if isinstance(decoded, list) else [decoded]
        for node in nodes:
            if not isinstance(node, dict):
                continue
            candidates = node.get("@graph") if isinstance(node.get("@graph"), list) else [node]
            for candidate in candidates[:5]:
                if not isinstance(candidate, dict):
                    continue
                observation = {
                    key: str(candidate[key])[:300]
                    for key in _DECLARED_FIELDS
                    if isinstance(candidate.get(key), str) and candidate[key].strip()
                }
                author = candidate.get("author")
                if isinstance(author, dict) and isinstance(author.get("name"), str):
                    observation["author_name"] = author["name"][:200]
                if observation:
                    declarations.append(observation)
                if len(declarations) >= 3:
                    return declarations
    return declarations


def _declared_open_graph(soup) -> dict:
    og: dict[str, str] = {}
    for tag in soup.find_all("meta", limit=50):
        prop = str(tag.get("property") or "")
        name = str(tag.get("name") or "")
        content = tag.get("content")
        if not isinstance(content, str) or not content.strip():
            continue
        val = content.strip()[:500]
        if prop == "og:description" or name == "description":
            og.setdefault("og_description", val)
        elif prop == "og:site_name":
            og["site_name"] = val
        elif prop == "og:type":
            og["og_type"] = val
        elif name == "twitter:creator":
            og["twitter_creator"] = val
        elif name == "twitter:site":
            og["twitter_site"] = val
        elif prop == "article:section":
            og["article_section"] = val
    return og


def extract_observed_page_details(soup, endpoint: str) -> dict:
    """Extract small source-context samples from article/main, or body fallback."""
    root = soup.find("article") or soup.find("main") or soup.body
    if root is None:
        return {"content_scope": "UNAVAILABLE", "observed_links": [], "tables": [],
                "quotations": [], "media_captions": [], "potential_corrections": [],
                "declared_structured_data": _declared_json_ld(soup),
                "declared_open_graph": _declared_open_graph(soup)}
    content_scope = "article" if root.name == "article" else "main" if root.name == "main" else "body_fallback"
    origin = (urlsplit(endpoint).hostname or "").lower()
    links: list[dict] = []
    seen: set[str] = set()
    for anchor in root.find_all("a", href=True, limit=200):
        href = _http_link(endpoint, str(anchor.get("href") or ""))
        if not href or href in seen:
            continue
        seen.add(href)
        links.append({
            "url": href,
            "text": _text(anchor, 160),
            "external_domain": (urlsplit(href).hostname or "").lower() != origin,
            "verification": "UNVERIFIED_PAGE_LINK",
        })
        if len(links) >= 20:
            break
    tables = []
    for table in root.find_all("table", limit=3):
        rows = []
        for row in table.find_all("tr", limit=10):
            cells = row.find_all(("th", "td"), limit=6)
            if cells:
                rows.append([_text(cell, 120) for cell in cells])
        if rows:
            tables.append(rows)
    corrections = []
    for node in root.find_all(("p", "aside"), limit=300):
        value = _text(node, 500)
        if _CORRECTION_PATTERN.search(value):
            corrections.append(value)
        if len(corrections) >= 3:
            break
    return {
        "content_scope": content_scope,
        "observed_links": links,
        "tables": tables,
        "quotations": [_text(node, 500) for node in root.find_all("blockquote", limit=5)],
        "media_captions": [_text(node, 300) for node in root.find_all("figcaption", limit=5)],
        "potential_corrections": corrections,
        "declared_structured_data": _declared_json_ld(soup),
        "declared_open_graph": _declared_open_graph(soup),
    }
