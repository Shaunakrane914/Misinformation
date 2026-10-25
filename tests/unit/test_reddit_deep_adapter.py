"""Unit tests for RedditDeepAdapter."""

import json
from unittest.mock import patch

from backend.infrastructure.acquisition.adapters.social.reddit_deep import RedditDeepAdapter
from backend.infrastructure.acquisition.network.http import BoundedHTTPResponse
from backend.services.agent_reach.channels import (
    CandidateSource,
    FetchedDocument,
    RetrievalRequest,
)


def test_reddit_deep_adapter_can_handle():
    adapter = RedditDeepAdapter()
    assert adapter.can_handle(CandidateSource(url="https://www.reddit.com/r/technology/comments/abc123/future_of_chips")) is True
    assert adapter.can_handle(CandidateSource(url="https://example.com/other", platform="reddit_deep")) is False
    assert adapter.can_handle(CandidateSource(url="https://example.com/other")) is False


def test_reddit_deep_adapter_discover():
    adapter = RedditDeepAdapter()
    sample_posts = {
        "data": [
            {
                "id": "post999",
                "title": "Quantum Computing Breakthrough Discussion",
                "selftext": "Researchers have demonstrated error correction in 100-qubit processors.",
                "author": "tech_enthusiast",
                "score": 1420,
                "num_comments": 85,
                "created_utc": 1770000000,
                "permalink": "/r/technology/comments/post999/quantum_breakthrough",
            }
        ]
    }
    mock_resp = BoundedHTTPResponse(
        body=json.dumps(sample_posts).encode("utf-8"),
        endpoint="https://arctic-shift.photon-reddit.com/api/posts/search",
        status_code=200,
        content_type="application/json",
        headers={},
        latency_ms=40,
        attempts=1,
    )

    with patch("backend.infrastructure.acquisition.adapters.social.reddit_deep.fetch_public_http", return_value=mock_resp):
        candidates = adapter.discover("Quantum Computing", limit=1)
        assert len(candidates) >= 1
        c = candidates[0]
        assert c.platform == "reddit_deep"
        assert "Quantum Computing Breakthrough" in c.title


def test_reddit_deep_adapter_acquire_and_normalize():
    adapter = RedditDeepAdapter()
    sample_post = {
        "data": [
            {
                "id": "post999",
                "title": "Quantum Computing Breakthrough Discussion",
                "selftext": "Researchers have demonstrated error correction in 100-qubit processors.",
                "author": "tech_enthusiast",
                "score": 1420,
            }
        ]
    }
    sample_comments = {
        "data": [
            {
                "id": "comm1",
                "author": "physicist_guy",
                "score": 350,
                "body": "The threshold theorem indicates fault tolerance is scalable if gate fidelity exceeds 99.9%.",
                "created_utc": 1770000100,
            },
            {
                "id": "comm2",
                "author": "skeptic_coder",
                "score": 120,
                "body": "Still waiting for practical post-NISQ quantum advantage outside of synthetic sampling.",
                "created_utc": 1770000200,
            },
        ]
    }

    cand = CandidateSource(
        url="https://www.reddit.com/r/technology/comments/post999/quantum_breakthrough",
        platform="reddit_deep",
        title="Quantum Computing Breakthrough",
        metadata={
            "post_id": "post999",
            "subreddit": "technology",
            "author": "tech_enthusiast",
            "score": 1420,
        },
    )

    def mock_fetch(url, **kwargs):
        if "/comments/" in url:
            body = json.dumps(sample_comments).encode("utf-8")
        else:
            body = json.dumps(sample_post).encode("utf-8")
        return BoundedHTTPResponse(
            body=body,
            endpoint=url,
            status_code=200,
            content_type="application/json",
            headers={},
            latency_ms=30,
            attempts=1,
        )

    with patch("backend.infrastructure.acquisition.adapters.social.reddit_deep.fetch_public_http", side_effect=mock_fetch):
        doc = adapter.acquire(cand, RetrievalRequest())
        assert doc.status == "SUCCESS"
        assert "physicist_guy" in doc.raw_content
        assert "threshold theorem indicates" in doc.raw_content
        assert "skeptic_coder" in doc.raw_content

        frags = adapter.normalize(doc, cand, RetrievalRequest())
        assert len(frags) == 1
        frag = frags[0]
        assert frag.platform == "reddit_deep"
        assert "threshold theorem" in frag.content
