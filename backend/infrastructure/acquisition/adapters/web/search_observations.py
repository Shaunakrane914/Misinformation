"""Request-local search observations; no singleton mutable investigation state."""
from contextlib import contextmanager
from contextvars import ContextVar
from urllib.parse import urlsplit, urlunsplit
import re

_search = ContextVar("search_observations", default=None)


@contextmanager
def capture_search(target="", domain=""):
    state = {"target": target, "domain": domain, "attempts": []}
    token = _search.set(state)
    try:
        yield state["attempts"]
    finally:
        _search.reset(token)


def public_locator(url):
    try:
        value = urlsplit(url or "")
        return urlunsplit((value.scheme, value.hostname or "", value.path, "", ""))[:500]
    except ValueError:
        return "INVALID_URL"


def begin_search(provider):
    row = {"provider": provider, "provider_invoked": True, "response_received": False,
           "status": "STARTED", "candidate_count": 0, "decisions": []}
    state = _search.get()
    if state is not None and len(state["attempts"]) < 12:
        state["attempts"].append(row)
    return row


def empty_search_failure(observations):
    """Do not call a swallowed transport failure a successful empty search.

    Legacy transport is explicitly uninstrumented. A completed empty or
    irrelevant instrumented response is not a transport failure.
    """
    measured = [row for row in observations if row.get("status") != "UNINSTRUMENTED_TRANSPORT"]
    if not measured or any(row.get("status") in {"NO_RESULTS", "IRRELEVANT_RESULTS", "CANDIDATES"} for row in measured):
        return None
    if all(row.get("status") in {"TIMEOUT", "TRANSPORT_FAILURE", "HTTP_ERROR"} for row in measured):
        status = "TIMEOUT" if all(row["status"] == "TIMEOUT" for row in measured) else "FAILED"
        return status, "Instrumented search providers failed; no candidates retained; legacy transport, if invoked, is unverified"
    return None


def result_fit(query, title, snippet, url, query_class=""):
    """Rank observed leads, never label a search snippet as an article body."""
    from backend.infrastructure.acquisition.adapters.web.search_matching import headline_overlap
    try:
        parsed = urlsplit(url or "")
        if parsed.scheme not in {"http", "https"} or not parsed.hostname or parsed.username or parsed.password:
            return 0.0, "INVALID_URL"
    except ValueError:
        return 0.0, "INVALID_URL"
    if query_class == "publisher_url_resolution":
        # A perfectly matching opaque feed wrapper still does not resolve an
        # article. Otherwise it suppresses the next bounded search provider,
        # only to be rejected by DeepReader after fallback has already ended.
        # Ordinary discovery retains these leads; this is a resolution-only
        # transport suitability decision, not a relaxed relevance/title gate.
        host = (parsed.hostname or "").lower().rstrip(".")
        if host == "news.google.com" or ((host == "bing.com" or host.endswith(".bing.com"))
                and parsed.path in {"/news/apiclick.aspx", "/ck/a"}):
            return 0.0, "UNRESOLVED_SEARCH_WRAPPER"
        score = headline_overlap(query, title)
        return score, None if score >= 0.75 else "HEADLINE_MISMATCH"
    text = f"{title} {snippet} {parsed.hostname} {parsed.path}".casefold()
    state = _search.get() or {}
    target = re.sub(r"\([^)]*\)", "", state.get("target") or "")
    subject = [word for word in re.findall(r"[a-z0-9]+", target.casefold())
               if len(word) >= 2 and word not in {"inc", "ltd", "limited", "corp", "corporation", "company"}]
    if subject:
        if state.get("domain") == "trending":
            from backend.services.research.entity_resolver import EntityResolver
            entity = EntityResolver.resolve_entity(target, domain="trending")
            _, _, rejection = EntityResolver.evaluate_entity_match(text, entity)
            if rejection:
                from backend.infrastructure.acquisition.adapters.web.search_matching import provisional_topic_overlap
                provisional = (str(query_class).startswith("harvest_")
                    and entity.entity_type in {"general", "topic", "concept"}
                    and provisional_topic_overlap(entity.canonical_name, f"{title} {snippet}"))
                if not provisional:
                    return 0.0, "SUBJECT_MISMATCH"
        elif not all(re.search(r"\b" + re.escape(word) + r"\b", text) for word in subject):
            return 0.0, "SUBJECT_MISMATCH"
    lexical_query = re.sub(r"\b(?:site|when|after|before):\S+", "", query, flags=re.I)
    terms = set(re.findall(r"[a-z0-9]{3,}", lexical_query.casefold())) - {
        "official", "source", "website", "latest", "independent", "reporting", "verified", "accounts"}
    hits = sum(bool(re.search(r"\b" + re.escape(term) + r"\b", text)) for term in terms)
    score = hits / max(1, len(terms))
    if len(terms) >= 3 and hits < 2:
        # An observed company hub can bootstrap issuer-document discovery. It
        # is weak discovery only, not a financial article or verified ownership.
        host_labels = (parsed.hostname or "").split(".")
        if (state.get("domain") == "financial" and subject and "".join(subject) in host_labels
                and re.fullmatch(r"/?(?:[a-z]{2}(?:-[a-z]{2})?/?)?", parsed.path, re.I)):
            return 0.10, None
        return score, "LOW_QUERY_COVERAGE"
    return score, None
