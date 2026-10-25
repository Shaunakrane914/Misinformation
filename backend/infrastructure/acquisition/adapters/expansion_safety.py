"""Shared safety boundary for the new adapter fleet, not provider approval.

Public documents remain source assertions. This boundary rejects forged host
claims, missing policy/configuration and metadata promoted to complete bodies.
"""
import functools
import contextvars
from contextlib import contextmanager
import os
import re
import urllib.parse
import zlib
import xml.etree.ElementTree as ET

from backend.infrastructure.acquisition.adapters.base import PlatformAdapter
from backend.infrastructure.acquisition.network.http import fetch_public_http as _fetch, BoundedHTTPResponse
from backend.services.url_validator import validate_url_safe
from backend.services.agent_reach.channels import FetchedDocument


HOSTS = {
    "wikipedia": ("wikipedia.org", "wikimedia.org"), "wikidata_exec": ("wikidata.org",),
    "sec_edgar": ("sec.gov",), "sec_filings_full": ("sec.gov",), "arxiv": ("arxiv.org",),
    "substack": ("substack.com",), "yahoo_finance": ("finance.yahoo.com",),
    "trustpilot": ("trustpilot.com", "sitejabber.com", "complaintsboard.com", "bbb.org"),
    "reddit_deep": ("reddit.com",), "bluesky": ("bsky.app",),
    "hackernews": ("news.ycombinator.com",), "telegram": ("t.me",),
    "factcheck": ("snopes.com", "politifact.com", "factcheck.org", "altnews.in", "boomlive.in", "fullfact.org"),
    "news": ("reuters.com", "reutersagency.com", "apnews.com", "bbc.com", "bbc.co.uk", "pib.gov.in", "aninews.in", "thehindu.com"),
}

_FETCH_OBSERVATIONS = contextvars.ContextVar("expanded_fetch_observations", default=None)


@contextmanager
def capture_adapter_fetches():
    observations = []
    token = _FETCH_OBSERVATIONS.set(observations)
    try:
        yield observations
    finally:
        _FETCH_OBSERVATIONS.reset(token)


def matches_host(url, hosts):
    try:
        parsed = urllib.parse.urlsplit(url)
        host = (parsed.hostname or "").lower().rstrip(".")
        return (parsed.scheme in {"http", "https"} and not parsed.username and not parsed.password
                and any(host == allowed or host.endswith("." + allowed) for allowed in hosts))
    except ValueError:
        return False


def policy_status(platform):
    if platform == "reddit_deep" and os.getenv("REDDIT_APPROVED_ACCESS", "false").lower() not in {"1", "true", "yes"}:
        return "POLICY_BLOCKED"
    if platform in {"sec_edgar", "sec_filings_full"}:
        agent = os.getenv("SEC_USER_AGENT", "").strip()
        if not agent or "@" not in agent or "\n" in agent or "\r" in agent:
            return "CONFIG_REQUIRED"
    if platform == "factcheck" and not os.getenv("GOOGLE_FACTCHECK_API_KEY", "").strip():
        return "AUTH_REQUIRED"
    return None


def bounded_decode(data, max_bytes=1_000_000):
    if len(data) > max_bytes:
        raise ValueError("Response byte budget exceeded")
    if not data.startswith(b"\x1f\x8b"):
        return data
    decoder = zlib.decompressobj(16 + zlib.MAX_WBITS)
    result = decoder.decompress(data, max_bytes + 1)
    if len(result) > max_bytes or decoder.unconsumed_tail or not decoder.eof or decoder.unused_data:
        raise ValueError("Compressed response byte budget exceeded or invalid entity")
    return result


def parse_bounded_xml(data):
    if len(data) > 1_000_000 or re.search(r"<!\s*(?:DOCTYPE|ENTITY)\b", data, re.I):
        raise ValueError("Unsafe or oversized XML")
    return ET.fromstring(data)


def safe_fetch(url, *, headers=None, timeout=5.0, max_bytes=1_000_000, **kwargs):
    headers = dict(headers or {})
    if matches_host(url, ("sec.gov",)):
        if policy_status("sec_edgar"):
            raise PermissionError("CONFIG_REQUIRED: SEC_USER_AGENT")
        headers = {key: value for key, value in headers.items() if key.lower() != "user-agent"}
        headers["User-Agent"] = os.environ["SEC_USER_AGENT"].strip()
    if matches_host(url, ("arctic-shift.photon-reddit.com", "reddit.com")) and policy_status("reddit_deep"):
        raise PermissionError("POLICY_BLOCKED: Reddit access")
    safe, _ = validate_url_safe(url)
    if not safe:
        raise PermissionError("URL_POLICY_REJECTED")
    # Initial-host access/config checks do not authorize another redirect host.
    # Fail before any follow-up transmission until adapters support per-hop
    # platform authorization and final-publisher identity. A caller must not
    # reopen redirects through transport kwargs. Ordinary native web reads keep
    # their separately validated redirect behavior.
    kwargs.pop("max_redirects", None)
    try:
        response = _fetch(url, headers=headers, timeout=min(float(timeout), 5.0),
                          max_bytes=min(max_bytes, 1_000_000), max_attempts=1, max_redirects=0, **kwargs)
        observations = _FETCH_OBSERVATIONS.get()
        if observations is not None:
            observations.append({"http_status": response.status_code, "host": urllib.parse.urlsplit(url).hostname})
        body = bounded_decode(response.body)
        return BoundedHTTPResponse(body=body, endpoint=response.endpoint, status_code=response.status_code,
            content_type=response.content_type, headers={key: value for key, value in response.headers.items()
                if key.lower() not in {"content-encoding", "set-cookie"}}, latency_ms=response.latency_ms,
            attempts=response.attempts, redirect_chain=response.redirect_chain)
    except PermissionError:
        raise
    except Exception as error:
        observations = _FETCH_OBSERVATIONS.get()
        if observations is not None:
            observations.append({"failure_type": type(error).__name__})
        raise RuntimeError("Bounded adapter transport failed: " + type(error).__name__) from None


class GuardedExpansionAdapter(PlatformAdapter):
    """Fail closed on direct calls as well as calls from the shared fabric."""
    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
        acquire = cls.__dict__.get("acquire")
        normalize = cls.__dict__.get("normalize")
        discover = cls.__dict__.get("discover")
        if acquire:
            @functools.wraps(acquire)
            def guarded_acquire(self, candidate, request):
                url = candidate.canonical_url or candidate.url
                blocked = policy_status(self.platform)
                if blocked or not matches_host(url, HOSTS.get(self.platform, ())):
                    return FetchedDocument(url=url, status=blocked or "URL_POLICY_REJECTED",
                        failure_reason=blocked or "Source host does not match adapter", backend_id=self.backend_id)
                return acquire(self, candidate, request)
            cls.acquire = guarded_acquire
        if discover:
            @functools.wraps(discover)
            def guarded_discover(self, query, limit=5):
                if policy_status(self.platform) or not str(query).strip() or limit <= 0:
                    return []
                selected = []
                for candidate in discover(self, query, min(int(limit), 5)):
                    url = candidate.canonical_url or candidate.url
                    owned = matches_host(url, HOSTS.get(self.platform, ()))
                    # API/feed-observed publisher links may leave the discovery
                    # host. They remain leads for the ordinary SSRF-safe reader;
                    # this does not authorize this adapter to acquire that host.
                    external_lead = self.platform in {"substack", "yahoo_finance", "news"} and validate_url_safe(url)[0]
                    if owned or external_lead:
                        candidate.metadata["discovery_only"] = True
                        selected.append(candidate)
                return selected[:limit]
            cls.discover = guarded_discover
        if normalize:
            @functools.wraps(normalize)
            def guarded_normalize(self, document, candidate, request):
                if (policy_status(self.platform) or document.status != "SUCCESS"
                        or not matches_host(document.url, HOSTS.get(self.platform, ()))
                        or not matches_host(candidate.canonical_url or candidate.url, HOSTS.get(self.platform, ()))):
                    return []
                fragments = normalize(self, document, candidate, request)
                for fragment in fragments:
                    fragment.raw_metadata["source_assertion_only"] = True
                    if self.platform in {"news", "substack", "yahoo_finance"}:
                        # A long page is not necessarily an article. Preserve the
                        # captured semantic scope at direct adapter boundaries too.
                        html = document.raw_metadata.get("source_html") or (document.raw_content if self.platform == "news" else "")
                        fragment.content_depth = "PARTIAL_CONTENT"
                        if html:
                            from bs4 import BeautifulSoup
                            from backend.infrastructure.acquisition.adapters.web.page_extraction import extract_readable_page
                            page = extract_readable_page(BeautifulSoup(html, "html.parser"))
                            fragment.content = page.pop("text")[:25_000]
                            page.pop("raw_text", None)
                            fragment.raw_metadata["page_metadata"] = page
                            if page.get("body_quality", {}).get("body_kind") == "ARTICLE_BODY":
                                fragment.content_depth = "FULL_ARTICLE"
                    if self.platform == "trustpilot":
                        fragment.content_depth = "SOCIAL_POST"
                        fragment.raw_metadata.update(source_role="COMMUNITY", content_scope="COMMUNITY_REVIEW_COLLECTION")
                    if self.platform in {"wikipedia", "wikidata_exec"}:
                        fragment.content_depth = "PROFILE_METADATA" if self.platform == "wikidata_exec" else "REFERENCE_TEXT"
                        fragment.raw_metadata.update(content_role="PROFILE" if self.platform == "wikidata_exec" else "BACKGROUND_REFERENCE",
                                                     primary_source=False, official_source=False, source_role="BACKGROUND")
                    elif self.platform == "arxiv":
                        fragment.content_depth = "DIRECT_ABSTRACT"
                        fragment.raw_metadata.update(content_scope="ABSTRACT_ONLY", full_paper_acquired=False, official_source=False)
                    elif self.platform in {"bluesky", "reddit_deep", "hackernews", "telegram"}:
                        fragment.content_depth = "SOCIAL_POST"
                        fragment.raw_metadata.update(source_role="COMMUNITY", virality_measured=False)
                    elif self.platform == "news" and document.retrieval_mode == "rss_feed":
                        fragment.content_depth = "SYNDICATED_SUMMARY"
                        fragment.raw_metadata.update(linked_article_retrieved=False)
                    fragment.raw_metadata.update(char_count=len(fragment.content or ""),
                                                 word_count=len((fragment.content or "").split()))
                return [fragment for fragment in fragments if (fragment.content or "").strip()]
            cls.normalize = guarded_normalize
        def can_handle(self, candidate):
            return matches_host(candidate.canonical_url or candidate.url, HOSTS.get(self.platform, ()))
        cls.can_handle = can_handle

    def health(self):
        blocked = policy_status(self.platform)
        return {"platform": self.platform, "backend_id": self.backend_id, "status": blocked or "NOT_PROBED",
                "auth_required": blocked in {"CONFIG_REQUIRED", "AUTH_REQUIRED"}, "live_health_verified": False}
