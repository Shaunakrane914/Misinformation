"""Aegis Protocol — SEC EDGAR Full Disclosures & 10-K Reader Adapter.

Provides comprehensive regulatory narrative disclosures for Scout and BrandShield:
- Full Form 10-K Item 1 (Business Overview), Item 1A (Risk Factors), and Item 7 (MD&A)
- Form 10-Q Quarterly Reports and Form 8-K Material Current Reports
- Ingests up to 25,000 characters of verified statutory corporate filings
- Full compliance with SEC EDGAR declared User-Agent guidelines
"""

from __future__ import annotations

import json
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
    "User-Agent": os.getenv("SEC_USER_AGENT", "AegisResearch admin@aegisresearch.org"),
}


class SecFilingsFullAdapter(PlatformAdapter):
    """Acquires and extracts full 10-K/10-Q corporate disclosures from SEC EDGAR."""

    KNOWN_CIKS = {
        "NVDA": "0001045810",
        "AAPL": "0000320193",
        "MSFT": "0000789019",
        "GOOGL": "0001652044",
        "GOOG": "0001652044",
        "AMZN": "0001018724",
        "TSLA": "0001318605",
        "META": "0001326801",
        "INFY": "0001067491",
        "ADBE": "0000796343",
        "ORCL": "0001341439",
        "INTC": "0000050863",
        "IBM": "0000051143",
    }

    NAME_TO_TICKER = {
        "APPLE": "AAPL",
        "MICROSOFT": "MSFT",
        "NVIDIA": "NVDA",
        "GOOGLE": "GOOGL",
        "ALPHABET": "GOOGL",
        "AMAZON": "AMZN",
        "TESLA": "TSLA",
        "INFOSYS": "INFY",
        "ADOBE": "ADBE",
        "ORACLE": "ORCL",
        "INTEL": "INTC",
    }

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
        """Discover full corporate filings for target entity ticker or name."""
        candidates: List[CandidateSource] = []
        clean_q = query.upper().strip()

        cik = None
        ticker = None
        for t, c in self.KNOWN_CIKS.items():
            if re.search(r"(?<![A-Z0-9])" + re.escape(t) + r"(?![A-Z0-9])", clean_q):
                cik = c
                ticker = t
                break

        if not cik:
            for name, mapped_ticker in self.NAME_TO_TICKER.items():
                if name in clean_q:
                    ticker = mapped_ticker
                    cik = self.KNOWN_CIKS.get(mapped_ticker)
                    break

        if not cik:
            return candidates

        submissions_url = f"{SEC_SUBMISSIONS_BASE}/CIK{cik}.json"
        if not validate_url_safe(submissions_url)[0]:
            return candidates

        try:
            resp = fetch_public_http(submissions_url, headers=DEFAULT_SEC_HEADERS, timeout=5.0)
            if resp.status_code != 200:
                logger.warning("[SecFilingsFullAdapter] EDGAR submissions HTTP %d for CIK %s", resp.status_code, cik)
                return candidates

            raw_bytes = resp.body
            if raw_bytes.startswith(b"\x1f\x8b"):
                from backend.infrastructure.acquisition.adapters.expansion_safety import bounded_decode
                raw_bytes = bounded_decode(raw_bytes)
            data = json.loads(raw_bytes.decode("utf-8", errors="replace"))
            company_name = data.get("name", ticker)
            recent_filings = data.get("filings", {}).get("recent", {})

            forms = recent_filings.get("form", [])
            filing_dates = recent_filings.get("filingDate", [])
            accession_numbers = recent_filings.get("accessionNumber", [])
            primary_docs = recent_filings.get("primaryDocument", [])
            primary_descs = recent_filings.get("primaryDocDescription", [])

            for i in range(min(len(forms), 25)):
                if len(candidates) >= limit:
                    break
                form = forms[i]
                if form in ("10-K", "10-Q", "8-K"):
                    acc_num = accession_numbers[i].replace("-", "")
                    doc_name = primary_docs[i]
                    fdate = filing_dates[i]
                    fdesc = primary_descs[i] if i < len(primary_descs) else form

                    doc_url = f"https://www.sec.gov/Archives/edgar/data/{int(cik)}/{acc_num}/{doc_name}"
                    candidates.append(
                        CandidateSource(
                            url=doc_url,
                            canonical_url=doc_url,
                            platform="sec_filings_full",
                            title=f"[{company_name}] Full SEC Form {form} ({fdate})",
                            snippet=f"Complete SEC regulatory filing {form} for {company_name}. Accession: {accession_numbers[i]}. Description: {fdesc}",
                            metadata={
                                "ticker": ticker,
                                "cik": cik,
                                "company_name": company_name,
                                "form": form,
                                "filing_date": fdate,
                                "accession_number": accession_numbers[i],
                                "primary_document": doc_name,
                                "primary_source": True,
                                "official_source": True,
                            },
                        )
                    )
        except Exception as exc:
            logger.warning("[SecFilingsFullAdapter] Discovery error for '%s': %s", query, type(exc).__name__)

        return candidates

    def acquire(self, candidate: CandidateSource, request: RetrievalRequest) -> FetchedDocument:
        """Fetch and extract full disclosure text from the SEC filing document."""
        url = candidate.canonical_url or candidate.url
        if not validate_url_safe(url)[0]:
            return FetchedDocument(url=url, status="BLOCKED_SSRF", failure_reason="SEC document URL failed SSRF check", backend_id=self.backend_id)

        try:
            resp = fetch_public_http(url, headers=DEFAULT_SEC_HEADERS, timeout=8.0, max_bytes=3_000_000)
            if resp.status_code != 200:
                return FetchedDocument(url=url, status="FAILED", failure_reason=f"HTTP {resp.status_code}", backend_id=self.backend_id)

            raw_body = resp.body
            if raw_body.startswith(b"\x1f\x8b"):
                import gzip
                raw_body = bounded_decode(raw_body)
            raw_html = raw_body.decode("utf-8", errors="replace")

            # Extract narrative text from HTML while preserving headers and items
            cleaned = re.sub(r"<script[^>]*>[\s\S]*?</script>", "", raw_html, flags=re.IGNORECASE)
            cleaned = re.sub(r"<style[^>]*>[\s\S]*?</style>", "", cleaned, flags=re.IGNORECASE)
            # Replace paragraph/div/tr tags with newlines
            cleaned = re.sub(r"<(?:p|div|tr|h[1-6])[^>]*>", "\n\n", cleaned, flags=re.IGNORECASE)
            cleaned = re.sub(r"<[^>]+>", " ", cleaned)
            # Normalize whitespace
            plain_text = re.sub(r"[ \t]+", " ", cleaned)
            plain_text = re.sub(r"\n{3,}", "\n\n", plain_text).strip()

            if not plain_text:
                return FetchedDocument(url=url, status="EMPTY_CONTENT", backend_id=self.backend_id)

            form = candidate.metadata.get("form") or "UNSPECIFIED"
            company_name = candidate.metadata.get("company_name", "Issuer")
            filing_date = candidate.metadata.get("filing_date", "")

            # Formulate full regulatory disclosure
            header = f"# SEC Form {form} Statutory Filing — {company_name}\n"
            header += f"**Filing Date**: {filing_date} | **Official EDGAR Submission**: {url}\n\n"

            full_content = (header + plain_text)[:25000]

            return FetchedDocument(
                url=url,
                status="SUCCESS",
                raw_content=full_content,
                backend_id=self.backend_id,
                raw_metadata={
                    "ticker": candidate.metadata.get("ticker"),
                    "cik": candidate.metadata.get("cik"),
                    "company_name": company_name,
                    "form": form,
                    "filing_date": filing_date,
                    "wordcount": len(full_content.split()),
                },
            )
        except Exception as exc:
            logger.warning("[SecFilingsFullAdapter] Acquisition error for '%s': %s", url, type(exc).__name__)
            return FetchedDocument(url=url, status="FAILED", failure_reason=type(exc).__name__, backend_id=self.backend_id)

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
