"""Unit tests for YahooFinanceAdapter."""

import json
from unittest.mock import patch

from backend.infrastructure.acquisition.adapters.financial.yahoo_finance import YahooFinanceAdapter
from backend.infrastructure.acquisition.network.http import BoundedHTTPResponse
from backend.services.agent_reach.channels import (
    CandidateSource,
    FetchedDocument,
    RetrievalRequest,
)


def test_yahoo_finance_adapter_can_handle():
    adapter = YahooFinanceAdapter()
    assert adapter.can_handle(CandidateSource(url="https://finance.yahoo.com/quote/NVDA")) is True
    assert adapter.can_handle(CandidateSource(url="https://finance.yahoo.com/news/nvidia-earnings-call")) is True
    assert adapter.can_handle(CandidateSource(url="https://example.com/other", platform="yahoo_finance")) is False
    assert adapter.can_handle(CandidateSource(url="https://example.com/other")) is False


def test_yahoo_finance_adapter_discover():
    adapter = YahooFinanceAdapter()
    sample_search_data = {
        "quotes": [
            {
                "symbol": "NVDA",
                "shortname": "NVIDIA Corporation",
                "longname": "NVIDIA Corporation",
                "exchange": "NMS",
                "quoteType": "EQUITY",
                "industry": "Semiconductors",
                "sector": "Technology",
            }
        ],
        "news": [
            {
                "uuid": "news-12345",
                "title": "Nvidia Reports Record Quarterly Revenue",
                "publisher": "PR Newswire",
                "link": "https://finance.yahoo.com/news/nvidia-record-rev-123.html",
                "providerPublishTime": 1770000000,
                "relatedTickers": ["NVDA"],
            }
        ],
    }
    mock_resp = BoundedHTTPResponse(
        body=json.dumps(sample_search_data).encode("utf-8"),
        endpoint="https://query2.finance.yahoo.com/v1/finance/search",
        status_code=200,
        content_type="application/json",
        headers={},
        latency_ms=40,
        attempts=1,
    )

    with patch("backend.infrastructure.acquisition.adapters.financial.yahoo_finance.fetch_public_http", return_value=mock_resp):
        candidates = adapter.discover("NVDA", limit=2)
        assert len(candidates) >= 1
        has_quote = any(c.metadata.get("type") == "quote" for c in candidates)
        has_news = any(c.metadata.get("type") == "news" for c in candidates)
        assert has_quote or has_news


def test_yahoo_finance_adapter_acquire_and_normalize():
    adapter = YahooFinanceAdapter()
    sample_article_html = """
    <html><body>
    <article>
    <h1>Nvidia Reports Record Quarterly Revenue of $35 Billion</h1>
    <p>SANTA CLARA, Calif. — NVIDIA today reported revenue for the quarter of $35.1 billion, up 94% from a year ago.</p>
    <p>Data Center revenue surged to $30.8 billion driven by Hopper GPU computing platforms.</p>
    </article>
    </body></html>
    """
    mock_resp = BoundedHTTPResponse(
        body=sample_article_html.encode("utf-8"),
        endpoint="https://finance.yahoo.com/news/nvidia-record-rev-123.html",
        status_code=200,
        content_type="text/html",
        headers={},
        latency_ms=50,
        attempts=1,
    )

    cand = CandidateSource(
        url="https://finance.yahoo.com/news/nvidia-record-rev-123.html",
        platform="yahoo_finance",
        title="Nvidia Reports Record Quarterly Revenue",
        metadata={"symbol": "NVDA", "publisher": "PR Newswire"},
    )

    with patch("backend.infrastructure.acquisition.adapters.financial.yahoo_finance.fetch_public_http", return_value=mock_resp):
        doc = adapter.acquire(cand, RetrievalRequest())
        assert doc.status == "SUCCESS"
        assert "$35.1 billion" in doc.raw_content

        frags = adapter.normalize(doc, cand, RetrievalRequest())
        assert len(frags) == 1
        frag = frags[0]
        assert frag.platform == "yahoo_finance"
        assert "PR Newswire" in frag.author
        assert "$35.1 billion" in frag.content
