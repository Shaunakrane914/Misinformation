"""Aegis Protocol — SEC EDGAR Corporate Regulatory Adapter.

Provides official regulatory filing intelligence for Scout and BrandShield:
- SEC EDGAR submissions & 10-K / 10-Q / 8-K filings
- CIK and company ticker resolution
- Strict User-Agent declaration compliance and rate throttling
"""

from __future__ import annotations

import json
import re
import os
import logging
import urllib.parse
from typing import Any, Dict, List, Optional

from backend.infrastructure.acquisition.adapters.expansion_safety import GuardedExpansionAdapter as PlatformAdapter
from backend.infrastructure.acquisition.adapters.expansion_safety import safe_fetch as fetch_public_http
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
    "Accept-Encoding": "gzip, deflate",
}


class SecEdgarAdapter(PlatformAdapter):
    """Acquires official corporate filings from SEC EDGAR."""

    # Common ticker to CIK mappings for high-frequency Scout targets
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
        return "sec_edgar"

    @property
    def backend_id(self) -> str:
        return "sec_edgar_api"

    def can_handle(self, candidate: CandidateSource) -> bool:
        url = (candidate.canonical_url or candidate.url).lower()
        if candidate.platform.lower() in ("sec", "sec_edgar", "edgar"):
            return True
        return "sec.gov" in url

    def discover(self, query: str, limit: int = 5) -> List[CandidateSource]:
        """Discover SEC EDGAR filings for a recognized company ticker or name."""
        candidates: List[CandidateSource] = []
        clean_q = query.upper().strip()

        # Find matching CIK
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

        target_url = f"{SEC_SUBMISSIONS_BASE}/CIK{cik}.json"
        try:
            resp = fetch_public_http(target_url, headers=DEFAULT_SEC_HEADERS, timeout=4.0)
            if resp.status_code == 200:
                data = json.loads(resp.body.decode("utf-8", errors="replace"))
                name = data.get("name", ticker)
                recent = data.get("filings", {}).get("recent", {})
                forms = recent.get("form", [])
                dates = recent.get("filingDate", [])
                accessions = recent.get("accessionNumber", [])
                doc_names = recent.get("primaryDocument", [])
                descriptions = recent.get("primaryDocDescription", [])

                for idx in range(min(len(forms), limit)):
                    form = forms[idx]
                    fdate = dates[idx] if idx < len(dates) else ""
                    acc = accessions[idx].replace("-", "") if idx < len(accessions) else ""
                    doc_n = doc_names[idx] if idx < len(doc_names) else ""
                    desc = descriptions[idx] if idx < len(descriptions) else form
                    acc_raw = accessions[idx] if idx < len(accessions) else ""

                    filing_url = f"https://www.sec.gov/Archives/edgar/data/{int(cik)}/{acc}/{doc_n}"

                    candidates.append(
                        CandidateSource(
                            url=filing_url,
                            platform="sec_edgar",
                            title=f"[{name}] SEC Form {form} ({fdate})",
                            snippet=f"Official {form} filing: {desc} | Accession: {acc_raw}",
                            search_engine="sec_edgar_submissions",
                            search_rank=idx + 1,
                            metadata={
                                "company_name": name,
                                "ticker": ticker,
                                "cik": cik,
                                "form": form,
                                "filing_date": fdate,
                                "accession_number": acc_raw,
                            },
                        )
                    )
        except Exception as exc:
            logger.debug(f"[SecEdgarAdapter] Discovery error for {query}: {type(exc).__name__}")

        return candidates

    def acquire(self, candidate: CandidateSource, request: RetrievalRequest) -> FetchedDocument:
        target_url = candidate.canonical_url or candidate.url
        is_safe, reason = validate_url_safe(target_url)
        if not is_safe:
            return FetchedDocument(
                url=target_url,
                status="BLOCKED",
                backend_id=self.backend_id,
                retrieval_mode=RetrievalMode.DIRECT_API.value,
                failure_reason=f"SSRF policy blocked URL: {reason}",
            )

        try:
            resp = fetch_public_http(target_url, headers=DEFAULT_SEC_HEADERS, timeout=5.0, max_bytes=1_000_000)
            return FetchedDocument(
                url=target_url,
                status="SUCCESS" if resp.status_code == 200 else "FAILED",
                backend_id=self.backend_id,
                retrieval_mode=RetrievalMode.WEB_READER.value,
                raw_content=resp.body.decode("utf-8", errors="replace"),
                latency_ms=resp.latency_ms,
            )
        except Exception as exc:
            return FetchedDocument(
                url=target_url,
                status="FAILED",
                backend_id=self.backend_id,
                retrieval_mode=RetrievalMode.WEB_READER.value,
                failure_reason=type(exc).__name__,
            )

    def normalize(
        self,
        document: FetchedDocument,
        candidate: CandidateSource,
        request: RetrievalRequest,
    ) -> List[EvidenceFragment]:
        if document.status != "SUCCESS":
            return []

        company = candidate.metadata.get("company_name") or "SEC Reporting Company"
        form = candidate.metadata.get("form") or "Filing"
        raw_text = document.raw_content[:4000]

        return [
            EvidenceFragment(
                platform="sec_edgar",
                title=candidate.title or f"{company} SEC Form {form}",
                content=f"SEC EDGAR Official Document ({form}):\n\n{raw_text}",
                url=document.url,
                author=f"{company} (SEC EDGAR)",
                published=candidate.metadata.get("filing_date", ""),
                snippet=candidate.snippet or raw_text[:250],
                score=98.0,
                content_depth=ContentDepth.FULL_ARTICLE.value if len(raw_text) > 800 else ContentDepth.PARTIAL_CONTENT.value,
                retrieval_mode=RetrievalMode.WEB_READER.value,
                native_backend_id=self.backend_id,
                channel_name="sec_edgar",
                raw_metadata={
                    "is_official_regulatory": True,
                    "primary_source": True,
                    "form_type": form,
                    "company_name": company,
                    "cik": candidate.metadata.get("cik", ""),
                },
            )
        ]
