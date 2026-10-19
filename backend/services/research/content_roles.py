"""Conservative content-role/agent-objective heuristics, never truth judgments.

Raw captures remain unchanged. A rejected passage may still be inspected.
"""
import re
from urllib.parse import urlsplit


NON_EVENT_ROLES = {"AUTHOR_BIO", "NAVIGATION", "SOURCE_METADATA", "LEGAL_DISCLOSURE", "LEGAL_NOTICE", "DOCUMENT_INDEX", "LANDING_PAGE", "PROFILE"}
OBJECTIVE_TERMS = {
    "financial": r"revenue|earnings|profit|loss|financial|filing|quarter|guidance|dividend|stock|shares|accounting|debt|lawsuit|investigat|resign|acquisition|merger|regulator",
    "brand": r"counterfeit|impersonat|\bfake\b|replica|knockoff|\bclone\b|phishing|scam|fraud|complaint|recall|safety hazard|defective|trademark|lawsuit|unauthori[sz]ed|refund|delivery delayed|never received|poor service|giveaway|free gift",
    "personal": r"impersonat|deepfake|fabricat|fake (?:account|video|profile|quote)|false (?:claim|quote)|identity (?:abuse|theft)|scam|denied|denies|authentic|transcript",
}


def paragraph_role(text):
    lower = text.casefold().strip()
    # Reader wrappers and links may repeat incident terms in a URL/title. They
    # are inspectable provenance, not a captured account of that incident.
    if re.match(r"^(?:title|url source|published time|markdown content):", lower):
        return "SOURCE_METADATA"
    if re.fullmatch(r"(?:\s*(?:[*_-]\s*)?(?:!?\[[^\n]*\]\([^\n]*\)|https?://\S+)\s*)+", text.strip()):
        return "NAVIGATION"
    if len(lower) < 700 and ("all rights reserved" in lower or "trademarks of the respective" in lower):
        return "LEGAL_NOTICE"
    if re.search(r"(?:about the author|author bio(?:graphy)?|\bcovering\b.{0,100}\bfor\b.{0,80}\bsince\b|\b(?:journalist|reporter|editor)\b.{0,70}\b(?:covers|covering|writes about)\b)", lower):
        return "AUTHOR_BIO"
    if any(x in lower for x in ("forward-looking statements", "certain statements in this press release", "safe harbor statement")):
        return "LEGAL_DISCLOSURE"
    if sum(x in lower for x in ("toggle navigation", "privacy policy", "contact us", "add to cart", "shop all", "all rights reserved")) >= 2:
        return "NAVIGATION"
    return "SUBSTANTIVE_CANDIDATE"


def matches_objective(text, domain=""):
    pattern = OBJECTIVE_TERMS.get(domain)
    return not pattern or bool(re.search(pattern, text, re.I))


def is_careers_landing(url):
    path = urlsplit(url).path.lower().strip("/")
    return bool(re.search(r"(?:^|/)(?:global-careers|careers|jobs|job-search)(?:\.html)?$", path))


def background_read_reason(item, domain):
    """Defer known background destinations, not unfamiliar publishers/reports."""
    url = item.canonical_url or ""
    parsed = urlsplit(url)
    text = f"{item.title} {item.snippet}"
    if domain in {"brand", "personal"} and not matches_objective(text, domain):
        path = parsed.path.lower().strip("/")
        encyclopedia = (parsed.hostname or "").endswith(".wikipedia.org")
        storefront = bool(re.search(r"(?:^|/)(?:store|shop|nike_store|men|women)(?:/|$)", path))
        landing = not path or bool(re.fullmatch(r"[a-z]{2}(?:[-/][a-z]{2})?", path))
        if encyclopedia or storefront or landing:
            return "background_not_agent_objective"
    return ""


def contains_word_or_phrase(text, terms):
    """A keyword is not a substring of an unrelated product/person name."""
    return any(re.search(r"(?<!\w)" + re.escape(term) + r"(?!\w)", text, re.I) for term in terms)


def document_role(item):
    """Role from captured structure, not ownership or publisher-declared trust."""
    value = item.get if isinstance(item, dict) else lambda key, default=None: getattr(item, key, default)
    depth = value("content_depth", "")
    if depth in {"PROFILE_METADATA", "VIDEO_METADATA", "DIRECT_METADATA", "METADATA"}:
        return "PROFILE" if depth == "PROFILE_METADATA" else "METADATA"
    text = value("content", "") or value("snippet", "") or ""
    meta = value("metadata", {}) or {}
    page = meta.get("page_metadata") or {}
    url = value("canonical_url", "") or value("url", "")
    path = urlsplit(url).path.lower().strip("/")
    if url and (not path or re.fullmatch(r"[a-z]{2}(?:[-/][a-z]{2})?", path) or is_careers_landing(url)):
        return "LANDING_PAGE"
    links = page.get("observed_links") or []
    document_links = sum(bool(re.search(r"\.pdf(?:[?#\s]|$)|financial|quarter|annual|statement", str(link.get("url", "")) + " " + str(link.get("text", "")), re.I))
                         for link in links if isinstance(link, dict))
    # A genuine HTML statement can link PDFs too. Look for actual numeric
    # financial prose/table content before treating a short link hub as an index.
    metrics = bool(re.search(r"(?:revenue|profit|earnings|income|assets|cash flow).{0,60}(?:[$₹€£]|\bINR\b|\bUSD\b|\d[\d,.]{2,})", text, re.I))
    if document_links >= 2 and not metrics and (len(text.split()) < 300 or len(re.findall(r"[.!?]\s", text)) < 3):
        return "DOCUMENT_INDEX"
    return "SUBSTANTIVE_CANDIDATE"
