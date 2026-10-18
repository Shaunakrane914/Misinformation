"""Bounded observations from a fetched HTML page, never verified claims.

The caller owns the already-fetched, SSRF-validated document. Links and
publisher-declared JSON-LD are retained for inspection only; this module
neither follows them nor promotes them to independent corroboration.
"""

from __future__ import annotations

import json
import hashlib
import re
from urllib.parse import urljoin, urlsplit, urlunsplit


_CORRECTION_PATTERN = re.compile(r"\b(?:correction|editor['’]s note|updated on)\b", re.I)
_DECLARED_FIELDS = ("@type", "headline", "datePublished", "dateModified", "description")


def extract_reader_markdown(raw: str) -> dict:
    """Select an observed reader heading before the caller's display cap.

    Reader envelopes can put thousands of navigation characters before an
    article. Only a unique explicit heading matching the declared title permits
    skipping that preamble. No keyword-based sentence removal, inferred main
    body, or fabricated metadata. Keep a bounded raw capture and source hash.
    """
    result = {"text": raw, "page_metadata": {}, "raw_capture": {
        "text": raw[:100_000], "truncated": len(raw) > 100_000,
        "selection_method": "READER_MARKDOWN_OBSERVED",
        "source_text_chars": len(raw),
        "source_text_sha256": hashlib.sha256(raw.encode("utf-8")).hexdigest(),
    }}
    marker = re.search(r"(?m)^Markdown Content:\s*\r?$", raw)
    if not marker:
        return result
    header = raw[:marker.start()]
    title_match = re.search(r"(?m)^Title: ([^\r\n]+)", header)
    if not title_match:
        return result
    title = title_match.group(1).strip()
    published = re.search(r"(?m)^Published Time: ([^\r\n]+)", header)
    start = marker.end()
    matches = []
    # Both ATX (#) and setext (underlined) headings are structural observations.
    headings = re.finditer(r"(?m)^(?:#{1,2}[ \t]+([^\r\n]+)|([^\r\n]+)\r?\n[=-]{3,}[ \t]*$)", raw[start:])
    normalize = lambda value: re.sub(r"\s+", " ", value.strip().strip("#* _")).casefold()
    for heading in headings:
        if normalize(heading.group(1) or heading.group(2)) == normalize(title):
            matches.append(start + heading.start())
    scope = "reader_body_unscoped"
    if len(matches) == 1:
        start = matches[0]
        scope = "reader_heading_match"
    result["text"] = raw[start:].strip()
    result["page_metadata"] = {"title": title[:500], "content_scope": scope,
                               "reader_declared_metadata_verified": False,
                               "reader_source_start": start}
    if published:
        result["page_metadata"]["published"] = published.group(1).strip()[:100]
    result["raw_capture"]["selection_method"] = scope.upper()
    return result


def document_link_priority(link):
    """Prefer observed result/release documents over navigation and ratio indexes."""
    text, url = str(link.get("text") or ""), str(link.get("url") or "")
    if re.search(r"results for .*quarter|quarter.*ended|earnings.release|quarterly-results/.+/q[1-4]", text + " " + url, re.I):
        return 0
    if re.search(r"press.release|financial.statements|annual.report", text, re.I):
        return 1
    if re.search(r"quarter|results|filing|earnings|report|profit-loss|balance-sheet", text + " " + url, re.I):
        return 2
    return 3


def _semantic_root(soup):
    """Use the same source scope for text and linked-document observations."""
    main = soup.find("main") or soup.find(attrs={"role": "main"})
    articles = (main or soup).find_all("article")
    if len(articles) == 1 and (main is None or len(articles[0].get_text()) >= len(main.get_text()) * 0.5):
        return articles[0], "article"
    if main is not None:
        return main, "main"
    return soup.body or soup, "body_fallback"


def extract_readable_page(soup) -> dict:
    """Select semantic document text without rewriting propositions.

    No network or model work. The separate raw text retains visible boilerplate
    for diagnosis. Only structural chrome is excluded; words such as 'scam',
    'not', 'correction' or 'cookie' never trigger prose deletion. Body fallback
    is explicitly weaker than an article/main selection, not full coverage.
    """
    from bs4 import BeautifulSoup

    original = BeautifulSoup(str(soup), "html.parser")
    for node in original.select("script, style, noscript, template"):
        node.decompose()
    raw = " ".join(original.stripped_strings)
    # A collection page must keep all its stories; never pick a random card.
    root, scope = _semantic_root(original)
    for node in list(root.select(
        'nav, footer, script, style, noscript, template, form, button, input, select, svg, '
        '[role="navigation"], [role="contentinfo"], [role="search"], [hidden], [aria-hidden="true"]'
    )):
        if node.parent is not None:
            node.decompose()
    # Preserve headers/bylines, asides/corrections, table rows and inline
    # negation. Blank lines are presentation boundaries, never summarization.
    for node in list(root.find_all(("p", "h1", "h2", "h3", "h4", "li", "tr", "pre", "blockquote", "figcaption"))):
        node.insert_before("\n\n")
        node.insert_after("\n\n")
    blocks = [" ".join(part.split()) for part in re.split(r"\n\s*\n", root.get_text(" "))]
    text = "\n\n".join(block for block in blocks if block)
    return {"raw_text": raw, "text": text, "content_scope": scope,
            "selection_method": "DOM_SEMANTIC_TEXT"}


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
    root, content_scope = _semantic_root(soup)
    if root is None:
        return {"content_scope": "UNAVAILABLE", "observed_links": [], "tables": [],
                "quotations": [], "media_captions": [], "potential_corrections": [],
                "declared_structured_data": _declared_json_ld(soup),
                "declared_open_graph": _declared_open_graph(soup)}
    origin = (urlsplit(endpoint).hostname or "").lower()
    links: list[dict] = []
    seen: set[str] = set()
    for anchor in root.find_all("a", href=True, limit=500):
        if anchor.find_parent(("nav", "footer")) or anchor.find_parent(attrs={"role": "navigation"}):
            continue
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
    # Document links often follow a large issuer menu. Preserve observed text
    # and URLs, but prioritize substantive documents within this bounded sample
    # rather than spending every slot on Home/Careers/contact links.
    links.sort(key=document_link_priority)
    links = links[:20]
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
