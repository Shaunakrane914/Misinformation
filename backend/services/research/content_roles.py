"""Conservative content-role/agent-objective heuristics, never truth judgments.

Raw captures remain unchanged. A rejected passage may still be inspected.
"""
import re
from urllib.parse import urlsplit


NON_EVENT_ROLES = {"AUTHOR_BIO", "NAVIGATION", "SOURCE_METADATA", "CMS_METADATA", "ASSET_METADATA", "LEGAL_DISCLOSURE", "LEGAL_NOTICE", "DOCUMENT_INDEX", "NEWS_INDEX", "LANDING_PAGE", "PROFILE"}
NON_EVENT_ROLES.add("BACKGROUND_REFERENCE")
NON_EVENT_ROLES.update({"QUESTION_PROMPT", "INSTRUCTIONAL_PROMPT"})
OBJECTIVE_TERMS = {
    "financial": r"revenue|earnings|profit|loss|financial|filing|quarter|guidance|dividend|stock|shares|accounting|debt|lawsuit|investigat|resign|acquisition|merger|regulator|appoint|chief.executive|\bCEO\b|executive.chair|leadership.transition|board.of.directors",
    "brand": r"counterfeit|impersonat|\bfake\b|replica|knockoff|\bclone\b|phishing|scam|fraud|complaint|recall|safety hazard|defective|trademark|lawsuit|unauthori[sz]ed|refund|delivery delayed|never received|poor service|giveaway|free gift",
    "personal": r"impersonat|deepfake|fabricat|fake (?:account|video|profile|quote)|false (?:claim|quote)|identity (?:abuse|theft)|scam|denied|denies|authentic|transcript",
}

# Small observed FR/ES vocabulary for native-text inspection, not translation
# or a general multilingual entailment claim. Whole words avoid name fragments.
LOCAL_BRAND_ABUSE = r"\b(?:arnaques?|fraudes?|contrefaçons?|estafas?|suplantación|falsificaciones?)\b"
LOCAL_BRAND_WARNING = r"\b(?:cuidado|méfiez|ne cliquez pas|no hagas clic|no pinches|protégez)\b"
LOCAL_BRAND_NEGATION = (r"\bno (?:es|son|se trata de) (?:(?:una?|unas?|unos?) )?(?:estafas?|fraudes?|falsificaciones?|falsificación)\b"
                       r"|\b(?:n['’]est|ne sont|ne constitue(?:nt)?) pas (?:(?:une?|des?|du) )?(?:arnaques?|fraudes?|contrefaçons?)\b")


def local_prose_predicate(text):
    """Require several language cues plus a standalone predicate, never a URL.

    Used only by deterministic prose selection; source assertions remain
    unverified and original source text is retained unchanged.
    """
    words = set(re.findall(r"[^\W\d_]+", text.casefold(), re.UNICODE))
    rules = [({"le", "la", "les", "des", "une", "avec", "pour", "dans", "vous", "votre", "cette"},
              r"est|sont|ont|affirme|offre|propose|annonce|signale|demande"),
             ({"el", "la", "los", "las", "una", "por", "para", "que", "con", "este", "esta", "del"},
              r"es|son|ha|han|dijo|ofrece|advierte|afirma|solicita|pide")]
    return any(len(words & cues) >= 3 and re.search(
        r'(?:^|[\s"(])(?:' + verbs + r")(?=$|[\s,.;:!?])", text, re.I)
        for cues, verbs in rules)


def paragraph_role(text):
    lower = text.casefold().strip()
    # An interrogative/quiz prompt is not an assertion, even when it contains a
    # target, financial numbers or words such as "declined". Do not reject a
    # reported quotation, an incident report containing a question, or a full
    # question-and-answer paragraph merely for containing a question mark.
    prompt = re.sub(r"^(?:(?:question|q)\s*\d*\s*[:.)-]\s*|\d+[.)]\s*)", "", lower)
    if prompt.endswith("?") and re.match(
            r"^(?:what|which|who|whom|whose|when|where|why|how|is|are|was|were|do|does|did|has|have|had|can|could|would|should|will)\b", prompt):
        return "QUESTION_PROMPT"
    if re.match(r"^(?:choose|select|pick|identify)\b", prompt) and re.search(
            r"\b(?:correct answer|one of the following|all that apply|answer below)\b", prompt):
        return "INSTRUCTIONAL_PROMPT"
    if re.match(r"^(?:card(?:title|description|image(?:alttext)?)|contenttype|cta\d(?:text|url)|badge(?:text|image))\b", lower) or re.fullmatch(
            r"style\s+(?:[\w-]+[ ,]*){1,8}|#[a-f0-9]{6}", lower):
        return "CMS_METADATA"
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
    if domain == "brand" and re.search(LOCAL_BRAND_ABUSE, text, re.I):
        return True
    if domain == "brand" and re.search(r"\b(?:giveaways?|sweepstakes|free gifts?)\b", text, re.I):
        # A promotional contest is not brand-abuse evidence merely because
        # scams can also use giveaways. Keep reported abuse, recalls, complaints
        # and observable credential/money solicitations investigable.
        incident = re.search(r"counterfeit|impersonat|fake|replica|phishing|scam|fraud|complaint|recall|hazard|defect|trademark|lawsuit|unauthori[sz]ed|refund|stolen|credential|password|decept|victim", text, re.I)
        solicitation = re.search(r"\b(?:crypto(?:currency)?|bitcoin|ethereum|btc|eth|usdt|wallets?)\b|\b(?:send|deposit|transfer|pay)\b.{0,55}\b(?:receive|double|return|back|prize)\b", text, re.I)
        if not incident and not solicitation:
            return False
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
    if page.get("content_scope") in {"FEED_INDEX", "SITEMAP_INDEX", "PUBLIC_DISCOVERY_INDEX"}:
        return "NEWS_INDEX"
    url = value("canonical_url", "") or value("url", "")
    host = (urlsplit(url).hostname or "").lower()
    if any(host == domain or host.endswith("." + domain) for domain in
           ("wikipedia.org", "wikimedia.org", "wiktionary.org", "britannica.com")):
        return "BACKGROUND_REFERENCE"
    path = urlsplit(url).path.lower().strip("/")
    if re.search(r"\.(?:svg|png|jpe?g|gif|webp|ico|css|js|woff2?|mp[34]|zip)$", path):
        return "ASSET_METADATA"
    if url and (not path or re.fullmatch(r"[a-z]{2}(?:[-/][a-z]{2})?", path) or is_careers_landing(url)):
        return "LANDING_PAGE"
    links = page.get("observed_links") or []
    # A semantic <article> can wrap a news listing. A collection endpoint with
    # several observed links is discovery context, not one acquired article.
    if (re.search(r"(?:^|/)(?:(?:news|newsroom|press-releases)|(?:category|tag)(?:/[^/]+)?)$", path)
            and len(links) >= 5 and not re.search(r"\b\d{4}\b|\.html?$", path)):
        return "NEWS_INDEX"
    document_links = sum(bool(re.search(r"\.pdf(?:[?#\s]|$)|financial|quarter|annual|statement", str(link.get("url", "")) + " " + str(link.get("text", "")), re.I))
                         for link in links if isinstance(link, dict))
    # A genuine HTML statement can link PDFs too. Look for actual numeric
    # financial prose/table content before treating a short link hub as an index.
    metrics = bool(re.search(r"(?:revenue|profit|earnings|income|assets|cash flow).{0,60}(?:[$₹€£]|\bINR\b|\bUSD\b|\d[\d,.]{2,})", text, re.I))
    if document_links >= 2 and not metrics and (len(text.split()) < 300 or len(re.findall(r"[.!?]\s", text)) < 3):
        return "DOCUMENT_INDEX"
    return "SUBSTANTIVE_CANDIDATE"
