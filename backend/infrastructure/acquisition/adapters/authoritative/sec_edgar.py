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
import os
import hashlib
from typing import Any, Dict, List, Optional

from backend.infrastructure.acquisition.network.http import (
    decode_bounded_http_body,
    fetch_public_http,
    BoundedHTTPResponse,
)
from backend.services.agent_reach.channels import EvidenceFragment, RetrievalMode

logger = logging.getLogger(__name__)

# SEC requires specific User-Agent format: Sample Company Name AdminContact@domain.com
SEC_USER_AGENT_ENV = "SEC_USER_AGENT"
# Backwards-compatible export; never invent a real organization's contact.
SEC_USER_AGENT = os.environ.get(SEC_USER_AGENT_ENV, "").strip()

# Extended high-volume and global ADR tickers to 10-digit zero-padded CIK
TICKER_CIK_MAP: Dict[str, str] = {
    # Mega-cap Tech & Communication
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
    "AVGO": "0001730168",
    "ADBE": "0000796343",
    "CRM": "0001108524",
    "NFLX": "0001065280",
    # Financials & Payments
    "JPM": "0000019617",
    "BAC": "0000070858",
    "V": "0001403161",
    "MA": "0001141391",
    "BRK.A": "0001067983",
    "BRK.B": "0001067983",
    # Healthcare & Pharma
    "JNJ": "0000200406",
    "LLY": "0000059478",
    "UNH": "0000731766",
    "PFE": "0000078003",
    "ABBV": "0001551152",
    "MRK": "0000310158",
    # Consumer & Industrial
    "WMT": "0000104169",
    "COST": "0000909832",
    "PG": "0000080424",
    "HD": "0000354950",
    "KO": "0000021344",
    "PEP": "0000077476",
    "DIS": "0001744489",
    "NKE": "0000320187",
    "SKX": "0001065837",   # Skechers USA Inc.
    "XOM": "0000034088",
    "CVX": "0000093410",
    # Key International ADRs (Foreign Private Issuers filing 20-F / 6-K)
    "INFY": "0001067491",  # Infosys ADR
    "TTM": "0000926042",   # Tata Motors ADR
    "LNVGY": "0001002517", # Lenovo ADR
    "BABA": "0001577552",  # Alibaba ADR
    "TSM": "0001046179",   # TSMC ADR
    "ASML": "0000937966",  # ASML ADR
    "SAP": "0001000184",   # SAP ADR
    "SONY": "0000092380",  # Sony ADR
    "TM": "0001094517",    # Toyota ADR
    "NVO": "0000353278",   # Novo Nordisk ADR
    "AZN": "0001071495",   # AstraZeneca ADR
}

COMPANY_NAME_CIK_MAP: Dict[str, str] = {
    "NVIDIA": "0001045810",
    "APPLE": "0000320193",
    "MICROSOFT": "0000789019",
    "AMAZON": "0001018724",
    "GOOGLE": "0001652044",
    "ALPHABET": "0001652044",
    "META": "0001326801",
    "FACEBOOK": "0001326801",
    "TESLA": "0001318605",
    "INFOSYS": "0001067491",
    "TATA MOTORS": "0000926042",
    "JOHNSON & JOHNSON": "0000200406",
    "JOHNSON AND JOHNSON": "0000200406",
    "JOHNSON JOHNSON": "0000200406",
    "WALMART": "0000104169",
    "PFIZER": "0000078003",
    "BERKSHIRE HATHAWAY": "0001067983",
    "SKECHERS": "0001065837",
    "SKECHERS USA": "0001065837",
    "SKECHERS USA INC": "0001065837",
}


def resolve_cik(query: str) -> Optional[str]:
    """Resolve a query string (ticker, clean company name, or raw CIK number) into a 10-digit zero-padded CIK.
    
    Precedence Order:
    1. Direct numeric CIK (e.g. '0001067491' or '1067491')
    2. Minimal audited static ticker/name map (exact canonical mapping)
    3. Authoritative Dynamic Resolver (IssuerIdentityResolver bootstrap + observed submissions/indexes)
    4. Cached index on disk (zero network I/O)
    """
    raw = query.strip()
    if not raw:
        return None
    # 1. Pure numeric CIK detection
    if raw.isdigit() and len(raw) <= 10:
        return raw.zfill(10)

    # 2. Exact Audited Static Map
    clean = raw.upper()
    # Strip market/exchange prefixes like NASDAQ:, NYSE:, BATS:
    clean = re.sub(r"^(?:NASDAQ|NYSE|AMEX|BATS):\s*", "", clean)
    # Strip country/exchange suffixes like .NS, .BO, .O, .N, .US, .HK
    clean_sym = re.sub(r"\.(?:O|N|US|NS|BO|HK)$", "", clean)
    clean_sym = clean_sym.replace("-", ".").replace("/", ".")
    if clean_sym in TICKER_CIK_MAP:
        return TICKER_CIK_MAP[clean_sym]
    # Check company name aliases
    name_clean = re.sub(r"[^\w\s&]", "", clean).strip()
    if name_clean in COMPANY_NAME_CIK_MAP:
        return COMPANY_NAME_CIK_MAP[name_clean]
    base_name = re.sub(r"\s+(?:INC|INCORPORATED|CORP|CORPORATION|LTD|LIMITED|CO|COMPANY)$", "", name_clean).strip()
    if base_name in COMPANY_NAME_CIK_MAP:
        return COMPANY_NAME_CIK_MAP[base_name]

    # 3. Authoritative Dynamic Resolver in memory
    from backend.services.research.issuer_identity import resolve_issuer, issuer_identity_resolver
    identity = resolve_issuer(raw)
    if identity["status"] == "AMBIGUOUS":
        return None
    if identity.get("cik"):
        return identity["cik"]

    # 4. Disk cache ingestion if present
    if identity["status"] == "UNRESOLVED":
        if issuer_identity_resolver.load_cached_index_file() > 0:
            identity = resolve_issuer(raw)
            if identity.get("cik"):
                return identity["cik"]
            if identity["status"] == "AMBIGUOUS":
                return None
    return None


def fetch_sec_submissions(
    query_or_cik: str,
    limit: int = 5,
    form_filter: Optional[str] = None,
    http_fetcher: Optional[Any] = None,
    filing_scope: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Acquire recent corporate submissions from SEC EDGAR.
    URL: https://data.sec.gov/submissions/CIK{cik}.json
    """
    fetcher = http_fetcher if http_fetcher is not None else fetch_public_http
    from backend.infrastructure.acquisition.adapters.expansion_safety import policy_status
    from backend.services.research.issuer_identity import issuer_identity_resolver
    if http_fetcher is None and policy_status("sec_edgar"):
        return {"status": "CONFIG_REQUIRED", "items": [], "error": "Configure an owner-approved SEC_USER_AGENT contact", "transport": {"network_observed": False}}
    if http_fetcher is None:
        from backend.infrastructure.acquisition.network.sec_pacing import wait_for_sec_slot
        def fetcher(*args, **kwargs):
            wait_for_sec_slot()
            return fetch_public_http(*args, **kwargs)
    cik = resolve_cik(query_or_cik)
    if not cik and issuer_identity_resolver.can_attempt_sync():
        index_url = "https://www.sec.gov/files/company_tickers_exchange.json"
        try:
            response = fetcher(index_url, headers={"User-Agent": os.environ.get(SEC_USER_AGENT_ENV) or "AegisOfflineFixture"},
                timeout=5.0, max_bytes=1_000_000, max_attempts=1, max_redirects=0)
            raw = decode_bounded_http_body(response, max_bytes=1_000_000)
            issuer_identity_resolver.observe_ticker_index(json.loads(raw), index_url, hashlib.sha256(raw).hexdigest(), query=query_or_cik)
            cik = issuer_identity_resolver.resolve(query_or_cik).get("cik")
        except Exception as error:
            issuer_identity_resolver.record_sync_failure(error, index_url)
            return {"status": "FAILED", "items": [], "error": type(error).__name__, "transport": {
                "endpoint": index_url, "status_code": getattr(error, "status_code", None),
                "failure_kind": getattr(error, "failure_kind", type(error).__name__)}}
    if not cik:
        return {
            "status": "UNRESOLVED_CIK",
            "error": f"Could not resolve corporate CIK for query '{query_or_cik}'. Provide ticker or 10-digit CIK.",
            "items": [],
            "transport": {}
        }

    url = f"https://data.sec.gov/submissions/CIK{cik}.json"
    user_agent = os.environ.get(SEC_USER_AGENT_ENV, "").strip()
    if not user_agent and http_fetcher is None:
        return {"status": "CONFIG_REQUIRED", "error": "Configure SEC_USER_AGENT with an owner-approved organization and contact", "items": [], "transport": {"network_observed": False}}
    headers = {
        "User-Agent": user_agent or "AegisOfflineFixture",
        "Accept": "application/json",
        "Accept-Encoding": "identity",
    }

    try:
        response: BoundedHTTPResponse = fetcher(
            url,
            headers=headers,
            timeout=5.0,
            max_bytes=1_000_000,
            max_attempts=1, max_redirects=0,
        )
        raw_bytes = decode_bounded_http_body(response, max_bytes=1_000_000)
        data = json.loads(raw_bytes.decode("utf-8", errors="strict"))
        prior_identity = issuer_identity_resolver.resolve(query_or_cik)
        from backend.services.research.issuer_identity import identity_key
        def legal_key(value):
            return identity_key(re.sub(r"\s+(?:INC\.?|CORP\.?|CORPORATION|LTD\.?|LIMITED|COMPANY|PLC|SA|NV|SE|U\.?S\.?A\.?)$", "", str(value or ""), flags=re.I))
        observed = [data.get("name", ""), *data.get("tickers", []), *[r.get("name", "") for r in data.get("formerNames", [])]]
        observed_keys = {legal_key(name) for name in observed if isinstance(name, str)}
        if prior_identity.get("legal_name") and not query_or_cik.strip().isdigit():
            req_legal = legal_key(prior_identity["legal_name"])
            if req_legal not in observed_keys:
                raise ValueError(f"Requested legal entity '{prior_identity['legal_name']}' does not match returned SEC entity '{data.get('name')}'")
        elif prior_identity["status"] == "UNRESOLVED" and not query_or_cik.strip().isdigit():
            clean = re.sub(r"^(?:NASDAQ|NYSE|AMEX|BATS):\s*", "", query_or_cik.strip().upper())
            clean_sym = re.sub(r"\.(?:O|N|US|NS|BO|HK)$", "", clean).replace("-", ".").replace("/", ".")
            static_hit = TICKER_CIK_MAP.get(clean_sym)
            if not static_hit:
                name_clean = re.sub(r"[^\w\s&]", "", clean).strip()
                static_hit = COMPANY_NAME_CIK_MAP.get(name_clean)
                if not static_hit:
                    base = re.sub(r"\s+(?:INC|INCORPORATED|CORP|CORPORATION|LTD|LIMITED|CO|COMPANY)$", "", name_clean).strip()
                    static_hit = COMPANY_NAME_CIK_MAP.get(base)

            if static_hit != cik:
                subject = re.sub(r"^(?:NASDAQ|NYSE|AMEX):\s*", "", query_or_cik.strip(), flags=re.I)
                subject = re.sub(r"\.(?:NS|BO|US|O|N)$", "", subject, flags=re.I)
                if legal_key(subject) not in observed_keys:
                    raise ValueError("Requested issuer does not match returned submissions identity")
        identity = issuer_identity_resolver.observe_submissions(data, cik, url, hashlib.sha256(raw_bytes).hexdigest())
    except Exception as e:
        logger.warning("[SEC EDGAR] Fetch failure for CIK %s: %s", cik, type(e).__name__)
        return {
            "status": "FAILED",
            "error": type(e).__name__,
            "items": [],
            "transport": {"endpoint": url, "cik": cik, "status_code": getattr(e, "status_code", None),
                          "failure_kind": getattr(e, "failure_kind", type(e).__name__)}
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

    count = min(len(forms), 2000)
    for i in range(count):
        form_name = forms[i] if i < len(forms) else "UNKNOWN"
        if clean_filter and form_name != clean_filter:
            continue
        permitted_forms = {"10-K", "10-Q", "20-F", "40-F", "6-K", "8-K", "10-K/A", "10-Q/A", "20-F/A"}
        if form_name not in permitted_forms or filing_scope == "QUARTER" and form_name not in {"10-Q", "10-Q/A", "6-K", "8-K"}:
            continue

        acc_num = acc_nums[i] if i < len(acc_nums) else ""
        acc_no_hyphen = acc_num.replace("-", "")
        f_date = dates[i] if i < len(dates) else ""
        r_date = report_dates[i] if i < len(report_dates) else ""
        doc_name = doc_names[i] if i < len(doc_names) else ""
        desc = descriptions[i] if i < len(descriptions) else ""
        items_entry = items_list[i] if i < len(items_list) else ""

        if (not re.fullmatch(r"\d{1,10}-\d{2}-\d{1,6}", acc_num)
                or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]*\.(?:htm|html|xml|pdf)", doc_name, re.I)
                or not re.fullmatch(r"\d{4}-\d{2}-\d{2}", f_date)):
            continue
        doc_url = f"https://www.sec.gov/Archives/edgar/data/{int(cik)}/{acc_no_hyphen}/{doc_name}"

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
            "submissions_url": url, "submissions_sha256": hashlib.sha256(raw_bytes).hexdigest(),
        })

    matched_items.sort(key=lambda item: (item["filing_date"], item["report_date"]), reverse=True)
    matched_items = matched_items[:max(0, min(20, limit))]
    issuer_identity_resolver.remember_filings(cik, matched_items)

    return {
        "status": "SUCCESS",
        "cik": cik,
        "company_name": company_name,
        "issuer_identity": identity,
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
            content_depth="DIRECT_METADATA",
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
                "source_role": "DISCOVERY",
                "source_tier": "TIER_5_AGGREGATE",
                "source_authority": "OFFICIAL_REGULATORY",
                "content_depth_detail": "SUBMISSION_METADATA_NOT_XBRL_BODY",
                "primary_source": False,
                "reliability_score": 0.98,
                "canonical_url": item["doc_url"],
            }
        )
        fragments.append(frag)
    return fragments


def financial_fact_leads(identity, query_id, query_class, query_text):
    """Documented standard-XBRL locators, not guessed issuer article URLs."""
    from backend.services.research.financial_structured import CONCEPTS
    basis = identity.get("accounting_basis")
    taxonomy = {"IFRS": "ifrs-full", "US_GAAP": "us-gaap"}.get(basis)
    cik = identity.get("cik")
    if not cik:
        return []
    urls = []
    profile = identity.get("structured_financial_profile") or {}
    if profile.get("preferred_mode") == "COMPANYFACTS" and profile.get("observed_decoded_bytes", 1000001) <= 1000000:
        urls.append((f"https://data.sec.gov/api/xbrl/companyfacts/CIK{cik}.json", "FINANCIAL_FACTS"))
    elif taxonomy:
        selected_metrics = set()
        for concept, metric in CONCEPTS[taxonomy].items():
            if metric in {"REVENUE", "NET_INCOME", "EPS_DILUTED"} and metric not in selected_metrics:
                urls.append((f"https://data.sec.gov/api/xbrl/companyconcept/CIK{cik}/{taxonomy}/{concept}.json", metric))
                selected_metrics.add(metric)
                if len(urls) >= 3:
                    break
    else:
        urls.append((f"https://data.sec.gov/api/xbrl/companyfacts/CIK{cik}.json", "FINANCIAL_FACTS"))
    return [EvidenceFragment(platform="sec_edgar", channel_name="sec_edgar", url=url,
        title=f"{identity['legal_name']} {metric} — SEC structured financial data",
        snippet="Official standard-XBRL endpoint; body and financial values not acquired yet.", content="",
        content_depth="INDEX_SNIPPET", query_id=query_id, query_class="structured_financial_disclosure",
        query_text=query_text, native_backend_id="sec-edgar-data-api", retrieval_mode=RetrievalMode.DIRECT_API.value,
        raw_metadata={"cik": cik, "source_role": "DISCOVERY", "primary_source": False,
                      "discovered_on_url": identity["provenance"][-1]["source_url"],
                      "financial_subject": query_text, "locator_basis": "DOCUMENTED_SEC_XBRL_ENDPOINT_AND_OBSERVED_CIK"})
        for url, metric in urls]


def read_sec_financial_url(url, max_chars=20000):
    """One bounded original-API read, with contact, permissions and pinned DNS."""
    from decimal import Decimal
    from backend.infrastructure.acquisition.adapters.expansion_safety import safe_fetch, policy_status
    from backend.services.research.financial_structured import sec_financial_locator, xbrl_document
    if not sec_financial_locator(url):
        return None
    if policy_status("sec_edgar"):
        return {"status": "failed", "url": url, "failure_kind": "CONFIG_REQUIRED", "network_observed": False, "content": ""}
    from backend.services.research.source_registry import source_registry, SourcePermissionError
    permission = source_registry.body_decision(url)
    if not permission["eligible"]:
        raise SourcePermissionError(permission)
    response = safe_fetch(url, timeout=5.0, max_bytes=1_000_000, max_attempts=1, preserve_http_errors=True)
    raw = decode_bounded_http_body(response, max_bytes=1_000_000)
    data = json.loads(raw, parse_float=Decimal)
    text, document = xbrl_document(data, url, hashlib.sha256(raw).hexdigest(), max_chars=max_chars)
    from backend.services.research.issuer_identity import issuer_identity_resolver
    if "/companyfacts/" in url:
        issuer_identity_resolver.observe_companyfacts(data, url, hashlib.sha256(raw).hexdigest(), len(raw))
    filings = issuer_identity_resolver.resolve(document["cik"]).get("observed_filings", [])
    for fact in document["facts"]:
        filing = next((row for row in filings if row["accession_number"] == fact["accession"]), None)
        if filing:
            fact["filing_document_url"] = filing["doc_url"]
            fact["filing_locator_basis"] = "OBSERVED_SUBMISSIONS_RECORD_NOT_DOCUMENT_BODY_PROOF"
    if not document["facts"]:
        return {"status": "failed", "failure_kind": "NO_ELIGIBLE_XBRL_FACTS", "url": url, "content": ""}
    return {"status": "success", "url": url, "title": document["issuer"] + " SEC XBRL financial disclosure",
        "content": text, "markdown": text, "content_depth": "STRUCTURED_PUBLIC_DATA", "backend": "sec-standard-xbrl",
        "page_metadata": {"content_scope": "STRUCTURED_FINANCIAL_DATA", "financial_document": document,
                          "extraction_method": "SEC_STANDARD_XBRL_JSON"},
        "transport": {"endpoint": response.endpoint, "status_code": response.status_code, "attempts": response.attempts,
                      "latency_ms": response.latency_ms, "network_observed": True},
        "truncated": document["facts_omitted"] > 0}
