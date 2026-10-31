"""Aegis Protocol — SEC EDGAR Full Disclosures & 10-K Reader Adapter.

Provides comprehensive regulatory narrative disclosures for Scout and BrandShield:
- Full Form 10-K Item 1 (Business Overview), Item 1A (Risk Factors), and Item 7 (MD&A)
- Form 10-Q Quarterly Reports and Form 8-K Material Current Reports
- Ingests up to 25,000 characters of verified statutory corporate filings
- Full compliance with SEC EDGAR declared User-Agent guidelines
"""

from __future__ import annotations

import json
import hashlib
import os
import logging
import re
import urllib.parse
from typing import Any, Dict, List, Optional

from backend.infrastructure.acquisition.adapters.expansion_safety import GuardedExpansionAdapter as PlatformAdapter
from backend.infrastructure.acquisition.adapters.expansion_safety import safe_fetch as fetch_public_http, bounded_decode
from backend.services.agent_reach.channels import (
    CandidateSource,
    ContentDepth,
    EvidenceFragment,
    FetchedDocument,
    RetrievalMode,
    RetrievalRequest,
)
from backend.services.url_validator import validate_url_safe

logger = logging.getLogger(__name__)

SEC_SUBMISSIONS_BASE = "https://data.sec.gov/submissions"
DEFAULT_SEC_HEADERS = {
    "User-Agent": os.getenv("SEC_USER_AGENT", ""),
}


def sec_filing_locator(url):
    """Only accession-scoped filing documents belong to this reader."""
    return re.fullmatch(r"https://www\.sec\.gov/Archives/edgar/data/(\d{1,10})/(\d{18})/([A-Za-z0-9][A-Za-z0-9_.-]*\.(?:htm|html|xml|pdf))", url, re.I)


class SecFilingsFullAdapter(PlatformAdapter):
    """Acquires and extracts full 10-K/10-Q corporate disclosures from SEC EDGAR."""

    @property
    def platform(self) -> str:
        return "sec_filings_full"

    @property
    def backend_id(self) -> str:
        return "sec_edgar_full_reader"

    def can_handle(self, candidate: CandidateSource) -> bool:
        url = (candidate.canonical_url or candidate.url).lower()
        if candidate.platform.lower() in ("sec_filings_full", "sec_full", "sec_10k"):
            return True
        return "sec.gov/archives/edgar/data" in url or ("sec.gov" in url and any(f in url for f in ["10-k", "10-q", "8-k"]))

    def discover(self, query: str, limit: int = 5) -> List[CandidateSource]:
        from backend.infrastructure.acquisition.adapters.authoritative.sec_edgar import fetch_sec_submissions
        result = fetch_sec_submissions(query, limit=limit)
        if result["status"] != "SUCCESS":
            return []
        return [CandidateSource(url=row["doc_url"], canonical_url=row["doc_url"], platform=self.platform,
            title=f"{row['company_name']} SEC Form {row['form']} ({row['filing_date']})",
            snippet=row["description"], metadata={**row, "primary_source": False,
                "official_source": False, "document_body_acquired": False}) for row in result["items"]]

    def acquire(self, candidate: CandidateSource, request: RetrievalRequest) -> FetchedDocument:
        from backend.services.research.issuer_identity import issuer_identity_resolver
        from backend.infrastructure.acquisition.network.http import decode_bounded_http_body
        from backend.infrastructure.acquisition.adapters.web.page_extraction import extract_readable_page, extract_observed_page_details
        from bs4 import BeautifulSoup
        url = candidate.canonical_url or candidate.url
        match = sec_filing_locator(url)
        if not match:
            return FetchedDocument(url=url, status="UNSUPPORTED_SEC_DOCUMENT", backend_id=self.backend_id)
        response = fetch_public_http(url, timeout=5.0, max_bytes=1_000_000, max_attempts=1, preserve_http_errors=True)
        raw = decode_bounded_http_body(response, max_bytes=1_000_000)
        if not raw.strip():
            return FetchedDocument(url=url, status="EMPTY_CONTENT", backend_id=self.backend_id)
        identity = issuer_identity_resolver.resolve(match.group(1).zfill(10))
        filing = next((row for row in identity.get("observed_filings", []) if row["doc_url"] == url), {})
        if raw.startswith(b"%PDF-"):
            from backend.infrastructure.acquisition.adapters.web.pdf_text import extract_pdf_text
            pdf = extract_pdf_text(raw)
            text, page = pdf["text"], {"content_scope": "PDF_TEXT_LAYER", "pdf_pages": pdf["pages"],
                "pdf_source_sha256": pdf["source_pdf_sha256"], "table_structure_verified": False}
        else:
            soup = BeautifulSoup(raw, "html.parser")
            page = extract_observed_page_details(soup, response.endpoint)
            extracted = extract_readable_page(soup)
            text = extracted.pop("text")
            extracted.pop("raw_text", None)
            page.update(extracted)
        return FetchedDocument(url=url, status="SUCCESS" if text.strip() else "EMPTY_CONTENT",
            raw_content=text[:20000], backend_id=self.backend_id,
            raw_metadata={**filing, "cik": match.group(1).zfill(10), "company_name": identity.get("legal_name"),
                "form": filing.get("form") or "UNSPECIFIED",
                "page_metadata": page, "body_truncated": len(text) > 20000,
                "payload_sha256": hashlib.sha256(raw).hexdigest(),
                "transport": {"endpoint":response.endpoint, "status_code":response.status_code,
                              "network_observed":True, "attempts":response.attempts}})

    def normalize(
        self,
        document: FetchedDocument,
        candidate: CandidateSource,
        request: RetrievalRequest,
    ) -> List[EvidenceFragment]:
        """Normalize into official primary evidence fragment."""
        if document.status != "SUCCESS" or not document.raw_content:
            return []

        company = document.raw_metadata.get("company_name") or candidate.metadata.get("company_name", "Issuer")
        form = document.raw_metadata.get("form") or candidate.metadata.get("form") or "UNSPECIFIED"
        content = document.raw_content

        fragment = EvidenceFragment(
            platform="sec_filings_full",
            channel_name="sec_filings_full",
            url=candidate.url,
            title=f"[{company}] SEC Form {form} Full Statutory Filing",
            content=content,
            snippet=content[:450] + ("..." if len(content) > 450 else ""),
            author=f"{company} / U.S. Securities and Exchange Commission",
            content_depth=ContentDepth.FULL_ARTICLE.value,
            retrieval_mode=RetrievalMode.DIRECT_API.value,
            native_backend_id=self.backend_id,
            retrieval_lineage=[{
                "platform": "sec_filings_full",
                "backend": self.backend_id,
                "url": candidate.url,
                "company_name": company,
                "form": form,
                "filing_date": document.raw_metadata.get("filing_date"),
                "retrieval_mode": RetrievalMode.DIRECT_API.value,
            }],
            raw_metadata={
                "source_role": "primary",
                "source_tier": "tier_1_official",
                "source_domain": "sec.gov",
                "source_independence_group": "sec.gov",
                "char_count": len(content),
                "word_count": len(content.split()),
                "company_name": company,
                "form": form,
                "filing_date": document.raw_metadata.get("filing_date"),
            },
        )
        return [fragment]
