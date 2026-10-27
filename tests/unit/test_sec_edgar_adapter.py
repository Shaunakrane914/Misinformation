"""Unit tests for SecEdgarAdapter."""

import json
from unittest.mock import MagicMock, patch

from backend.infrastructure.acquisition.adapters.regulatory.sec_edgar import SecEdgarAdapter
from backend.infrastructure.acquisition.network.http import BoundedHTTPResponse
from backend.services.agent_reach.channels import (
    CandidateSource,
    FetchedDocument,
    RetrievalRequest,
)


def test_sec_edgar_adapter_can_handle():
    adapter = SecEdgarAdapter()
    assert adapter.can_handle(CandidateSource(url="https://www.sec.gov/edgar/data/1045810/nvda-10q")) is True
    assert adapter.can_handle(CandidateSource(url="https://sec.gov/Archives/edgar/data/1045810/doc.htm")) is True
    assert adapter.can_handle(CandidateSource(url="https://example.com/other")) is False


def test_sec_edgar_adapter_discover():
    adapter = SecEdgarAdapter()
    sample_sec_response = {
        "name": "NVIDIA CORP",
        "filings": {
            "recent": {
                "form": ["10-Q", "8-K"],
                "filingDate": ["2026-08-25", "2026-07-15"],
                "accessionNumber": ["0001045810-26-000050", "0001045810-26-000045"],
                "primaryDocument": ["nvda-20260728.htm", "nvda-20260715.htm"],
                "primaryDocDescription": ["Quarterly Report", "Current Report"],
            }
        },
    }
    mock_resp = BoundedHTTPResponse(
        body=json.dumps(sample_sec_response).encode("utf-8"),
        endpoint="https://data.sec.gov/submissions/CIK0001045810.json",
        status_code=200,
        content_type="application/json",
        headers={},
        latency_ms=45,
        attempts=1,
    )

    with patch("backend.infrastructure.acquisition.adapters.regulatory.sec_edgar.fetch_public_http", return_value=mock_resp):
        candidates = adapter.discover("NVDA", limit=2)
        assert len(candidates) == 2
        c1 = candidates[0]
        assert c1.platform == "sec_edgar"
        assert "10-Q" in c1.title
        assert c1.metadata["form"] == "10-Q"
        assert c1.metadata["ticker"] == "NVDA"
        assert "000104581026000050" in c1.url


def test_sec_edgar_adapter_normalize():
    adapter = SecEdgarAdapter()
    cand = CandidateSource(
        url="https://www.sec.gov/edgar/doc",
        title="[NVIDIA CORP] SEC Form 10-Q",
        snippet="Official 10-Q filing",
        metadata={
            "company_name": "NVIDIA CORP",
            "form": "10-Q",
            "filing_date": "2026-08-25",
            "cik": "0001045810",
        },
    )
    doc = FetchedDocument(
        url=cand.url,
        status="SUCCESS",
        raw_content="Item 1. Financial Statements. Consolidated revenue for the quarter was...",
    )
    frags = adapter.normalize(doc, cand, RetrievalRequest())
    assert len(frags) == 1
    f = frags[0]
    assert f.platform == "sec_edgar"
    assert f.score == 98.0
    assert f.raw_metadata["is_official_regulatory"] is True
    assert f.raw_metadata["primary_source"] is True
    assert f.raw_metadata["form_type"] == "10-Q"
