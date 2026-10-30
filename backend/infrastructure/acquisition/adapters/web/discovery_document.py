"""Bounded observed feed/sitemap entries, never acquired article bodies.

The caller owns transport/SSRF validation. This parser makes no requests and
only resolves references actually present in a fetched document. A sitemap's
lastmod and Atom updated stay separate from publication declarations.
"""
import hashlib
import json
import re
from urllib.parse import urljoin, urlsplit, urlunsplit
from xml.etree import ElementTree as ET


def _tag(node):
    return node.tag.rsplit("}", 1)[-1].lower() if isinstance(node.tag, str) else ""


def _url(endpoint, value):
    try:
        if not value or not value.strip():
            return ""
        value = urljoin(endpoint, value.strip())
        parsed = urlsplit(value)
        if len(value) > 2000 or parsed.scheme not in {"http", "https"} or not parsed.hostname or parsed.username or parsed.password:
            return ""
        return urlunsplit((parsed.scheme, parsed.netloc, parsed.path, parsed.query, ""))
    except (AttributeError, ValueError):
        return ""


def _summary(raw):
    from bs4 import BeautifulSoup
    return BeautifulSoup(raw[:20_000], "html.parser").get_text(" ", strip=True)[:2000]


def drupal_search_document(raw, endpoint):
    """Observe search-card links in a fetched Drupal AJAX textarea envelope.

    Commands, scripts and settings are never executed. Only same-origin links
    inside article cards in an explicit search-results insertion are retained.
    This is discovery metadata, never article content or publication evidence.
    """
    if not isinstance(raw, str) or len(raw) > 1_000_000 or not raw.lstrip().startswith('<textarea>'):
        return None
    from bs4 import BeautifulSoup
    envelope = re.fullmatch(r'\s*<textarea>(.*)</textarea>\s*', raw, re.S)
    if not envelope:
        return None
    try:
        commands = json.loads(envelope.group(1))
    except (ValueError, TypeError, RecursionError):
        return None
    if not isinstance(commands, list) or not 1 <= len(commands) <= 100:
        return None
    origin, links, seen = urlsplit(endpoint), [], set()
    for command in commands:
        if (not isinstance(command, dict) or command.get('command') != 'insert'
                or command.get('method') not in {'replaceWith', 'html'}
                or not re.fullmatch(r'\.js-view-dom-id-search__[\w-]+', str(command.get('selector', '')))
                or not isinstance(command.get('data'), str)):
            continue
        fragment = BeautifulSoup(command['data'], 'html.parser')
        for card in fragment.select('article.story-card')[:100]:
            for node in card.select('h2 a[href], h3 a[href], a[href]:has(h2), a[href]:has(h3)')[:2]:
                url = _url(endpoint, node.get('href'))
                parsed = urlsplit(url)
                title = node.get_text(' ', strip=True)[:500]
                if (not url or not title or url in seen
                        or (parsed.scheme, parsed.netloc) != (origin.scheme, origin.netloc)):
                    continue
                seen.add(url)
                links.append({'url': url, 'text': title, 'kind': 'ARTICLE_LEAD',
                              'verification': 'OBSERVED_AJAX_SEARCH_LINK_UNVERIFIED'})
                if len(links) >= 100:
                    break
            if len(links) >= 100:
                break
        if len(links) >= 100:
            break
    if not links:
        return None
    return {'content_scope': 'PUBLIC_DISCOVERY_INDEX', 'source_type': 'SOURCE_INDEX',
            'title': 'Observed publisher search results', 'document_kind': 'DRUPAL_AJAX_SEARCH',
            'observed_links': links, 'discovery_links': [], 'entry_count': len(links),
            'body_quality': {'body_kind': 'UNCLASSIFIED_PAGE', 'evidence_qualified': False},
            'response_text_sha256': hashlib.sha256(raw.encode('utf-8')).hexdigest()}


def discovery_document(raw, endpoint, *, max_entries=100):
    """Return observed discovery metadata from already fetched XML bytes/text."""
    if isinstance(raw, bytes):
        raw = raw.decode("utf-8", errors="replace")
    if not isinstance(raw, str) or len(raw) > 1_000_000 or not raw.lstrip().startswith("<") or "<!DOCTYPE" in raw.upper() or "<!ENTITY" in raw.upper():
        return None
    try:
        root = ET.fromstring(raw)
    except ET.ParseError:
        return None
    kind = _tag(root)
    if kind not in {"rss", "feed", "rdf", "urlset", "sitemapindex"}:
        return None
    limit = max(1, min(int(max_entries), 200))
    feed = kind in {"rss", "feed", "rdf"}
    source = root.find("channel") if kind == "rss" else root
    source = source if source is not None else root
    identity = next(((node.text or "").strip() for node in source if _tag(node) == "title"), "")[:300]
    links, seen = [], set()
    # The byte cap bounds parser memory; the scan cap bounds dense indexes.
    for index, entry in enumerate(root.iter()):
        if index >= 5000:
            break
        if _tag(entry) not in {"item", "entry", "url", "sitemap"}:
            continue
        fields = {_tag(child): "".join(child.itertext()).strip() for child in entry}
        href = fields.get("loc")
        if not href:
            href = next(((child.text or "").strip() or child.get("href", "") for child in entry
                         if _tag(child) == "link" and child.get("rel", "alternate") == "alternate"
                         and child.get("type", "text/html") in {"text/html", "application/xhtml+xml"}), "")
        if not href:
            href = next(((child.text or "").strip() for child in entry if _tag(child) == "guid"
                         and child.get("isPermaLink", "true").lower() == "true"), "")
        base = entry.get("{http://www.w3.org/XML/1998/namespace}base") or root.get("{http://www.w3.org/XML/1998/namespace}base") or endpoint
        url = _url(urljoin(endpoint, base), href)
        if not url or url in seen:
            continue
        seen.add(url)
        news = next((node for node in entry if _tag(node) == "news"), None)
        news_fields = {_tag(node): "".join(node.itertext()).strip() for node in news} if news is not None else {}
        publication = next((node for node in news if _tag(node) == "publication"), None) if news is not None else None
        publisher = next(((node.text or "").strip() for node in publication if _tag(node) == "name"), "") if publication is not None else ""
        declared_source = next((node for node in entry if _tag(node) == "source"), None)
        if declared_source is not None and not publisher:
            publisher = (declared_source.text or "").strip()
        published = fields.get("published") or fields.get("pubdate") or news_fields.get("publication_date") or ""
        basis = ("ATOM:published" if fields.get("published") else "RSS:pubDate" if fields.get("pubdate")
                 else "NEWS_SITEMAP:publication_date" if news_fields.get("publication_date") else "")
        index_entry = _tag(entry) == "sitemap"
        row = {"url": url, "text": (fields.get("title") or news_fields.get("title") or "")[:500],
               "published": published[:100], "publication_time_source": basis,
               "modified": (fields.get("updated") or fields.get("lastmod") or "")[:100],
               "modified_time_source": "ATOM:updated" if fields.get("updated") else "SITEMAP:lastmod" if fields.get("lastmod") else "",
               "kind": "FEED_INDEX" if index_entry else "FEED_ENTRY" if feed else "ARTICLE_LEAD",
               "source_type": "SOURCE_INDEX" if index_entry else "FEED_ENTRY" if feed else "DISCOVERY_LEAD",
               "publisher": publisher[:200], "feed_identity": identity or endpoint,
               "feed_url": endpoint, "verification": "UNVERIFIED_FEED_LINK"}
        if feed:
            row["summary"] = _summary(fields.get("summary") or fields.get("description") or fields.get("encoded") or "")
        if declared_source is not None and declared_source.get("url"):
            row["publisher_source_url"] = _url(endpoint, declared_source.get("url"))
        links.append(row)
        if len(links) >= limit:
            break
    return {"content_scope": "FEED_INDEX" if feed else "SITEMAP_INDEX", "source_type": "SOURCE_INDEX",
            "observed_links": links, "discovery_links": [], "feed_identity": identity or endpoint,
            "title": identity or "Observed publisher discovery index", "document_kind": kind,
            "entry_count": len(links), "entries_truncated": len(links) >= limit}
