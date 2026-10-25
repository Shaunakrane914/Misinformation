"""Unit tests for FactCheckAdapter and ClaimReview parsing."""

import json
from unittest.mock import MagicMock, patch

from backend.infrastructure.acquisition.adapters.factcheck.factcheck_adapter import FactCheckAdapter
from backend.infrastructure.acquisition.network.http import BoundedHTTPResponse
from backend.services.agent_reach.channels import (
    CandidateSource,
    ContentDepth,
    FetchedDocument,
    RetrievalRequest,
)


def test_factcheck_adapter_can_handle():
    adapter = FactCheckAdapter()

    cand_snopes = CandidateSource(url="https://www.snopes.com/fact-check/test-rumor/")
    assert adapter.can_handle(cand_snopes) is True

    cand_politifact = CandidateSource(url="https://www.politifact.com/factchecks/2026/statement/")
    assert adapter.can_handle(cand_politifact) is True

    cand_altnews = CandidateSource(url="https://www.altnews.in/viral-claim-verification/")
    assert adapter.can_handle(cand_altnews) is True

    cand_random = CandidateSource(url="https://random-blog.example.com/post")
    assert adapter.can_handle(cand_random) is False


def test_factcheck_adapter_discover():
    adapter = FactCheckAdapter()
    sample_api_response = {
        "claims": [
            {
                "text": "The moon is made of green cheese.",
                "claimant": "Social Media Users",
                "claimReview": [
                    {
                        "publisher": {"name": "Snopes"},
                        "url": "https://www.snopes.com/fact-check/moon-cheese/",
                        "title": "Moon Cheese Investigation",
                        "textualRating": "False",
                    }
                ],
            }
        ]
    }
    mock_resp = BoundedHTTPResponse(
        body=json.dumps(sample_api_response).encode("utf-8"),
        endpoint="https://factchecktools.googleapis.com",
        status_code=200,
        content_type="application/json",
        headers={},
        latency_ms=50,
        attempts=1,
    )

    with patch("backend.infrastructure.acquisition.adapters.factcheck.factcheck_adapter.fetch_public_http", return_value=mock_resp):
        candidates = adapter.discover("moon cheese", limit=2)
        assert len(candidates) == 1
        cand = candidates[0]
        assert cand.platform == "factcheck"
        assert "Snopes" in cand.title
        assert cand.metadata["claimant"] == "Social Media Users"
        assert cand.metadata["textual_rating"] == "False"


def test_factcheck_adapter_normalize_ld_json():
    adapter = FactCheckAdapter()
    cand = CandidateSource(url="https://www.snopes.com/fact-check/sample/")
    req = RetrievalRequest()

    sample_html = """
    <html>
      <head>
        <script type="application/ld+json">
        {
          "@context": "https://schema.org",
          "@type": "ClaimReview",
          "claimReviewed": "Electric cars cause earthquakes",
          "reviewRating": {
            "@type": "Rating",
            "ratingValue": "1",
            "alternateName": "False"
          }
        }
        </script>
      </head>
      <body>
        <p>Full article debunking the claim...</p>
      </body>
    </html>
    """
    doc = FetchedDocument(
        url="https://www.snopes.com/fact-check/sample/",
        status="SUCCESS",
        raw_content=sample_html,
    )

    frags = adapter.normalize(doc, cand, req)
    assert len(frags) == 1
    f = frags[0]
    assert f.platform == "factcheck"
    assert "False" in f.content
    assert f.raw_metadata.get("extracted_verdict") == "False"
    assert f.raw_metadata.get("is_fact_check") is True
