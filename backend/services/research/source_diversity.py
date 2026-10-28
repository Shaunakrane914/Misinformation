"""Publisher discovery hints, not access grants or source-quality assertions.

Search selectors broaden the existing web route. They never supply an article
URL, override provider restrictions, or authenticate ownership/independence.
No dedicated third-party account, paid API, or credentials are introduced.
"""
from urllib.parse import urlsplit
import re


SOURCE_FAMILIES = {
    "general_reporting": ("reuters.com", "apnews.com", "bbc.com"),
    "financial_reporting": ("cnbc.com", "marketwatch.com", "business-standard.com"),
    "regional_reporting": ("theguardian.com", "dw.com", "aljazeera.com"),
    "technology_reporting": ("arstechnica.com", "techcrunch.com", "theverge.com"),
    "science_reporting": ("nature.com", "sciencedaily.com", "phys.org"),
    "consumer_safety": ("cpsc.gov", "recalls.gov", "gov.uk"),
    "enforcement_reports": ("justice.gov", "cbp.gov", "europol.europa.eu"),
    "consumer_protection": ("ftc.gov", "europa.eu", "accc.gov.au"),
}
DOMAIN_FAMILIES = {
    "financial": ("financial_reporting", "general_reporting", "regional_reporting"),
    "trending": ("technology_reporting", "science_reporting", "general_reporting"),
    "brand": ("enforcement_reports", "consumer_safety", "consumer_protection"),
    "personal": ("general_reporting", "technology_reporting", "regional_reporting"),
}

FAMILY_ANGLES = {
    "consumer_safety": r"recall|safety|defect|hazard",
    "enforcement_reports": r"counterfeit|enforcement|seizure|trademark|lawsuit",
    "consumer_protection": r"phishing|complaint|fraud|scam|refund",
    "science_reporting": r"research|study|scientific",
    "financial_reporting": r"earnings|financial|revenue|quarter",
}


def diversify_search_plan(rows, target, domain, limit, context=None):
    """Substitute bounded family searches for repeated generic channel queries.

    Validated source-plan actions retain their priority. Scoped queries inherit
    the task and temporal hints of an existing row, so a false-quote request
    cannot silently become a generic biography or a stale Trending search.
    Domains are discovery hints only; runtime web policy still governs reads.
    """
    rows = list(rows)
    families = DOMAIN_FAMILIES.get(domain, ())
    from backend.services.research.topic_context import infer_context
    context = context or infer_context(target, target, domain=domain)
    topics = set(context.topics)
    if domain in {'trending', 'personal'}:
        if topics & {'bollywood', 'regional_cinema', 'film', 'hollywood', 'cricket', 'sports',
                     'politics', 'elections', 'false_quotes', 'health'}:
            # SourcePlanningEngine already supplies reviewed topic-family
            # actions. Never substitute technology feeds on past yield alone.
            families = ()
        elif not topics:
            families = ('general_reporting',)
    if limit < 6 or not families:
        return rows[:limit]
    planned = [row for row in rows if row.get("source_plan_action_id")]
    ordinary = [row for row in rows if not row.get("source_plan_action_id")]
    templates, seen = [], set()
    for row in rows:
        text = row.get("query_text", "")
        if row.get("channel") not in {"web", "news", "rss"} or not text or text in seen:
            continue
        seen.add(text)
        templates.append(row)
    reserve = min(len(families), max(0, limit - len(planned) - 2), 2 if limit < 10 else 3)
    if not templates or not reserve:
        return rows[:limit]
    selected = (planned + ordinary)[:limit - reserve]
    for index, family in enumerate(families[:reserve]):
        angle = FAMILY_ANGLES.get(family)
        # A recall authority hint should not accidentally inherit an unrelated
        # impersonation query merely because it occupied the next list index.
        # Select only existing user/task queries; never add an unrequested task.
        matching = [row for row in templates if angle and re.search(angle, row["query_text"], re.I)]
        template = matching[0] if matching else templates[index % len(templates)]
        # Existing user/site restrictions take precedence over our expansion.
        if "site:" in template["query_text"].casefold():
            continue
        selector = " OR ".join("site:" + host for host in SOURCE_FAMILIES[family])
        selected.append({**{key: value for key, value in template.items()
                            if key not in {"source_plan_action_id", "source_plan_action_ids"}},
                         "channel": "web", "query_id": "family_" + family,
                         "query_text": template["query_text"] + " (" + selector + ")",
                         "basis": "PUBLISHER_FAMILY_DISCOVERY_HINT", "source_family": family})
    # A skipped hint must not reduce the original request's search opportunity.
    for row in rows:
        if len(selected) >= limit:
            break
        if row not in selected:
            selected.append(row)
    hints = [row for row in selected if row.get("source_family")]
    base = [row for row in selected if not row.get("source_family")]
    insertion = min(len(base), len(planned) + 2)
    return (base[:insertion] + hints + base[insertion:])[:limit]


def publisher_host(url):
    """Observed host grouping only, not registrable ownership or corroboration."""
    try:
        host = (urlsplit(url or "").hostname or "").casefold()
        return host.removeprefix("www.")
    except ValueError:
        return ""
