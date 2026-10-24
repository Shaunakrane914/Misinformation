"""Follow only observed same-publisher links, never constructed article URLs."""
import hashlib
import re
from urllib.parse import urlsplit, urlunsplit, urlencode, parse_qsl, unquote

from backend.services.research.research_models import EvidenceItem
from backend.services.research.content_roles import matches_objective
from backend.services.research.source_quality import canonical_hostname, hostname_matches
from backend.infrastructure.acquisition.adapters.web.search_observations import public_locator


def failed_feed_publisher_hubs(candidates, attempts, seen_urls):
    """Observed feed publishers are bounded discovery hubs, never article URLs.

    An unresolved wrapper must not loop through the same search engine. Reuse
    a feed-declared public hub only within the caller's remaining read slots;
    normal read transport still validates DNS/SSRF and access restrictions.
    """
    failed = {row.get("candidate_id") for row in attempts
              if row.get("failure_kind") == "PUBLISHER_UNRESOLVED"}
    hubs, seen = [], set(seen_urls)
    for candidate in candidates:
        if candidate.id not in failed:
            continue
        url = candidate.metadata.get("publisher_source_url") or ""
        try:
            parsed = urlsplit(url)
            valid = (parsed.scheme in {"http", "https"} and parsed.hostname and not parsed.username
                     and not parsed.password and not parsed.query and not parsed.fragment and is_publisher_hub(url))
        except ValueError:
            valid = False
        if not valid or url in seen:
            continue
        seen.add(url)
        hubs.append(EvidenceItem(id="ev_hub_" + hashlib.sha256(url.encode()).hexdigest()[:12],
            canonical_url=url, title="Feed-declared publisher hub: " + (parsed.hostname or ""),
            channel="web", source_domain=parsed.hostname or "", source_quality_score=0.5,
            query_class="observed_feed_publisher_hub", query_text=candidate.query_text,
            metadata={"discovered_on_candidate_id": candidate.id, "publisher_hop": 0,
                      "publisher_basis": "FEED_DECLARED_PUBLISHER_UNVERIFIED"}))
        if len(hubs) >= 2:
            break
    return hubs


def is_publisher_hub(url):
    path = urlsplit(url).path.strip("/").lower()
    return not path or bool(re.fullmatch(r"[a-z]{2}(?:[-/][a-z]{2})?", path) or re.search(
        r"(?:^|/)(?:news|newsroom|press|press-releases|investors|investor-relations|financial-results|reports|media|blog|archives?|search|sitemap(?:s)?|feed)(?:\.xml|\.html?)?$"
        r"|(?:^|/)archives?(?:/\d{4}(?:/\d{1,2})?|/page/\d+)$"
        r"|(?:^|/)(?:category|tag)/[\w-]+(?:/page/\d+)?$"
        r"|(?:^|/)(?:news|newsroom|press|blog)/page/\d+$", path))


def observed_publisher_articles(parent, domain, audit, target="", *, max_children=4, max_hops=2):
    """Rank bounded observed child leads; no body or evidence acceptance here.

    Expanded profiles may request more children/depth, within hard safety caps.
    The caller still owns total read/per-host/deadline budgets.
    """
    page = parent.metadata.get("page_metadata") or {}
    child_limit = max(1, min(int(max_children), 40))
    hop_limit = max(1, min(int(max_hops), 4))
    if (not parent.metadata.get("read_success") or parent.metadata.get("publisher_hop", 0) >= hop_limit
            or not (is_publisher_hub(parent.canonical_url) or page.get("content_scope") in {"FEED_INDEX", "SITEMAP_INDEX", "PUBLIC_DISCOVERY_INDEX"})):
        return []
    children, seen = [], {parent.canonical_url}
    origin = canonical_hostname(parent.canonical_url)
    links = (page.get("discovery_links", []) + page.get("observed_links", []))[:200]
    if target and parent.metadata.get("publisher_hop", 0) == 0:
        for form in page.get("search_forms", [])[:1]:
            parsed = urlsplit(form.get("action", ""))
            if (form.get("parameter") not in {"s", "q", "search", "query"} or parsed.username or parsed.password
                    or canonical_hostname(form.get("action", "")) != origin):
                continue
            params = dict(parse_qsl(parsed.query))
            params[form["parameter"]] = target[:100]
            links.insert(0, {"url": urlunsplit((parsed.scheme, parsed.netloc, parsed.path, urlencode(params), "")),
                "text": "Observed public publisher search", "kind": "FEED_INDEX"})
    tokens = set(re.findall(r"[a-z0-9]{3,}", target.lower()))
    def subject_hits(row):
        try:
            context = str(row.get("text", "")) + " " + unquote(urlsplit(str(row.get("url", ""))).path)
        except ValueError:
            context = ""
        words = set(re.findall(r"[a-z0-9]+", context.lower()))
        return len(tokens & words)
    def lead_priority(row):
        # A concrete observed subject article outranks another discovery hop.
        # Hostname presence alone is not title/topic relevance.
        return (-subject_hits(row), row.get("kind") == "FEED_INDEX")
    links.sort(key=lead_priority)
    for link in links:
        url, title = str(link.get("url") or ""), str(link.get("text") or "")
        try:
            parsed = urlsplit(url)
            valid = parsed.scheme in {"http", "https"} and parsed.hostname and not parsed.username and not parsed.password
        except ValueError:
            valid = False
        context = title + " " + url
        # Acquisition is deliberately broader than evidence qualification. An
        # on-subject article may be read before task/date/context is established.
        relevant = link.get("kind") == "FEED_INDEX" or subject_hits(link) > 0 or matches_objective(context, domain)
        if domain == "financial":
            relevant = relevant or bool(re.search(r"annual.report|investor|results|announc|appoint|chief.executive|\bceo\b|collaborat|partnership", context, re.I))
        elif domain == "personal":
            relevant = relevant or bool(re.search(r"statement|interview|speech|transcript", context, re.I))
        reason = ("INVALID_URL" if not valid else "DUPLICATE" if url in seen else
                  "NON_DOCUMENT_ASSET" if re.search(r"\.(?:svg|png|jpe?g|gif|webp|ico|css|js|woff2?|mp[34]|zip)$", parsed.path, re.I) else
                  "DIFFERENT_PUBLISHER" if not hostname_matches(canonical_hostname(url), origin) else
                  "NON_DOCUMENT" if re.search(r"(?:^|/)(?:login|signin|careers|privacy(?:-policy)?|terms(?:-of-use)?|contact|shop|cart)(?:/|$)", parsed.path, re.I) else
                  "OFF_OBJECTIVE" if not relevant else None)
        audit.append({"parent_id": parent.id, "url": public_locator(url), "title": title[:160], "discard_reason": reason})
        if reason:
            continue
        seen.add(url)
        children.append(EvidenceItem(id="ev_page_" + hashlib.sha256(url.encode()).hexdigest()[:12],
            canonical_url=url, title=title, snippet=link.get("summary") or title, channel="web", content_depth="INDEX_SNIPPET",
            source_name=link.get("publisher") or parent.source_name,
            source_domain=parsed.hostname or "", query_id=parent.query_id,
            published_at=link.get("published") or "",
            query_class="observed_publisher_article", query_text=parent.query_text,
            metadata={"discovered_on_url": parent.canonical_url, "discovered_on_candidate_id": parent.id,
                      "publisher_hop": parent.metadata.get("publisher_hop", 0) + 1, "linked_article_retrieved": False,
                      "discovery_kind": link.get("kind", "ARTICLE_LEAD"),
                      "source_type": "SOURCE_INDEX" if link.get("kind") == "FEED_INDEX" else "FEED_ENTRY" if link.get("kind") == "FEED_ENTRY" else "DISCOVERY_LEAD",
                      "publication_time_source": link.get("publication_time_source") or "",
                      "publisher_source_url": link.get("publisher_source_url") or "",
                      "feed_identity": link.get("feed_identity") or "",
                      "feed_url": link.get("feed_url") or ""}))
        if len(children) >= child_limit:
            break
    return children
