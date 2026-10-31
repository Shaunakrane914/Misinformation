"""Connect the repaired adapter fleet to bounded discovery and observed URL reads.

No alternative credentials, policy overrides, health probes or independent
verdict engine. Existing SEC/arXiv/Reddit/HN/ClaimReview routes remain canonical.
"""
import importlib
import json
from functools import lru_cache
from urllib.parse import urlsplit, quote

from backend.services.agent_reach.channels import CandidateSource, RetrievalRequest, EvidenceFragment, Channel, ChannelStatus
from backend.infrastructure.acquisition.adapters.expansion_safety import policy_status, safe_fetch, capture_adapter_fetches

ADAPTERS = {
    "sec_filings_full": ("regulatory.sec_filings_full", "SecFilingsFullAdapter"),
    "govuk": ("authoritative.govuk_public", "GovukPublicAdapter"),
    "wikipedia": ("encyclopedia.wikipedia", "WikipediaAdapter"),
    "substack": ("news.substack", "SubstackAdapter"),
    "yahoo_finance": ("financial.yahoo_finance", "YahooFinanceAdapter"),
    "trustpilot": ("consumer.trustpilot", "ConsumerReviewAdapter"),
    "wikidata_exec": ("governance.wikidata_exec", "WikidataExecutiveAdapter"),
    "bluesky": ("social.bluesky", "BlueskyAdapter"),
    "telegram": ("social.telegram", "TelegramPublicAdapter"),
    "news_wires": ("news.wires_adapter", "NewswireAdapter"),
    "gdelt": ("news.gdelt", "GdeltDocAdapter"),
    "cpsc_recalls": ("consumer.cpsc_recalls", "CpscRecallsAdapter"),
}
DOMAIN_DISCOVERY = {"financial": "yahoo_finance", "trending": "gdelt", "brand": "news_wires", "personal": "substack"}


@lru_cache(maxsize=1)
def get_expanded_adapters():
    return {name: getattr(importlib.import_module("backend.infrastructure.acquisition.adapters." + module), cls)()
            for name, (module, cls) in ADAPTERS.items()}


class ExpandedSourceChannel(Channel):
    @property
    def name(self):
        return "expanded_sources"

    def health_check(self):
        return ChannelStatus.NOT_PROBED

    def search(self, query, limit=3, **kwargs):
        key, separator, subject = query.partition("|")
        if not separator or key not in ADAPTERS:
            raise ValueError("Explicit supported adapter selector required")
        if policy_status(key):
            raise PermissionError(policy_status(key))
        adapter = get_expanded_adapters()[key]
        # Discovery returns leads only. Body acquisition happens in the ordinary
        # budgeted reader phase, not inside an extra unaccounted adapter sweep.
        with capture_adapter_fetches() as observations:
            candidates = adapter.discover(subject[:300], limit=min(3, max(0, limit)))
        if not candidates and observations and not any(200 <= row.get("http_status", 0) < 300 for row in observations):
            from backend.infrastructure.acquisition.network.http import ProviderHTTPError
            raise ProviderHTTPError("Expanded discovery providers failed; no acquired evidence",
                endpoint="", network_observed=any("http_status" in row for row in observations), attempts=len(observations))
        if key == 'cpsc_recalls':
            fragments = []
            for candidate in candidates:
                document = adapter.acquire(candidate, RetrievalRequest(task_type='READ'))
                for fragment in adapter.normalize(document, candidate, RetrievalRequest(task_type='READ')):
                    fragment.content_depth = 'STRUCTURED_PUBLIC_DATA'
                    fragment.channel_name = 'expanded_sources'
                    fragment.query_id = kwargs.get('query_id', '')
                    fragment.query_text = query
                    fragment.raw_metadata.update(body_acquired_during_discovery=True,
                        adapter_fetch_observations=observations[:12], source_family='cpsc',
                        source_role='PRIMARY', source_assertion_only=True)
                    fragments.append(fragment)
            return fragments
        return [EvidenceFragment(platform=key, channel_name=self.name, url=candidate.canonical_url or candidate.url,
            title=candidate.title, snippet=candidate.snippet, content="", content_depth="INDEX_SNIPPET",
            published=_publisher_observation(key, candidate.metadata).get('discovery_published_at', ''),
            author=_publisher_observation(key, candidate.metadata).get('discovery_author', ''),
            query_id=kwargs.get("query_id", ""), query_class=kwargs.get("query_class", "expanded_discovery"),
            query_text=query, native_backend_id=adapter.backend_id, retrieval_mode="direct_api",
            raw_metadata={"expanded_adapter": key, "linked_article_retrieved": False,
                          "discovery_only": True, "primary_source": False, "official_source": False,
                          "adapter_fetch_observations": observations[:12],
                          **_index_provenance(candidate.metadata),
                          **_publisher_observation(key, candidate.metadata)})
                for candidate in candidates]


def _publisher_observation(adapter, metadata):
    """Retain an explicit publisher date, never an index/creation timestamp.

    These are discovery hints. The acquired body must still pass its own date,
    subject and task gates. GDELT first-seen and CPSC issue observations keep
    their existing distinct provenance and never enter this publication field.
    """
    if adapter != 'news_wires' or not isinstance(metadata, dict):
        return {}
    publication = metadata.get('published')
    if (metadata.get('publication_time_basis') != 'PUBLISHER_FEED_DECLARATION'
            or not isinstance(publication, str) or not publication.strip()):
        return {}
    author = metadata.get('author')
    return {'discovery_published_at': publication[:100],
            'discovery_publication_basis': 'PUBLISHER_FEED_DECLARATION',
            'discovery_author': author[:300] if isinstance(author, str) else '',
            'discovery_date_requires_body_recheck': True}


def _index_provenance(metadata):
    """Carry an index's own observation provenance, never a publication date.

    The temporal guard reads ``published``/``published_at`` from item metadata, so
    those names (and any other date-like key) are deliberately not forwarded. A
    first-seen index time is retained only under its explicit ``gdelt_*`` name.
    """
    return {key: value for key, value in (metadata or {}).items()
            if key.startswith("gdelt_") or key == "publication_time_basis"} | {
        key: value for key, value in (metadata or {}).items()
        if key in {"cpsc_recall_id", "cpsc_api_url", "cpsc_record_index", "cpsc_issue_date"}}


def expanded_query(request, research_context=None):
    topics = set((research_context or {}).get('topics', []))
    if request.domain == 'personal' and topics & {'bollywood', 'regional_cinema', 'film', 'hollywood', 'cricket', 'sports', 'politics', 'elections'}:
        # A generic newsletter adapter is not a default celebrity/sports source.
        return None
    key = DOMAIN_DISCOVERY.get(request.domain)
    if request.domain == 'brand' and any(word in (getattr(request, 'intent', '') + ' ' + (getattr(request, 'extra_params', {}) or {}).get('claim_text', '')).lower()
                                        for word in ('recall', 'safety', 'hazard')):
        key = 'cpsc_recalls'
    # GOV.UK API adapter remains explicit-pilot only pending retained body proof.
    if not key:
        return None
    return {"channel": "expanded_sources", "operation": "search", "query_id": "expanded_01",
            "query_class": "expanded_discovery", "query_text": key + "|" + request.target,
            "basis": "BOUNDED_ADAPTER_DISCOVERY_NOT_EVIDENCE"}


def read_expanded_url(url, max_chars=20_000):
    """Read an observed source URL through its host-specific adapter, once.

    Return None only when the existing web reader should handle this host. A
    recognized access failure is terminal here, never a reason to bypass it.
    """
    from backend.infrastructure.acquisition.adapters.authoritative.sec_edgar import read_sec_financial_url
    structured = read_sec_financial_url(url, max_chars=max_chars)
    if structured is not None:
        return structured
    from backend.infrastructure.acquisition.adapters.regulatory.sec_filings_full import sec_filing_locator
    selected = next(((key, adapter) for key, adapter in get_expanded_adapters().items()
                     if key != 'cpsc_recalls' and (key != 'govuk' or urlsplit(url).path.startswith('/government/speeches/'))
                      and (key != 'sec_filings_full' or sec_filing_locator(url))
                     and adapter.can_handle(CandidateSource(url=url))), None)
    if selected is None:
        return None
    key, adapter = selected
    candidate = CandidateSource(url=url, canonical_url=url, platform=key)
    if key == "bluesky":
        parts = urlsplit(url).path.strip("/").split("/")
        if len(parts) != 4 or parts[0] != "profile" or parts[2] != "post":
            return {"status": "failed", "url": url, "failure_kind": "UNSUPPORTED_SOURCE", "content": ""}
        uri = "at://" + parts[1] + "/app.bsky.feed.post/" + parts[3]
        response = safe_fetch("https://public.api.bsky.app/xrpc/app.bsky.feed.getPostThread?uri=" + quote(uri, safe=""))
        if response.status_code != 200:
            return {"status": "failed", "url": url, "failure_kind": "HTTP_FAILURE", "content": ""}
        post = json.loads(response.body).get("thread", {}).get("post", {})
        candidate.metadata.update(post_text=post.get("record", {}).get("text", ""),
            created_at=post.get("record", {}).get("createdAt"), author_handle=post.get("author", {}).get("handle"))
    document = adapter.acquire(candidate, RetrievalRequest(task_type="READ"))
    if document.status != "SUCCESS":
        return {"status": "failed", "url": url, "failure_kind": document.status,
                "error": document.failure_reason or document.status, "content": "", "backend": adapter.backend_id}
    fragments = adapter.normalize(document, candidate, RetrievalRequest(task_type="READ"))
    if not fragments:
        return {"status": "failed", "url": url, "failure_kind": "EMPTY_CONTENT", "content": ""}
    fragment = fragments[0]
    content, page = fragment.content or "", {"content_scope": "UNCLASSIFIED_PAGE"}
    html = document.raw_metadata.get("source_html") or (document.raw_content if key == "news_wires" else "")
    if html and key != "trustpilot":
        from bs4 import BeautifulSoup
        from backend.infrastructure.acquisition.adapters.web.page_extraction import extract_readable_page, extract_observed_page_details, _publication_identity
        soup = BeautifulSoup(html, "html.parser")
        page = extract_observed_page_details(soup, document.url or url)
        readable = extract_readable_page(soup)
        content = readable.pop("text")
        readable.pop("raw_text", None)
        page.update(readable)
        if key == "substack" and document.raw_metadata.get("source_html_basis") == "CAPTURED_POST_BODY_HTML":
            # A captured API body_html field is an observed article-body field,
            # not a search headline. Ordinary HTML still needs semantic spans.
            if len(content.split()) >= 40 and "<p" in html:
                page["body_quality"] = {"body_kind": "ARTICLE_BODY", "basis": "CAPTURED_POST_BODY_HTML"}
            # These fields came with this acquired post body, not its feed/search
            # candidate. Missing metadata stays missing; updates are not dates.
            published = document.raw_metadata.get("published")
            if isinstance(published, str) and published.strip() and not page.get("publication_metadata_conflict"):
                if page.get("published") and _publication_identity(page["published"]) != _publication_identity(published):
                    page["publication_metadata_conflict"] = True
                    page.pop("published", None)
                else:
                    page.update(published=published[:100], publication_time_source="CAPTURED_POST_API:post_date")
            for field in ("author", "title"):
                if isinstance(document.raw_metadata.get(field), str):
                    page[field] = document.raw_metadata[field][:500]
    if key == 'govuk':
        page.update(document.raw_metadata.get('page_metadata') or {})
        page.update(published=document.raw_metadata.get('published'), author='',
                    licence_urls=['https://www.nationalarchives.gov.uk/doc/open-government-licence/version/3/'])
    if key == 'sec_filings_full':
        page.update(document.raw_metadata.get('page_metadata') or {})
    if fragment.content_depth in {"REFERENCE_TEXT", "PROFILE_METADATA"}:
        page.update(content_scope="PROFILE" if key == "wikidata_exec" else "BACKGROUND_REFERENCE",
                    body_kind="UNCLASSIFIED_PAGE")
    if key == "trustpilot":
        fragment.content_depth = "SOCIAL_POST"
        page["content_scope"] = "COMMUNITY_REVIEW_COLLECTION"
    original_length = len(content)
    content = content[:max(0, min(25_000, max_chars))]
    if key == 'govuk' and isinstance(page.get('published_address'), dict) and len(content) != original_length:
        import hashlib
        page['published_address'] = {**page['published_address'], 'start':0, 'end':len(content),
            'source_text_sha256':hashlib.sha256(content.encode('utf-8')).hexdigest()}
    if not content.strip():
        return {"status": "failed", "url": url, "failure_kind": "EMPTY_CONTENT", "content": ""}
    return {"status": "success", "url": url, "title": fragment.title, "content": content, "markdown": content,
            "content_depth": fragment.content_depth, "page_metadata": page, "backend": adapter.backend_id,
            "truncated": original_length > len(content) or document.raw_metadata.get('body_truncated', False),
            **({"transport": document.raw_metadata['transport']} if 'transport' in document.raw_metadata else {}),
            "source_completeness": "BOUNDED_CAPTURE_NOT_COMPLETE_WEBSITE"}
