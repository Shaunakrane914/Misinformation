"""Unit tests for SecFilingsFullAdapter."""

import json
import gzip
from unittest.mock import patch

from backend.infrastructure.acquisition.adapters.regulatory.sec_filings_full import SecFilingsFullAdapter
from backend.infrastructure.acquisition.network.http import BoundedHTTPResponse
from backend.services.agent_reach.channels import (
    CandidateSource,
    FetchedDocument,
    RetrievalRequest,
)


def test_gzipped_sec_capture_is_decoded_boundedly_and_empty_stays_empty():
    adapter = SecFilingsFullAdapter()
    candidate = CandidateSource(url="https://www.sec.gov/Archives/edgar/data/123/report.htm")
    for body, status in [(gzip.compress(b"<p>Observed regulatory passage.</p>"), "SUCCESS"),
                         (b"", "EMPTY_CONTENT")]:
        response = BoundedHTTPResponse(body=body, endpoint=candidate.url, status_code=200,
            content_type="text/html", headers={}, latency_ms=1, attempts=1)
        with patch("backend.infrastructure.acquisition.adapters.regulatory.sec_filings_full.fetch_public_http", return_value=response):
            result = adapter.acquire(candidate, RetrievalRequest())
        assert result.status == status
        if status == "SUCCESS":
            assert "Observed regulatory passage" in result.raw_content
            assert result.raw_metadata["form"] == "UNSPECIFIED"


def test_sec_filings_full_adapter_can_handle():
    adapter = SecFilingsFullAdapter()
    assert adapter.can_handle(CandidateSource(url="https://www.sec.gov/Archives/edgar/data/1045810/000104581026000050/nvda-10k.htm")) is True
    assert adapter.can_handle(CandidateSource(url="https://sec.gov/edgar/data/nvda-10-k")) is True
    assert adapter.can_handle(CandidateSource(url="https://example.com/other", platform="sec_filings_full")) is False
    assert adapter.can_handle(CandidateSource(url="https://example.com/other")) is False


def test_sec_filings_full_adapter_discover():
    adapter = SecFilingsFullAdapter()
    sample_submissions = {
        "name": "NVIDIA CORP",
        "filings": {
            "recent": {
                "form": ["10-K", "10-Q"],
                "filingDate": ["2026-02-20", "2026-05-25"],
                "accessionNumber": ["0001045810-26-000010", "0001045810-26-000030"],
                "primaryDocument": ["nvda-20260128.htm", "nvda-20260428.htm"],
                "primaryDocDescription": ["Annual Report Form 10-K", "Quarterly Report Form 10-Q"],
            }
        }
    }
    mock_resp = BoundedHTTPResponse(
        body=json.dumps(sample_submissions).encode("utf-8"),
        endpoint="https://data.sec.gov/submissions/CIK0001045810.json",
        status_code=200,
        content_type="application/json",
        headers={},
        latency_ms=40,
        attempts=1,
    )

    with patch("backend.infrastructure.acquisition.adapters.regulatory.sec_filings_full.fetch_public_http", return_value=mock_resp):
        candidates = adapter.discover("NVDA", limit=2)
        assert len(candidates) == 2
        c = candidates[0]
        assert c.platform == "sec_filings_full"
        assert "Form 10-K" in c.title
        assert c.metadata["form"] == "10-K"
        assert c.metadata["company_name"] == "NVIDIA CORP"
        assert c.metadata["primary_source"] is True


def test_sec_filings_full_adapter_acquire_and_normalize():
    adapter = SecFilingsFullAdapter()
    sample_html = """
    <html><body>
    <h1>UNITED STATES SECURITIES AND EXCHANGE COMMISSION</h1>
    <h2>FORM 10-K ANNUAL REPORT</h2>
    <p>ITEM 1. BUSINESS.</p>
    <p>NVIDIA Corporation pioneered accelerated computing to tackle challenges ordinary computers cannot solve.</p>
    <p>ITEM 7. MANAGEMENT'S DISCUSSION AND ANALYSIS OF FINANCIAL CONDITION.</p>
    <p>Fiscal 2026 Revenue was driven by exceptional enterprise demand for Hopper and Blackwell AI architectures.</p>
    </body></html>
    """
    mock_resp = BoundedHTTPResponse(
        body=sample_html.encode("utf-8"),
        endpoint="https://www.sec.gov/Archives/edgar/data/1045810/000104581026000010/nvda.htm",
        status_code=200,
        content_type="text/html",
        headers={},
        latency_ms=50,
        attempts=1,
    )

    cand = CandidateSource(
        url="https://www.sec.gov/Archives/edgar/data/1045810/000104581026000010/nvda.htm",
        platform="sec_filings_full",
        title="[NVIDIA CORP] Full SEC Form 10-K",
        metadata={
            "company_name": "NVIDIA CORP",
            "form": "10-K",
            "filing_date": "2026-02-20",
            "ticker": "NVDA",
            "cik": "0001045810",
        },
    )

    with patch("backend.infrastructure.acquisition.adapters.regulatory.sec_filings_full.fetch_public_http", return_value=mock_resp):
        doc = adapter.acquire(cand, RetrievalRequest())
        assert doc.status == "SUCCESS"
        assert "Blackwell AI architectures" in doc.raw_content
        assert "ITEM 1. BUSINESS" in doc.raw_content

        frags = adapter.normalize(doc, cand, RetrievalRequest())
        assert len(frags) == 1
        frag = frags[0]
        assert frag.platform == "sec_filings_full"
        assert "Blackwell" in frag.content
        assert frag.content_depth == "FULL_ARTICLE"
        assert frag.raw_metadata["source_role"] == "primary"
