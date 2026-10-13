"""
Aegis Protocol — SEC EDGAR Primary Regulatory Acquisition Adapter
==================================================================
Acquires official corporate filings (10-K, 10-Q, 8-K) directly from data.sec.gov.
Enforces 15-point source contract, SEC-compliant User-Agent header, SSRF safety,
and 1MB bounded payload limits.
"""

from __future__ import annotations

import json
import logging
import re
from typing import Any, Dict, List, Optional

from backend.infrastructure.acquisition.network.http import (
    decode_bounded_http_body,
    fetch_public_http,
    BoundedHTTPResponse,
)
from backend.services.agent_reach.channels import EvidenceFragment, RetrievalMode

logger = logging.getLogger(__name__)

# SEC requires specific User-Agent format: Sample Company Name AdminContact@domain.com
SEC_USER_AGENT = "AegisProtocol MisinfoResearch/1.0 (compliance@aegisprotocol.internal)"

# Known high-volume tickers to 10-digit zero-padded CIK
TICKER_CIK_MAP: Dict[str, str] = {
    "NVDA": "0001045810",
    "AAPL": "0000320193",
    "MSFT": "0000789019",
    "AMZN": "0001018724",
    "GOOGL": "0001652044",
    "GOOG": "0001652044",
    "META": "0001326801",
    "TSLA": "0001318605",
    "AMD": "0000002488",
    "INTC": "0000050863",
    "ORCL": "0001341439",
    "CSCO": "0000858877",
    "IBM": "0000051143",
    "JPM": "0000019617",
    "BAC": "0000070858",
}


def resolve_cik(query: str) -> Optional[str]:
    """Resolve a query string (ticker or raw CIK number) into a 10-digit zero-padded CIK."""
    clean = query.strip().upper()
    if clean in TICKER_CIK_MAP:
        return TICKER_CIK_MAP[clean]
    # Check if purely numeric
    if clean.isdigit() and len(clean) <= 10:
        return clean.zfill(10)
    return None


def fetch_sec_submissions(
    query_or_cik: str,
    limit: int = 5,
    form_filter: Optional[str] = None,
    http_fetcher: Optional[Any] = None,
) -> Dict[str, Any]:
    """
    Acquire recent corporate submissions from SEC EDGAR.
    URL: https://data.sec.gov/submissions/CIK{cik}.json
    """
    fetcher = http_fetcher if http_fetcher is not None else fetch_public_http
    cik = resolve_cik(query_or_cik)
    if not cik:
        return {
            "status": "UNRESOLVED_CIK",
            "error": f"Could not resolve corporate CIK for query '{query_or_cik}'. Provide ticker or 10-digit CIK.",
            "items": [],
            "transport": {}
        }

    url = f"https://data.sec.gov/submissions/CIK{cik}.json"
    headers = {
        "User-Agent": SEC_USER_AGENT,
        "Accept": "application/json",
        "Accept-Encoding": "identity",
    }

    try:
        response: BoundedHTTPResponse = fetcher(
            url,
            headers=headers,
            timeout=5.0,
            max_bytes=1_000_000,
        )
        raw_bytes = decode_bounded_http_body(response, max_bytes=1_000_000)
        data = json.loads(raw_bytes.decode("utf-8", errors="replace"))
    except Exception as e:
        logger.warning(f"[SEC EDGAR] Fetch failure for CIK {cik}: {e}")
        return {
            "status": "FAILED",
            "error": str(e),
            "items": [],
            "transport": {"endpoint": url, "cik": cik}
        }

    company_name = data.get("name", "Unknown Corporate Entity")
    sic_desc = data.get("sicDescription", "")
    filings = data.get("filings", {}).get("recent", {})

    forms = filings.get("form", [])
    acc_nums = filings.get("accessionNumber", [])
    dates = filings.get("filingDate", [])
    report_dates = filings.get("reportDate", [])
    doc_names = filings.get("primaryDocument", [])
    descriptions = filings.get("primaryDocDescription", [])
    items_list = filings.get("items", [])

    matched_items: List[Dict[str, Any]] = []
    clean_filter = form_filter.upper().strip() if form_filter else None

    count = len(forms)
    for i in range(count):
        form_name = forms[i] if i < len(forms) else "UNKNOWN"
        if clean_filter and form_name != clean_filter:
            continue

        acc_num = acc_nums[i] if i < len(acc_nums) else ""
        acc_no_hyphen = acc_num.replace("-", "")
        f_date = dates[i] if i < len(dates) else ""
        r_date = report_dates[i] if i < len(report_dates) else ""
        doc_name = doc_names[i] if i < len(doc_names) else ""
        desc = descriptions[i] if i < len(descriptions) else ""
        items_entry = items_list[i] if i < len(items_list) else ""

        doc_url = f"https://www.sec.gov/Archives/edgar/data/{int(cik)}/{acc_no_hyphen}/{doc_name}" if doc_name else f"https://www.sec.gov/edgar/browse/?CIK={cik}"

        matched_items.append({
            "cik": cik,
            "company_name": company_name,
            "sic_description": sic_desc,
            "form": form_name,
            "accession_number": acc_num,
            "filing_date": f_date,
            "report_date": r_date,
            "primary_document": doc_name,
            "description": desc or f"{company_name} Form {form_name}",
            "doc_url": doc_url,
            "filing_items": items_entry,
        })

        if len(matched_items) >= limit:
            break

    return {
        "status": "SUCCESS",
        "cik": cik,
        "company_name": company_name,
        "items": matched_items,
        "transport": {
            "endpoint": url,
            "status_code": response.status_code,
            "latency_ms": response.latency_ms,
        }
    }


def normalize_sec_items(
    items: List[Dict[str, Any]],
    query_id: str = "",
    query_class: str = "",
    query_text: str = ""
) -> List[EvidenceFragment]:
    """Normalize SEC EDGAR filing items into typed EvidenceFragments."""
    fragments: List[EvidenceFragment] = []
    for idx, item in enumerate(items):
        title = f"{item['company_name']} Form {item['form']} ({item['filing_date']})"
        snippet = (
            f"Official SEC filing for {item['company_name']}. Form: {item['form']}. "
            f"Filing Date: {item['filing_date']}. Period: {item['report_date']}. "
            f"Description: {item['description']}. Accession: {item['accession_number']}."
        )
        frag = EvidenceFragment(
            platform="sec_edgar",
            title=title,
            content=snippet,
            snippet=snippet,
            url=item["doc_url"],
            author="U.S. Securities and Exchange Commission (SEC EDGAR)",
            published=item["filing_date"],
            score=98.0,
            retrieval_method="sec_edgar_rest",
            retrieval_mode=RetrievalMode.DIRECT_API.value,
            native_backend_id="sec-edgar-data-api",
            channel_name="sec_edgar",
            requested_channel="sec_edgar",
            actual_retrieval_channel="sec_edgar",
            content_depth="DIRECT_CONTENT",
            query_id=query_id,
            query_class=query_class,
            query_text=query_text,
            raw_metadata={
                "cik": item["cik"],
                "company_name": item["company_name"],
                "form": item["form"],
                "accession_number": item["accession_number"],
                "report_date": item["report_date"],
                "filing_items": item.get("filing_items"),
                "source_role": "PRIMARY",
                "source_tier": "TIER_1_OFFICIAL_FILING",
                "source_authority": "OFFICIAL_REGULATORY",
                "primary_source": True,
                "reliability_score": 0.98,
                "canonical_url": item["doc_url"],
            }
        )
        fragments.append(frag)
    return fragments
