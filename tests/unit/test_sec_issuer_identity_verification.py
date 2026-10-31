"""Verification of SEC issuer identity consistency, CIK corrections, and mismatch defense."""

import json
from unittest.mock import MagicMock
from backend.infrastructure.acquisition.adapters.authoritative import sec_edgar
from backend.infrastructure.acquisition.network.http import BoundedHTTPResponse
from backend.services.research.issuer_identity import resolve_issuer, identity_key
from backend.services.research.financial_structured import qualified_document, scout_financial_disclosures
from backend.services.agent_reach.source_planner import SourcePlanningEngine


def make_submissions_payload(cik: int, name: str, ticker: str, form: str = "10-K"):
    return {
        "cik": cik,
        "name": name,
        "tickers": [ticker],
        "exchanges": ["NYSE" if ticker != "AAPL" and ticker != "MSFT" else "NASDAQ"],
        "filings": {
            "recent": {
                "form": [form],
                "filingDate": ["2026-06-15"],
                "reportDate": ["2026-03-31"],
                "accessionNumber": [f"{str(cik).zfill(10)}-26-000001"],
                "primaryDocument": [f"{ticker.lower()}-20260331.htm"],
                "primaryDocDescription": ["Annual or Quarterly Report"],
            }
        },
    }


def make_mock_http(payload: dict, endpoint: str):
    raw = json.dumps(payload).encode("utf-8")
    return BoundedHTTPResponse(
        body=raw,
        endpoint=endpoint,
        status_code=200,
        content_type="application/json",
        headers={},
        latency_ms=10,
        attempts=1,
    )


def test_four_issuers_cik_resolution():
    """Verify authoritative CIK resolution for Infosys, Skechers, Apple, and Microsoft."""
    # 1. Infosys must be 0001067491, NEVER Skechers (0001065837)
    assert sec_edgar.resolve_cik("Infosys") == "0001067491"
    assert sec_edgar.resolve_cik("INFY") == "0001067491"
    assert sec_edgar.resolve_cik("Infosys Limited") == "0001067491"

    # 2. Skechers must be 0001065837
    assert sec_edgar.resolve_cik("Skechers") == "0001065837"
    assert sec_edgar.resolve_cik("SKX") == "0001065837"
    assert sec_edgar.resolve_cik("Skechers USA") == "0001065837"

    # 3. Apple must be 0000320193
    assert sec_edgar.resolve_cik("Apple") == "0000320193"
    assert sec_edgar.resolve_cik("AAPL") == "0000320193"

    # 4. Microsoft must be 0000789019
    assert sec_edgar.resolve_cik("Microsoft") == "0000789019"
    assert sec_edgar.resolve_cik("MSFT") == "0000789019"


def test_issuer_identity_resolver_distinct_records():
    """Verify IssuerIdentityResolver strictly distinguishes Infosys and Skechers."""
    infy = resolve_issuer("Infosys")
    assert infy["status"] == "RESOLVED_WITH_PROVENANCE"
    assert infy["cik"] == "0001067491"
    assert "Infosys" in infy["legal_name"]
    assert set(infy["reporting_jurisdictions"]) == {"India", "US"}

    skx = resolve_issuer("Skechers")
    assert skx["status"] == "RESOLVED_WITH_PROVENANCE"
    assert skx["cik"] == "0001065837"
    assert "Skechers" in skx["legal_name"]
    assert set(skx["reporting_jurisdictions"]) == {"US"}

    # Resolving CIK 0001065837 directly resolves to Skechers, NEVER Infosys
    cik_res = resolve_issuer("0001065837")
    assert cik_res["cik"] == "0001065837"
    assert "Skechers" in cik_res["legal_name"]


def test_submissions_fetch_rejects_identity_mismatch():
    """Verify that if SEC returns Skechers submissions when Infosys was requested, fetch fails."""
    # Mock returning Skechers payload
    skechers_payload = make_submissions_payload(1065837, "SKECHERS USA INC", "SKX")

    def mock_fetcher(url, **kw):
        return make_mock_http(skechers_payload, url)

    # Calling fetch_sec_submissions for Infosys with mismatched Skechers data must fail
    res = sec_edgar.fetch_sec_submissions("Infosys", http_fetcher=mock_fetcher)
    assert res["status"] == "FAILED"
    assert len(res["items"]) == 0


def test_submissions_fetch_succeeds_when_identity_matches():
    """Verify that when SEC returns matching company identity, fetch succeeds."""
    infy_payload = make_submissions_payload(1067491, "INFOSYS LTD", "INFY", form="20-F")

    def mock_fetcher(url, **kw):
        return make_mock_http(infy_payload, url)

    res = sec_edgar.fetch_sec_submissions("Infosys", http_fetcher=mock_fetcher)
    assert res["status"] == "SUCCESS"
    assert len(res["items"]) == 1
    assert res["items"][0]["cik"] == "0001067491"
    assert "INFOSYS" in res["items"][0]["company_name"].upper()


def test_direct_numeric_cik_request_not_silently_reassigned():
    """Verify that a direct numeric CIK query preserves official SEC company name."""
    skechers_payload = make_submissions_payload(1065837, "SKECHERS USA INC", "SKX")

    def mock_fetcher(url, **kw):
        return make_mock_http(skechers_payload, url)

    res = sec_edgar.fetch_sec_submissions("0001065837", http_fetcher=mock_fetcher)
    assert res["status"] == "SUCCESS"
    assert len(res["items"]) == 1
    assert res["items"][0]["company_name"] == "SKECHERS USA INC"
    assert res["items"][0]["cik"] == "0001065837"
    # Title must be for Skechers, not any other entity
    fragments = sec_edgar.normalize_sec_items(res["items"], "q1", "regulatory_filing", "0001065837")
    assert "SKECHERS" in fragments[0].title


def test_financial_qualification_blocks_mismatched_issuer():
    """Verify that financial fact qualification stops completely on CIK/issuer mismatch."""
    # Synthesize document with Skechers CIK (0001065837)
    fake_skx_item = {
        "url": "https://data.sec.gov/api/xbrl/companyfacts/CIK0001065837.json",
        "canonical_url": "https://data.sec.gov/api/xbrl/companyfacts/CIK0001065837.json",
        "content": "Sample content",
        "metadata": {
            "read_success": True,
            "page_metadata": {
                "financial_document": {
                    "schema": "sec-xbrl-facts-v1",
                    "source_url": "https://data.sec.gov/api/xbrl/companyfacts/CIK0001065837.json",
                    "cik": "0001065837",
                    "issuer": "Skechers U.S.A., Inc.",
                    "facts": [{"val": 100}],
                }
            }
        }
    }
    # Asking to qualify for Infosys must return None
    doc = qualified_document(fake_skx_item, "Infosys")
    assert doc is None, "Expected qualified_document to reject Skechers document when subject is Infosys"

    # Scout disclosures must have zero facts for Infosys
    disclosures = scout_financial_disclosures([fake_skx_item], "Infosys")
    assert disclosures["distinct_facts"] == 0
    assert disclosures["status"] == "NO_QUALIFIED_STRUCTURED_DISCLOSURES"


def test_scout_jurisdiction_routing_for_indian_companies():
    """Verify Indian company SEC routing: dual-listed ADRs (Infosys) plan SEC, non-ADRs (TCS) plan SEBI only."""
    planner = SourcePlanningEngine()

    # 1. Infosys: Indian + US reporting -> Plans SEC EDGAR and Indian market search
    infy_plan = planner.plan(
        "Infosys quarterly revenue results",
        entity="Infosys",
        domain="financial",
        agent="scout",
    )
    sec_actions = [a for a in infy_plan.actions if a.channel == "sec_edgar"]
    assert len(sec_actions) > 0, "Infosys must plan SEC EDGAR"
    assert any("NSE BSE" in a.query for a in infy_plan.actions), "Infosys must also discover Indian disclosures"

    # 2. TCS: Indian only (no CIK) -> Does NOT plan SEC EDGAR, plans SEBI/NSE/BSE
    tcs_plan = planner.plan(
        "TCS quarterly revenue results",
        entity="TCS",
        domain="financial",
        agent="scout",
    )
    tcs_sec = [a for a in tcs_plan.actions if a.channel == "sec_edgar"]
    assert len(tcs_sec) == 0, "TCS must NOT plan SEC EDGAR"
    assert any("SEBI" in a.query or "NSE BSE" in a.query for a in tcs_plan.actions), "TCS must plan Indian regulatory search"

def test_fetch_sec_submissions_accepts_static_map_alias_google():
    """Verify that static-map alias 'Google' -> Alphabet CIK 0001652044 is accepted (Comment 12)."""
    from unittest.mock import patch
    from backend.infrastructure.acquisition.adapters.authoritative.sec_edgar import fetch_sec_submissions
    from backend.infrastructure.acquisition.network.http import BoundedHTTPResponse

    fake_submissions = {
        "cik": "0001652044",
        "entityType": "Operating",
        "sic": "7370",
        "sicDescription": "SERVICES-COMPUTER PROGRAMMING, DATA PROCESSING, ETC.",
        "name": "Alphabet Inc.",
        "tickers": ["GOOGL", "GOOG"],
        "exchanges": ["Nasdaq", "Nasdaq"],
        "ein": "611767919",
        "description": "Alphabet Inc.",
        "website": "https://abc.xyz",
        "stateOfIncorporation": "DE",
        "stateOfIncorporationDescription": "DELAWARE",
        "fiscalYearEnd": "1231",
        "filings": {"recent": {"accessionNumber": [], "filingDate": [], "reportDate": [], "acceptanceDateTime": [], "act": [], "form": [], "fileNumber": [], "filmNumber": [], "items": [], "size": [], "isXBRL": [], "isInlineXBRL": [], "primaryDocument": [], "primaryDocDescription": []}},
    }
    raw_payload = json.dumps(fake_submissions).encode("utf-8")
    mock_resp = BoundedHTTPResponse(
        body=raw_payload,
        endpoint="https://data.sec.gov/submissions/CIK0001652044.json",
        status_code=200,
        content_type="application/json",
        headers={"content-type": "application/json"},
        latency_ms=50,
        attempts=1,
    )

    with patch("backend.infrastructure.acquisition.adapters.authoritative.sec_edgar.fetch_public_http", return_value=mock_resp):
        res = fetch_sec_submissions("Google")
        assert res["status"] == "SUCCESS", f"Expected SUCCESS for Google, got: {res}"
        assert res["company_name"] == "Alphabet Inc."
        assert res["cik"] == "0001652044"
