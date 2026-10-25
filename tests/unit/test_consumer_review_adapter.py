"""Unit tests for ConsumerReviewAdapter."""

from unittest.mock import patch

from backend.infrastructure.acquisition.adapters.consumer.trustpilot import ConsumerReviewAdapter
from backend.infrastructure.acquisition.network.http import BoundedHTTPResponse
from backend.services.agent_reach.channels import (
    CandidateSource,
    FetchedDocument,
    RetrievalRequest,
)


def test_consumer_review_adapter_can_handle():
    adapter = ConsumerReviewAdapter()
    assert adapter.can_handle(CandidateSource(url="https://www.trustpilot.com/review/acmebrand.com")) is True
    assert adapter.can_handle(CandidateSource(url="https://www.complaintsboard.com/acme-inc-b123")) is True
    assert adapter.can_handle(CandidateSource(url="https://example.com/other", platform="trustpilot")) is False
    assert adapter.can_handle(CandidateSource(url="https://example.com/other")) is False


def test_consumer_review_adapter_discover():
    adapter = ConsumerReviewAdapter()
    assert adapter.discover("Acme Corp", limit=1) == []  # Never guess a company domain.
    candidates = adapter.discover("https://www.trustpilot.com/review/acmebrand.com", limit=1)
    assert len(candidates) == 1
    c = candidates[0]
    assert c.platform == "trustpilot"
    assert "trustpilot.com/review/" in c.url


def test_consumer_review_adapter_acquire_and_normalize():
    adapter = ConsumerReviewAdapter()
    sample_html = """
    <html><body>
    <script id="__NEXT_DATA__" type="application/json">
    {
      "props": {
        "pageProps": {
          "businessUnit": {
            "trustScore": 1.8,
            "numberOfReviews": 420
          },
          "reviews": [
            {
              "title": "Complete scam website",
              "text": "Received counterfeit goods after waiting 6 weeks. Customer support refuses refund.",
              "rating": 1,
              "dates": {"publishedDate": "2026-03-01"}
            }
          ]
        }
      }
    }
    </script>
    </body></html>
    """
    mock_resp = BoundedHTTPResponse(
        body=sample_html.encode("utf-8"),
        endpoint="https://www.trustpilot.com/review/acmecorp.com",
        status_code=200,
        content_type="text/html",
        headers={},
        latency_ms=45,
        attempts=1,
    )

    cand = CandidateSource(
        url="https://www.trustpilot.com/review/acmecorp.com",
        platform="trustpilot",
        title="Acme Corp Consumer Reviews",
        metadata={"brand": "Acme Corp"},
    )

    with patch("backend.infrastructure.acquisition.adapters.consumer.trustpilot.fetch_public_http", return_value=mock_resp):
        doc = adapter.acquire(cand, RetrievalRequest())
        assert doc.status == "SUCCESS"
        assert "1.8/5.0" in doc.raw_content
        assert "Received counterfeit goods" in doc.raw_content

        frags = adapter.normalize(doc, cand, RetrievalRequest())
        assert len(frags) == 1
        frag = frags[0]
        assert frag.platform == "trustpilot"
        assert "counterfeit goods" in frag.content
        assert frag.raw_metadata["source_domain"] == "trustpilot.com"
