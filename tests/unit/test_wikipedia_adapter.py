"""Unit tests for WikipediaAdapter."""

import json
from unittest.mock import patch

from backend.infrastructure.acquisition.adapters.encyclopedia.wikipedia import WikipediaAdapter
from backend.infrastructure.acquisition.network.http import BoundedHTTPResponse
from backend.services.agent_reach.channels import (
    CandidateSource,
    FetchedDocument,
    RetrievalRequest,
)


def test_wikipedia_adapter_can_handle():
    adapter = WikipediaAdapter()
    assert adapter.can_handle(CandidateSource(url="https://en.wikipedia.org/wiki/Nvidia")) is True
    assert adapter.can_handle(CandidateSource(url="https://commons.wikimedia.org/wiki/File:Test.jpg")) is False
    assert adapter.can_handle(CandidateSource(url="https://example.com/other", platform="wikipedia")) is False
    assert adapter.can_handle(CandidateSource(url="https://example.com/other")) is False


def test_wikipedia_adapter_discover():
    adapter = WikipediaAdapter()
    sample_search_resp = {
        "query": {
            "search": [
                {
                    "title": "Nvidia",
                    "pageid": 21250,
                    "wordcount": 8500,
                    "snippet": "<span>Nvidia</span> is an American multinational corporation and technology company.",
                    "timestamp": "2026-10-15T12:00:00Z",
                }
            ]
        }
    }
    mock_resp = BoundedHTTPResponse(
        body=json.dumps(sample_search_resp).encode("utf-8"),
        endpoint="https://en.wikipedia.org/w/api.php?action=query",
        status_code=200,
        content_type="application/json",
        headers={},
        latency_ms=30,
        attempts=1,
    )

    with patch("backend.infrastructure.acquisition.adapters.encyclopedia.wikipedia.fetch_public_http", return_value=mock_resp):
        candidates = adapter.discover("Nvidia", limit=1)
        assert len(candidates) == 1
        c = candidates[0]
        assert c.platform == "wikipedia"
        assert "Nvidia" in c.title
        assert c.metadata["pageid"] == 21250
        assert "Nvidia is an American" in c.snippet


def test_wikipedia_adapter_acquire_and_normalize():
    adapter = WikipediaAdapter()
    sample_extract_resp = {
        "query": {
            "pages": {
                "21250": {
                    "pageid": 21250,
                    "title": "Nvidia",
                    "extract": "Nvidia Corporation is a company specializing in graphic processing units and artificial intelligence hardware. Founded in 1993 by Jensen Huang...",
                    "fullurl": "https://en.wikipedia.org/wiki/Nvidia",
                    "pageprops": {
                        "wikibase-shortdesc": "American multinational technology company"
                    }
                }
            }
        }
    }
    mock_resp = BoundedHTTPResponse(
        body=json.dumps(sample_extract_resp).encode("utf-8"),
        endpoint="https://en.wikipedia.org/w/api.php?action=query",
        status_code=200,
        content_type="application/json",
        headers={},
        latency_ms=45,
        attempts=1,
    )

    cand = CandidateSource(
        url="https://en.wikipedia.org/wiki/Nvidia",
        platform="wikipedia",
        title="Nvidia — Wikipedia",
        metadata={"wiki_title": "Nvidia"},
    )

    with patch("backend.infrastructure.acquisition.adapters.encyclopedia.wikipedia.fetch_public_http", return_value=mock_resp):
        doc = adapter.acquire(cand, RetrievalRequest())
        assert doc.status == "SUCCESS"
        assert "Jensen Huang" in doc.raw_content
        assert "American multinational technology company" in doc.raw_content

        frags = adapter.normalize(doc, cand, RetrievalRequest())
        assert len(frags) == 1
        frag = frags[0]
        assert frag.platform == "wikipedia"
        assert "Jensen Huang" in frag.content
        assert frag.raw_metadata["source_domain"] == "wikipedia.org"
