"""Unit tests for SubstackAdapter."""

import json
from unittest.mock import patch

from backend.infrastructure.acquisition.adapters.news.substack import SubstackAdapter
from backend.infrastructure.acquisition.network.http import BoundedHTTPResponse
from backend.services.agent_reach.channels import (
    CandidateSource,
    FetchedDocument,
    RetrievalRequest,
)


def test_substack_adapter_can_handle():
    adapter = SubstackAdapter()
    assert adapter.can_handle(CandidateSource(url="https://pragmaticengineer.substack.com/p/engineering-executives")) is True
    assert adapter.can_handle(CandidateSource(url="https://substack.com/@thediff")) is True
    assert adapter.can_handle(CandidateSource(url="https://example.com/other", platform="substack")) is False
    assert adapter.can_handle(CandidateSource(url="https://example.com/other")) is False


def test_substack_adapter_discover():
    adapter = SubstackAdapter()
    sample_posts = [
        {
            "id": 101,
            "title": "State of AI Infrastructure",
            "slug": "state-of-ai-infra",
            "subtitle": "A deep dive into GPU clustering and network interconnects.",
            "post_date": "2026-03-01T08:00:00Z",
            "canonical_url": "https://pragmaticengineer.substack.com/p/state-of-ai-infra",
        }
    ]
    mock_resp = BoundedHTTPResponse(
        body=json.dumps(sample_posts).encode("utf-8"),
        endpoint="https://pragmaticengineer.substack.com/api/v1/posts",
        status_code=200,
        content_type="application/json",
        headers={},
        latency_ms=35,
        attempts=1,
    )

    with patch("backend.infrastructure.acquisition.adapters.news.substack.fetch_public_http", return_value=mock_resp):
        candidates = adapter.discover("AI Infrastructure", limit=1)
        assert len(candidates) >= 1
        c = candidates[0]
        assert c.platform == "substack"
        assert "State of AI Infrastructure" in c.title


def test_substack_adapter_acquire_and_normalize():
    adapter = SubstackAdapter()
    sample_post_detail = {
        "title": "State of AI Infrastructure",
        "subtitle": "A deep dive into GPU clustering and network interconnects.",
        "body_html": "<p>Massive clusters are transforming datacenter interconnect topologies across the globe.</p>",
        "publishedBylines": [{"name": "Gergely Orosz"}],
    }
    mock_resp = BoundedHTTPResponse(
        body=json.dumps(sample_post_detail).encode("utf-8"),
        endpoint="https://pragmaticengineer.substack.com/api/v1/posts/state-of-ai-infra",
        status_code=200,
        content_type="application/json",
        headers={},
        latency_ms=40,
        attempts=1,
    )

    cand = CandidateSource(
        url="https://pragmaticengineer.substack.com/p/state-of-ai-infra",
        platform="substack",
        title="State of AI Infrastructure",
        metadata={"slug": "state-of-ai-infra"},
    )

    with patch("backend.infrastructure.acquisition.adapters.news.substack.fetch_public_http", return_value=mock_resp):
        doc = adapter.acquire(cand, RetrievalRequest())
        assert doc.status == "SUCCESS"
        assert "Gergely Orosz" in doc.raw_content
        assert "Massive clusters are transforming" in doc.raw_content

        frags = adapter.normalize(doc, cand, RetrievalRequest())
        assert len(frags) == 1
        frag = frags[0]
        assert frag.platform == "substack"
        assert frag.author == "Gergely Orosz"
        assert "interconnect topologies" in frag.content
