"""
Aegis Protocol — Firecrawl Web Acquisition Adapter
===================================================
Provides high-fidelity, clean Markdown and structured metadata extraction
from permitted public web articles via Firecrawl API (Cloud or Self-Hosted).

Architectural Invariants & Safeguards:
1. Strict SSRF Defense: Validates target URLs with `is_safe_url` before transmission.
2. Honest Provenance: Distinguishes observed upstream metadata from inferred fields.
3. Bounded Resources: Enforces 5.0s network timeouts, 1MB response caps, and zero
   excessive paid retry loops.
4. Transport vs Relevance: Categorizes provider transport failures separately from
   relevance or content policy decisions.
5. Complementary Fallback: Operates as an opt-in, policy-compliant reader fallback,
   never bypassing site policies, paywalls, or access denials.
"""

from __future__ import annotations

import hashlib
import ipaddress
import json
import logging
import os
import re
import time
import urllib.parse
from typing import Any, Dict, List, Mapping, Optional

from backend.infrastructure.acquisition.adapters.base import PlatformAdapter
from backend.infrastructure.acquisition.network.http import (
    DEFAULT_MAX_RESPONSE_BYTES,
    BoundedHTTPResponse,
    ProviderHTTPError,
    decode_bounded_http_body,
    post_public_http,
    transport_failure_kind,
)
from backend.infrastructure.acquisition.security.url_validator import validation_failure_kind
from backend.services.agent_reach.channels import (
    CandidateSource,
    EvidenceFragment,
    FetchedDocument,
    RetrievalMode,
    RetrievalRequest,
)
from backend.services.url_validator import is_safe_url
from backend.infrastructure.acquisition.network.budget import acquisition_deadline, remaining_timeout
from backend.infrastructure.acquisition.adapters.web.page_extraction import extract_readable_page, extract_reader_markdown

logger = logging.getLogger(__name__)

# Environment variable keys
FIRECRAWL_API_BASE_URL_ENV = "FIRECRAWL_API_BASE_URL"
FIRECRAWL_API_KEY_ENV = "FIRECRAWL_API_KEY"
DEFAULT_FIRECRAWL_BASE_URL = "https://api.firecrawl.dev"


def _public_endpoint_origin(url):
    """A configuration summary must never echo credentials, query or path tokens.

    This is syntax/config validation only; actual egress still needs DNS/pinning
    in post_public_http. Health reads must not perform network diagnostics.
    """
    try:
        parsed = urllib.parse.urlsplit(url)
        if (parsed.scheme != "https" or not parsed.hostname or parsed.username or parsed.password
                or parsed.query or parsed.fragment or any(ord(c) < 33 for c in url)):
            return None
        host = parsed.hostname.lower().rstrip(".")
        if host == "localhost" or host.endswith((".localhost", ".local", ".internal")):
            return None
        try:
            address = ipaddress.ip_address(host)
        except ValueError:
            address = None
        if address is not None and not address.is_global:
            return None
        port = parsed.port  # Malformed ports must fail configuration, not health.
        host = "[" + host + "]" if ":" in host else host
        return "https://" + host + (":" + str(port) if port and port != 443 else "")
    except (TypeError, ValueError):
        return None


def _reported_failure(payload):
    """Interpret only provider failure metadata, never echo arbitrary errors."""
    if not isinstance(payload, dict):
        return None, None
    data = payload.get("data")
    meta = data.get("metadata") if isinstance(data, dict) else None
    observations = [payload]
    if isinstance(meta, dict):
        observations.append(meta)
    error = payload.get("error")
    if isinstance(error, dict):
        observations.append(error)
    for observed in observations:
        for key in ("statusCode", "status_code", "http_status", "status"):
            status = observed.get(key)
            if isinstance(status, (str, int)) and str(status).isdigit() and 300 <= int(status) <= 599:
                code = int(status)
                return ("RATE_LIMITED" if code == 429 else "ACCESS_DENIED" if code in (401, 403)
                        else "HTTP_FAILURE"), code
    # Some providers supply symbolic codes without an HTTP status. Preserve
    # explicit refusal/throttling semantics so a fallback cannot bypass them.
    labels = " ".join(str(row.get(key, "")) for row in observations
                      for key in ("code", "error_code", "error", "message"))[:4000].lower()
    if re.search(r"rate[ _-]?limit|too many requests|\b429\b", labels):
        return "RATE_LIMITED", 429
    if re.search(r"access[ _-]?denied|forbidden|robots|captcha|paywall|unauthori[sz]ed|login required|\b40[13]\b", labels):
        return "ACCESS_DENIED", 403
    return None, None


class FirecrawlAdapter(PlatformAdapter):
    """
    Platform adapter for Firecrawl web scraping and bounded crawling.
    Supports both official Firecrawl Cloud and self-hosted instances.
    """

    @staticmethod
    def _default_post(
        endpoint: str,
        *,
        method: str = "POST",
        headers: Mapping[str, str],
        body: bytes,
        timeout: float,
        max_bytes: int,
    ) -> BoundedHTTPResponse:
        if method != "POST":
            raise ValueError("Firecrawl only admits explicit POST requests")
        return post_public_http(endpoint, body=body, headers=headers, timeout=timeout, max_bytes=max_bytes)

    def __init__(
        self,
        base_url: Optional[str] = None,
        api_key: Optional[str] = None,
        timeout: float = 5.0,
        max_bytes: int = DEFAULT_MAX_RESPONSE_BYTES,
        http_fetcher: Optional[Any] = None,
    ):
        self._base_url = (base_url or os.environ.get(FIRECRAWL_API_BASE_URL_ENV)
                          or os.environ.get("FIRECRAWL_BASE_URL") or DEFAULT_FIRECRAWL_BASE_URL).rstrip("/")
        self._api_key = (os.environ.get(FIRECRAWL_API_KEY_ENV, "") if api_key is None else api_key).strip()
        self.timeout = min(5.0, max(0.01, float(timeout)))
        self.max_bytes = min(DEFAULT_MAX_RESPONSE_BYTES, max(1, int(max_bytes)))
        self._fetcher = http_fetcher if http_fetcher is not None else self._default_post

    @property
    def platform(self) -> str:
        return "firecrawl"

    @property
    def backend_id(self) -> str:
        return "firecrawl-v1"

    def is_configured(self) -> bool:
        """Check if Firecrawl is configured (has API key for cloud, or custom self-hosted endpoint)."""
        if not _public_endpoint_origin(self._base_url):
            return False
        parsed = urllib.parse.urlsplit(self._base_url)
        is_cloud = parsed.hostname.lower().rstrip(".") == "api.firecrawl.dev"
        if is_cloud:
            return bool(self._api_key)
        # Self-hosted does not strictly require an API key
        return bool(self._base_url)

    def can_handle(self, candidate: CandidateSource) -> bool:
        """Handle standard HTTP/HTTPS web documents when Firecrawl is configured."""
        if not self.is_configured():
            return False
        url = candidate.url.lower().strip()
        return url.startswith(("http://", "https://"))

    def health(self) -> Dict[str, Any]:
        """Expose capability status without leaking credentials."""
        configured = self.is_configured()
        try:
            is_cloud = (urllib.parse.urlsplit(self._base_url).hostname or "").lower().rstrip(".") == "api.firecrawl.dev"
        except ValueError:
            is_cloud = False
        return {
            "platform": self.platform,
            "backend_id": self.backend_id,
            "status": "CONFIGURED_UNVERIFIED" if configured else "CONFIG_REQUIRED",
            "is_cloud": is_cloud,
            "has_api_key": bool(self._api_key),
            "endpoint": _public_endpoint_origin(self._base_url),
            "timeout_seconds": self.timeout,
            "public_endpoint_required": True,
            "live_health_verified": False,
        }

    # ── Single Article Scraping ───────────────────────────────────────────────

    def scrape_article(
        self,
        url: str,
        timeout: Optional[float] = None,
        only_main_content: bool = True,
    ) -> Dict[str, Any]:
        """
        Scrape a single permitted web article and return clean markdown with provenance.
        """
        # DNS, provider transmission and parsing share one original deadline.
        try:
            with acquisition_deadline(time.monotonic() + remaining_timeout(min(self.timeout, timeout or self.timeout))):
                return self._scrape_article(url, only_main_content)
        except TimeoutError:
            return {"status": "failed", "failure_kind": "BUDGET_EXHAUSTED", "url": url,
                    "error": "Acquisition deadline exhausted", "transport": {"network_observed_this_attempt": False}}

    def _scrape_article(self, url, only_main_content):
        if not self.is_configured():
            return {"status": "failed", "failure_kind": "CONFIG_REQUIRED", "url": url,
                    "error": "Configure a public HTTPS Firecrawl endpoint and required credentials"}
        # 1. SSRF Validation on Target URL
        safe, reason = is_safe_url(url)
        if not safe:
            kind = validation_failure_kind(reason)
            return {
                "status": "blocked_ssrf" if kind == "SSRF_BLOCKED" else "failed",
                "failure_kind": kind,
                "error": f"Target URL failed safety validation: {reason}",
                "url": url,
                "rejection_layer": "SSRF",
                "transport": {"network_observed_this_attempt": False, "http_status": None},
            }

        # 2. SSRF Validation on Firecrawl Endpoint
        endpoint = f"{self._base_url}/v1/scrape"
        safe_endpoint, ep_reason = is_safe_url(endpoint)
        if not safe_endpoint:
            return {
                "status": "failed",
                "failure_kind": "SSRF_BLOCKED",
                "error": f"Firecrawl endpoint failed safety validation: {ep_reason}",
                "url": url,
                "rejection_layer": "SSRF",
            }

        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
            "User-Agent": "AegisProtocol/1.0 (Firecrawl Integration)",
        }
        if self._api_key:
            headers["Authorization"] = f"Bearer {self._api_key}"

        payload = {
            "url": url,
            "formats": ["markdown", "html"],
            "onlyMainContent": only_main_content,
            "timeout": max(1, int(remaining_timeout(self.timeout) * 1000)),
        }

        try:
            req_body = json.dumps(payload).encode("utf-8")
            response: BoundedHTTPResponse = self._fetcher(
                endpoint,
                method="POST",
                headers=headers,
                body=req_body,
                timeout=remaining_timeout(self.timeout),
                max_bytes=self.max_bytes,
            )

            raw_bytes = decode_bounded_http_body(response, max_bytes=self.max_bytes)
            if response.status_code is not None and response.status_code >= 400:
                raise ProviderHTTPError("Firecrawl HTTP failure", endpoint=endpoint, status_code=response.status_code,
                                        network_observed=True)
            parsed = json.loads(raw_bytes.decode("utf-8", errors="replace"))
            if not isinstance(parsed, dict):
                raise ValueError("Invalid provider response object")
            refusal, refusal_status = _reported_failure(parsed)
            if refusal:
                return {"status": "failed", "failure_kind": refusal,
                        "error": "Reader provider reported an upstream request failure",
                        "url": url, "transport": {
                            "endpoint": _public_endpoint_origin(endpoint), "http_status": refusal_status,
                            "latency_ms": response.latency_ms, "network_observed_this_attempt": True}}

            if not parsed.get("success", False):
                return {
                    "status": "failed",
                    "failure_kind": "PROVIDER_FAILURE",
                    "error": "Firecrawl extraction unsuccessful",
                    "url": url,
                    "transport": {
                        "endpoint": _public_endpoint_origin(endpoint),
                        "http_status": response.status_code,
                        "latency_ms": response.latency_ms,
                        "network_observed_this_attempt": True,
                    },
                }

            data = parsed.get("data", {})
            markdown_body = (data.get("markdown") or "").strip()
            meta = data.get("metadata", {})

            declared_url = meta.get("canonicalURL") or meta.get("sourceURL") or url
            # Remote canonical metadata is an observation, not permission to
            # replace the requested source with another origin/private locator.
            canonical_url = url
            if (urllib.parse.urlsplit(declared_url).hostname == urllib.parse.urlsplit(url).hostname
                    and is_safe_url(declared_url)[0]):
                canonical_url = declared_url
            title = meta.get("title") or ""
            description = meta.get("description") or ""
            published = meta.get("publishedTime") or meta.get("date") or ""
            status_code = meta.get("statusCode")
            try:
                status_code = int(status_code) if status_code is not None else None
            except (ValueError, TypeError):
                status_code = None

            # Respect upstream access denials: do not treat 401/403 or challenge pages as usable content
            if status_code in (401, 403, 429):
                return {
                    "status": "failed",
                    "failure_kind": "RATE_LIMITED" if status_code == 429 else "ACCESS_DENIED",
                    "error": f"Upstream publisher access denied (HTTP {status_code}); circumvention forbidden",
                    "url": url,
                    "title": title,
                    "canonical_url": canonical_url,
                    "transport": {
                        "endpoint": _public_endpoint_origin(endpoint),
                        "http_status": status_code,
                        "latency_ms": response.latency_ms,
                        "network_observed_this_attempt": True,
                    },
                }

            opening = re.sub(r"\s+", " ", markdown_body[:250]).strip().lower()
            if bool(re.match(r"^(?:#{1,3}\s*)?(?:just a moment|verify (?:that )?you are human|attention required|access denied|403 forbidden|checking your browser)", opening)):
                return {
                    "status": "failed",
                    "failure_kind": "ACCESS_DENIED",
                    "error": "Publisher challenge or access denial page; alternate extraction forbidden",
                    "url": url,
                    "title": title,
                    "canonical_url": canonical_url,
                    "transport": {
                        "endpoint": _public_endpoint_origin(endpoint),
                        "http_status": 403,
                        "latency_ms": response.latency_ms,
                        "network_observed_this_attempt": True,
                    },
                }

            # Check for empty body or trivial extraction
            word_count = len(markdown_body.split())
            if not markdown_body or len(markdown_body) < 50 or word_count < 15:
                return {
                    "status": "failed",
                    "failure_kind": "EMPTY_EXTRACTION",
                    "error": "Extracted document content too short or empty",
                    "url": url,
                    "title": title,
                    "canonical_url": canonical_url,
                    "transport": {
                        "endpoint": _public_endpoint_origin(endpoint),
                        "http_status": response.status_code,
                        "latency_ms": response.latency_ms,
                        "network_observed_this_attempt": True,
                    },
                }

            extracted = extract_reader_markdown(markdown_body)
            readable = markdown_body
            page = dict(extracted["page_metadata"])
            raw_capture = {**extracted["raw_capture"], "format": "markdown"}
            # An optional actual HTML capture supplies structural observations.
            # Markdown length alone cannot establish an article body, source
            # relevance, publication freshness, or completeness.
            html = data.get("html")
            if isinstance(html, str) and html.strip():
                from bs4 import BeautifulSoup
                observed = extract_readable_page(BeautifulSoup(html, "html.parser"))
                if observed["text"].strip():
                    readable = observed["text"]
                    page.update({key: value for key, value in observed.items() if key not in {"text", "raw_text"}})
                    raw_capture = {"text": observed["raw_text"][:100_000], "format": "html_visible_text",
                                   "html_sha256": hashlib.sha256(html.encode("utf-8")).hexdigest(),
                                   "truncated": len(observed["raw_text"]) > 100_000}
            return {
                "status": "success",
                "title": title,
                "content": readable,
                "markdown": readable,
                "url": url,
                "canonical_url": canonical_url,
                "published": published,
                "description": description,
                "char_count": len(readable),
                "backend": self.backend_id,
                "fallback_used": True,
                "fallback_backend": self.backend_id,
                "page_metadata": {
                    **page,
                    "title": title,
                    "description": description,
                    "published": published,
                    "language": meta.get("language"),
                    "status_code": meta.get("statusCode"),
                },
                "raw_capture": {
                    **raw_capture,
                    "sha256": hashlib.sha256(markdown_body.encode("utf-8")).hexdigest(),
                    "byte_count": len(markdown_body.encode("utf-8")),
                    "source": "firecrawl_api",
                },
                "transport": {
                    "endpoint": _public_endpoint_origin(endpoint),
                    "http_status": response.status_code,
                    "latency_ms": response.latency_ms,
                    "network_observed_this_attempt": True,
                },
            }

        except ProviderHTTPError as pe:
            f_kind = pe.failure_kind or "HTTP_FAILURE"
            return {
                "status": "failed",
                "failure_kind": f_kind,
                "error": "Firecrawl provider request failed",
                "url": url,
                "transport": {
                    "endpoint": _public_endpoint_origin(endpoint),
                    "http_status": pe.status_code,
                    "network_observed_this_attempt": pe.network_observed,
                },
            }
        except Exception as exc:
            f_kind = transport_failure_kind(exc)
            logger.debug("[FirecrawlAdapter] Scrape failed (%s)", f_kind)
            return {
                "status": "error",
                "failure_kind": f_kind,
                "error": "Firecrawl response could not be processed",
                "url": url,
                "transport": {
                    "endpoint": _public_endpoint_origin(endpoint),
                    "http_status": None,
                    "network_observed_this_attempt": True,
                },
            }

    # ── Bounded Website Crawling ──────────────────────────────────────────────

    def crawl_permitted_domain(
        self,
        domain_url: str,
        limit: int = 5,
        max_depth: int = 1,
    ) -> Dict[str, Any]:
        """
        Crawl a bounded set of discovered links on a permitted domain.
        Returns discovered URL list and extraction job pointer.
        """
        # Remote crawl jobs can outlive the original investigation and spend
        # credits outside its admission budget. Do not submit them implicitly.
        return {"status": "failed", "failure_kind": "UNSUPPORTED_OPERATION", "url": domain_url,
                "error": "Background crawl jobs are disabled; use bounded article reads", "links": []}

    # ── PlatformAdapter Implementation ────────────────────────────────────────

    def acquire(self, candidate: CandidateSource, request: RetrievalRequest) -> FetchedDocument:
        """Acquire document content and wrap in canonical FetchedDocument."""
        scrape_res = self.scrape_article(candidate.url)
        status_ok = scrape_res.get("status") == "success"
        content_body = scrape_res.get("markdown") or scrape_res.get("content") or ""
        cand_id = getattr(candidate, "candidate_id", getattr(candidate, "id", "cand_unknown"))

        return FetchedDocument(
            url=candidate.url,
            status="SUCCESS" if status_ok else "FAILED",
            backend_id=self.backend_id,
            retrieval_mode=RetrievalMode.WEB_READER.value,
            raw_content=content_body,
            raw_metadata={
                "source_id": cand_id,
                "platform": self.platform,
                "canonical_url": scrape_res.get("canonical_url") or candidate.url,
                "status_code": (scrape_res.get("transport") or {}).get("http_status"),
                "raw_capture": scrape_res.get("raw_capture") or {},
                "page_metadata": scrape_res.get("page_metadata") or {},
            },
            latency_ms=int((scrape_res.get("transport") or {}).get("latency_ms") or 0),
            failure_reason=scrape_res.get("error"),
        )

    def normalize(
        self,
        document: FetchedDocument,
        candidate: CandidateSource,
        request: RetrievalRequest,
    ) -> List[EvidenceFragment]:
        """Normalize acquired document into EvidenceFragment."""
        if document.status != "SUCCESS" or not document.raw_content:
            return []

        text = document.raw_content
        page = document.raw_metadata.get("page_metadata") or {}
        title = page.get("title") or candidate.title or "Firecrawl Extracted Document"
        canonical_url = document.raw_metadata.get("canonical_url") or candidate.url
        published = page.get("published") or getattr(candidate, "published", "") or ""
        score = getattr(candidate, "semantic_score", getattr(candidate, "score", 85.0))

        # Honest depth assessment: do not claim FULL_ARTICLE for snippets or partial text
        word_count = len(text.split())
        char_count = len(text)
        if word_count >= 40 and char_count >= 150:
            depth = "PARTIAL_CONTENT"
        else:
            depth = "SNIPPET"

        frag = EvidenceFragment(
            platform=self.platform,
            title=title,
            content=text,
            snippet=text[:400] if text else "",
            url=canonical_url,
            published=published,
            score=score,
            retrieval_method="firecrawl_v1_scrape",
            retrieval_mode=RetrievalMode.WEB_READER.value,
            native_backend_id=self.backend_id,
            channel_name="web",
            requested_channel="web",
            actual_retrieval_channel="firecrawl",
            content_depth=depth,
            query_id=request.query or "",
            raw_metadata={
                "source_role": "UNVERIFIED_SOURCE",
                "page_metadata": page,
                "raw_capture": document.raw_metadata.get("raw_capture") or {},
                "canonical_url": canonical_url,
                "content_hash": hashlib.sha256(text.encode("utf-8")).hexdigest(),
                "backend": self.backend_id,
                "extracted_word_count": word_count,
            },
        )
        return [frag]
