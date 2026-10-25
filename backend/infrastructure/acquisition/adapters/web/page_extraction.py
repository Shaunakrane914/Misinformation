"""Bounded observations from a fetched HTML page, never verified claims.

The caller owns the already-fetched, SSRF-validated document. Links and
publisher-declared JSON-LD are retained for inspection only; this module
neither follows them nor promotes them to independent corroboration.
"""

from __future__ import annotations

import json
import hashlib
import re
from datetime import datetime, timezone
from urllib.parse import urljoin, urlsplit, urlunsplit


_CORRECTION_PATTERN = re.compile(r"\b(?:correction|editor['’]s note|updated on)\b", re.I)
_DECLARED_FIELDS = ("@type", "headline", "datePublished", "dateModified", "description")
_ARTICLE_TYPES = {"Article", "NewsArticle", "ReportageNewsArticle", "AnalysisNewsArticle", "BlogPosting", "ScholarlyArticle"}


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
    # Compact issuer releases should get a read opportunity before large
    # auditor/financial statement bundles, without relaxing the byte limit.
    if re.search(r"press[-_. ]release|earnings[-_. ]release", text + " " + url, re.I):
        return -1
    if re.search(r"results for .*quarter|quarter.*ended|earnings.release|quarterly-results/.+/q[1-4]", text + " " + url, re.I):
        return 0
    if re.search(r"press.release|financial.statements|annual.report", text, re.I):
        return 1
    if re.search(r"quarter|results|filing|earnings|report|profit-loss|balance-sheet", text + " " + url, re.I):
        return 2
    return 3


def _semantic_root(soup):
    """Use the same source scope for text and linked-document observations."""
    explicit = soup.select('[itemprop="articleBody"]')
    if len(explicit) == 1:
        return explicit[0], "article_body"
    main = soup.find("main") or soup.find(attrs={"role": "main"})
    articles = (main or soup).find_all("article")
    if len(articles) == 1 and (main is None or len(articles[0].get_text()) >= len(main.get_text()) * 0.5):
        return articles[0], "article"
    # Common static publishing containers are structural observations. Require
    # a unique container with paragraphs so a list of story cards cannot win.
    containers = (main or soup).select('.article-body, .article-content, .story-body, .story-content, .entry-content, .post-content, .artText, .article_body, .storyContent, .articleWrap')
    containers = [node for node in containers if len(node.find_all("p")) >= 2]
    containers = [node for node in containers if not any(parent in containers for parent in node.parents)]
    if len(containers) == 1:
        return containers[0], "publisher_article_container"
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

    declarations = _declared_json_ld(soup)
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
    method = "DOM_SEMANTIC_TEXT"
    # Some legitimately accessible static pages expose the complete article
    # body in JSON-LD but only a short DOM shell. A description/headline never
    # substitutes for body text. Ambiguous distinct declarations are not used.
    bodies = list(dict.fromkeys(node["articleBody"] for node in declarations if node.get("articleBody")))
    if (len(bodies) == 1 and len(text.split()) < 80
            and len(bodies[0].split()) >= 40 and len(bodies[0].split()) > len(text.split()) * 2):
        body = BeautifulSoup(bodies[0], "html.parser")
        for hidden in body.select("script, style, noscript, template"):
            hidden.decompose()
        for node in body.find_all(("p", "h1", "h2", "h3", "li", "tr", "blockquote")):
            node.insert_before("\n\n")
            node.insert_after("\n\n")
        text = "\n\n".join(" ".join(value.split()) for value in re.split(r"\n\s*\n", body.get_text(" ")) if value.strip())
        scope, method = "declared_article_body", "PUBLISHER_JSONLD_ARTICLE_BODY"
    structure = observe_text_structure(text, [_text(node, 6000) for node in root.find_all(("h1", "h2", "h3", "h4"), limit=100)])
    return {"raw_text": raw, "text": text, **structure, "content_scope": scope,
            "selection_method": method, "extraction_method": method,
            "readable_word_count": len(text.split()), "readable_character_count": len(text),
            "readable_text_sha256": hashlib.sha256(text.encode("utf-8")).hexdigest(),
            "body_quality": _body_quality(root, text, scope, declared_article=any(
                node.get("@type") in _ARTICLE_TYPES for node in declarations))}


def _body_quality(root, text, scope, *, declared_article=False):
    """Observable extraction characteristics, not relevance or truth scores."""
    prose = [node.get_text(" ", strip=True) for node in root.find_all(("p", "blockquote"), limit=500)]
    link_chars = sum(len(node.get_text(" ", strip=True)) for node in root.find_all("a", limit=1000))
    total = max(1, len(root.get_text(" ", strip=True)))
    density = min(1.0, link_chars / total)
    article_scope = (scope in {"article", "article_body", "publisher_article_container", "declared_article_body"}
                     or (scope in {"main", "body_fallback"} and declared_article))
    # JSON-LD scope supplies an explicit body, not DOM paragraphs. The label
    # still describes an extraction observation, not acquired evidence quality.
    substantive = ((len(prose) >= 2 and sum(len(p.split()) >= 12 for p in prose) >= 2 and density < 0.35)
                   or scope == "declared_article_body")
    return {"paragraph_count": len(prose), "link_text_ratio": round(density, 4),
            "body_kind": "ARTICLE_BODY" if article_scope and substantive else "UNCLASSIFIED_PAGE",
            "basis": "OBSERVED_DOCUMENT_STRUCTURE", "evidence_qualified": False}


def observe_anchored_article_body(text, page):
    """Recover bounded prose spans when a page lacks an article DOM container.

    This consumes only an already-acquired capture and its exact observed
    heading offsets. A unique title heading, adjacent explicit byline/publication
    label and at least three substantial prose paragraphs are required. It does
    not infer the publisher's truth, publication timestamp or whole-page scope.
    Original text is never rewritten and unrelated story headings stop selection.
    """
    if not isinstance(page, dict) or page.get("content_scope") != "body_fallback" or not isinstance(text, str) or len(text) > 100_000:
        return None
    title = page.get("title")
    if not isinstance(title, str) or len(title.strip()) < 20:
        return None
    normalize = lambda value: " ".join(value.split()).casefold()
    headings = [row for row in page.get("text_blocks", []) if isinstance(row, dict)
                and row.get("role") == "HEADING" and type(row.get("start")) is int
                and type(row.get("end")) is int and 0 <= row["start"] < row["end"] <= len(text)]
    anchors = [row for row in headings if normalize(text[row["start"]:row["end"]]) == normalize(title)]
    if len(anchors) != 1:
        return None
    heading = anchors[0]
    blocks = list(re.finditer(r"\S[^\n]*(?:\n(?!\s*\n)[^\n]+)*", text[heading["end"]:]))
    if not blocks:
        return None
    byline = blocks[0]
    byline_text = byline.group().strip()
    if len(byline_text) > 300 or not re.fullmatch(
        r"(?:(?:Authored|Written)\s+)?By\s+.{2,100}?\s+(?:[|·]\s*)?(?:Published|Posted)\s*:.+",
        byline_text, re.I,
    ) or not re.search(r"\b(?:20\d{2}|Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?|Jul(?:y)?|Aug(?:ust)?|Sep(?:tember)?|Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?)\b", byline_text, re.I):
        return None
    byline_end = heading["end"] + byline.end()
    # A bounded partial article is preferable to silently swallowing a sidebar
    # or a second story. Short photo labels do not interrupt the initial prose.
    heading_starts = {row["start"] for row in headings}
    prose_starts = [byline_end + row.start()
        for row in re.finditer(r"\S[^\n]*(?:\n(?!\s*\n)[^\n]+)*", text[byline_end:byline_end + 6000])
        if byline_end + row.start() not in heading_starts and len(row.group().split()) >= 12
        and re.search(r"[.!?][\"'’”]?$", row.group().rstrip())]
    first_prose = min(prose_starts, default=len(text))
    section_label = re.compile(r"^(?:related(?: stories| articles| news)?|more(?: stories| articles| news)?|read more|recommended(?: stories| articles)?|navigation|latest news)\s*[:|—-]?$", re.I)
    boundaries = [row["start"] for row in headings if row["start"] >= byline_end
                  and (row["start"] > first_prose or len(text[row["start"]:row["end"]]) >= 40
                       or section_label.fullmatch(text[row["start"]:row["end"]].strip()))]
    stop = min([len(text), byline_end + 6000, *boundaries])
    spans = []
    heading_starts = {row["start"] for row in headings}
    for match in re.finditer(r"\S[^\n]*(?:\n(?!\s*\n)[^\n]+)*", text[byline_end:stop]):
        value = match.group().rstrip()
        start = byline_end + match.start()
        if (start in heading_starts or len(value.split()) < 12
                or not re.search(r"[.!?][\"'’”]?$", value)
                or re.match(r"(?:Also read|Read more|Related(?: stories| articles)?|Recommended)\s*(?:[|:—-]|$)", value, re.I)):
            continue
        spans.append({"start": start, "end": start + len(value)})
    if len(spans) < 3 or sum(len(text[row["start"]:row["end"]].split()) for row in spans) < 80:
        return None
    return {"basis": "OBSERVED_CAPTURED_TITLE_BYLINE_PROSE_SPANS", "scope": "PARTIAL_ARTICLE_SPANS",
            "source_text_sha256": hashlib.sha256(text.encode("utf-8")).hexdigest(),
            "title_heading": dict(heading), "byline_start": heading["end"] + byline.start(),
            "byline_end": byline_end, "spans": spans, "selection_end": stop,
            "publication_timestamp_inferred": False, "evidence_qualified": False}


def recovered_span_allowed(text, page, start, end):
    """Apply one exact captured-body boundary to all downstream consumers."""
    if not isinstance(page, dict) or "article_body_recovery" not in page:
        return True
    recovery = page["article_body_recovery"]
    if (not isinstance(recovery, dict) or not isinstance(text, str)
            or type(start) is not int or type(end) is not int or not 0 <= start < end <= len(text)
            or recovery.get("basis") != "OBSERVED_CAPTURED_TITLE_BYLINE_PROSE_SPANS"
            or recovery.get("source_text_sha256") != hashlib.sha256(text.encode("utf-8")).hexdigest()
            or not isinstance(recovery.get("spans"), list)):
        return False
    return any(type(row.get("start")) is int and type(row.get("end")) is int
        and 0 <= row["start"] <= start < end <= row["end"] <= len(text)
        for row in recovery["spans"][:50] if isinstance(row, dict))


def observe_text_structure(text, headings=()):
    """Exact captured spans, never inferred publication or effective dates."""
    blocks, dates = [], []
    known = {" ".join(value.split()) for value in (headings if isinstance(headings, (list, tuple)) else ()) if isinstance(value, str)}
    date_line = re.compile(r"^(?:(?:Published|Posted|Updated|Last updated)\s*:?\s*)?(?:(?:Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday),?\s+)?(?:January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{1,2},?\s+20\d{2}(?:\s+\d{1,2}:\d{2}\s*(?:AM|PM)?(?:\s+[A-Z]{2,5})?)?$", re.I)
    for index, match in enumerate(re.finditer(r"\S[^\n]*(?:\n(?!\s*\n)[^\n]+)*", text)):
        value = match.group().rstrip()
        if " ".join(value.split()) in known and len(blocks) < 100:
            blocks.append({"start": match.start(), "end": match.start() + len(value), "role": "HEADING"})
        if index < 12 and len(dates) < 4 and date_line.fullmatch(value):
            meaning = ("DECLARED_PUBLICATION_LABEL" if re.match(r"Published|Posted", value, re.I) else
                       "DECLARED_UPDATE_LABEL" if re.match(r"Updated|Last updated", value, re.I) else "UNSPECIFIED_DATE_LABEL")
            dates.append({"text": value, "start": match.start(), "end": match.start() + len(value),
                "meaning": meaning, "independently_verified": False})
    return {"text_blocks": blocks, "date_observations": dates}


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
        if not source or len(source) > 150_000:
            continue
        try:
            decoded = json.loads(source)
        except (TypeError, ValueError):
            continue
        nodes = decoded if isinstance(decoded, list) else [decoded]
        visited = 0
        while nodes and visited < 40:
            node = nodes.pop(0)
            visited += 1
            if not isinstance(node, dict):
                continue
            graph = node.get("@graph")
            if isinstance(graph, list):
                nodes.extend(graph[:30])
            for key in ("mainEntity", "mainEntityOfPage"):
                if isinstance(node.get(key), dict):
                    nodes.append(node[key])
            for candidate in [node]:
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
                types = candidate.get("@type", [])
                types = [types] if isinstance(types, str) else types if isinstance(types, list) else []
                article_types = [value for value in types if value in _ARTICLE_TYPES]
                if article_types:
                    observation["@type"] = article_types[0]
                    if isinstance(candidate.get("articleBody"), str):
                        observation["articleBody"] = candidate["articleBody"][:100_000]
                        observation["articleBody_truncated"] = len(candidate["articleBody"]) > 100_000
                    publisher = candidate.get("publisher")
                    if isinstance(publisher, dict) and isinstance(publisher.get("name"), str):
                        observation["publisher_name"] = publisher["name"][:200]
                    observation["declaration_basis"] = "PUBLISHER_JSONLD_UNVERIFIED"
                if observation:
                    declarations.append(observation)
                if len(declarations) >= 12:
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


def _publication_observations(soup, declarations):
    observations = []
    for node in soup.find_all("meta", limit=200):
        field = str(node.get("property") or node.get("name") or node.get("itemprop") or "")
        if field in {"article:published_time", "citation_publication_date", "datePublished"} and node.get("content"):
            observations.append({"value": str(node["content"])[:100], "source": "HTML_META:" + field})
    for node in soup.find_all("time", limit=30):
        if node.get("itemprop") == "datePublished" and node.get("datetime"):
            observations.append({"value": str(node["datetime"])[:100], "source": "HTML_TIME:datePublished"})
    for declaration in declarations:
        if declaration.get("@type") in _ARTICLE_TYPES and declaration.get("datePublished"):
            observations.append({"value": declaration["datePublished"][:100], "source": "JSONLD:datePublished"})
    return observations[:12]


def _publication_identity(value):
    """Normalize equivalent ISO timezone spellings, without inventing a zone."""
    val = value.strip()
    try:
        parsed = datetime.fromisoformat(val.replace("Z", "+00:00"))
        if parsed.tzinfo:
            parsed = parsed.astimezone(timezone.utc)
        return parsed.isoformat()
    except (ValueError, TypeError):
        pass
    m = re.match(r"^(\d{4}-\d{2}-\d{2}[ T]\d{2}:\d{2}:\d{2})\s*([A-Za-z_]+/[A-Za-z_]+)$", val)
    if m:
        dt_str, tz_name = m.groups()
        try:
            from zoneinfo import ZoneInfo
            parsed = datetime.fromisoformat(dt_str).replace(tzinfo=ZoneInfo(tz_name)).astimezone(timezone.utc)
            return parsed.isoformat()
        except Exception:
            pass
    return val


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
    links = links[:120]
    # Keep a separate, small navigation-discovery sample. These are hub leads,
    # not article text or verified ownership. A bounded same-publisher reader
    # may inspect them; never inject navigation into extracted body passages.
    discovery_links = []
    for node in soup.find_all("link", href=True, limit=100):
        rel = node.get("rel", [])
        if node.get("type", "").lower() in {"application/rss+xml", "application/atom+xml"} or "sitemap" in rel:
            href = _http_link(endpoint, str(node["href"]))
            if href:
                discovery_links.append({"url": href, "text": str(node.get("title") or "Observed publisher discovery index")[:160],
                                        "kind": "FEED_INDEX", "basis": "HTML_LINK_DECLARATION"})
        if len(discovery_links) >= 6:
            break
    for anchor in soup.select('nav a[href], footer a[href], [role="navigation"] a[href]')[:200]:
        title = _text(anchor, 160)
        href = _http_link(endpoint, str(anchor.get("href") or ""))
        if href and re.search(r"investor|financial results|newsroom|press releases|\bnews\b|\barchive\b|\bblog\b|scam|fraud alert|\brss\b|sitemap", title, re.I):
            discovery_links.append({"url": href, "text": title, "verification": "UNVERIFIED_NAVIGATION_LINK"})
        if len(discovery_links) >= 16:
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
    search_forms = []
    for form in soup.find_all("form", limit=20):
        if str(form.get("method", "get")).lower() != "get":
            continue
        field = next((node for node in form.find_all("input", limit=15)
                      if node.get("name") in {"s", "q", "search", "query"} and node.get("type", "text").lower() in {"text", "search"}), None)
        action = _http_link(endpoint, str(form.get("action") or endpoint))
        if field is not None and action and (urlsplit(action).hostname or "").lower() == origin:
            search_forms.append({"action": action, "parameter": field["name"], "basis": "OBSERVED_PUBLIC_GET_FORM"})
        if len(search_forms) >= 1:
            break
    for node in root.find_all(("p", "aside"), limit=300):
        value = _text(node, 500)
        if _CORRECTION_PATTERN.search(value):
            corrections.append(value)
        if len(corrections) >= 3:
            break
    declarations = _declared_json_ld(soup)
    dates = _publication_observations(soup, declarations)
    result = {
        "content_scope": content_scope,
        "observed_links": links,
        "discovery_links": discovery_links,
        "search_forms": search_forms,
        "tables": tables,
        "quotations": [_text(node, 500) for node in root.find_all("blockquote", limit=5)],
        "media_captions": [_text(node, 300) for node in root.find_all("figcaption", limit=5)],
        "potential_corrections": corrections,
        "declared_structured_data": declarations,
        "declared_open_graph": _declared_open_graph(soup),
        "publication_observations": dates,
        "parsed_html_sha256": hashlib.sha256(str(soup).encode("utf-8")).hexdigest(),
    }
    unique_dates = list(dict.fromkeys(row["value"] for row in dates))
    identities = {_publication_identity(value) for value in unique_dates}
    if unique_dates and len(identities) == 1:
        result["published"] = unique_dates[0]
        result["publication_time_source"] = ";".join(dict.fromkeys(row["source"] for row in dates))
    elif len(unique_dates) > 1:
        parsed_dts = []
        for v in identities:
            try:
                p = datetime.fromisoformat(v.replace("Z", "+00:00"))
                if p.tzinfo:
                    p = p.astimezone(timezone.utc)
                parsed_dts.append(p)
            except Exception:
                pass
        if len(parsed_dts) == len(identities) and len(parsed_dts) >= 2:
            if (max(parsed_dts) - min(parsed_dts)).total_seconds() <= 3 * 3600:
                result["published"] = unique_dates[0]
                result["publication_time_source"] = ";".join(dict.fromkeys(row["source"] for row in dates))
            else:
                result["publication_metadata_conflict"] = True
        else:
            result["publication_metadata_conflict"] = True
    headlines = list(dict.fromkeys(row["headline"] for row in declarations if row.get("@type") in _ARTICLE_TYPES and row.get("headline")))
    if len(headlines) == 1 and not soup.find("title"):
        result["title"] = headlines[0]
        result["title_source"] = "JSONLD:headline"
    return result
