"""Unit tests for ArxivAdapter."""

from unittest.mock import patch

from backend.infrastructure.acquisition.adapters.academic.arxiv import ArxivAdapter
from backend.infrastructure.acquisition.network.http import BoundedHTTPResponse
from backend.services.agent_reach.channels import (
    CandidateSource,
    FetchedDocument,
    RetrievalRequest,
)

SAMPLE_ATOM_FEED = """<?xml version="1.0" encoding="UTF-8"?>
<feed xmlns="http://www.w3.org/2005/Atom">
  <entry>
    <id>http://arxiv.org/abs/2602.12345v1</id>
    <published>2026-02-14T10:00:00Z</published>
    <title>Scaling Transformer Architectures Beyond 100M Tokens</title>
    <summary>We propose a novel sparse attention mechanism that achieves linear time complexity.</summary>
    <author><name>Alice Smith</name></author>
    <author><name>Bob Jones</name></author>
    <category term="cs.LG" scheme="http://arxiv.org/schemas/atom"/>
  </entry>
</feed>
"""


def test_arxiv_adapter_can_handle():
    adapter = ArxivAdapter()
    assert adapter.can_handle(CandidateSource(url="https://arxiv.org/abs/2602.12345")) is True
    assert adapter.can_handle(CandidateSource(url="https://arxiv.org/pdf/2602.12345.pdf")) is True
    assert adapter.can_handle(CandidateSource(url="https://example.com/other", platform="arxiv")) is False
    assert adapter.can_handle(CandidateSource(url="https://example.com/other")) is False


def test_arxiv_adapter_discover():
    adapter = ArxivAdapter()
    mock_resp = BoundedHTTPResponse(
        body=SAMPLE_ATOM_FEED.encode("utf-8"),
        endpoint="https://export.arxiv.org/api/query",
        status_code=200,
        content_type="application/atom+xml",
        headers={},
        latency_ms=60,
        attempts=1,
    )

    with patch("backend.infrastructure.acquisition.adapters.academic.arxiv.fetch_public_http", return_value=mock_resp):
        candidates = adapter.discover("Transformer Architecture", limit=1)
        assert len(candidates) == 1
        c = candidates[0]
        assert c.platform == "arxiv"
        assert "Scaling Transformer Architectures" in c.title
        assert c.metadata["arxiv_id"] == "2602.12345v1"
        assert "Alice Smith" in c.metadata["authors"]


def test_arxiv_adapter_acquire_and_normalize():
    adapter = ArxivAdapter()
    cand = CandidateSource(
        url="https://arxiv.org/abs/2602.12345v1",
        platform="arxiv",
        title="Scaling Transformer Architectures Beyond 100M Tokens",
        metadata={
            "arxiv_id": "2602.12345v1",
            "authors": ["Alice Smith", "Bob Jones"],
            "published": "2026-02-14",
            "primary_category": "cs.LG",
            "full_abstract": "We propose a novel sparse attention mechanism that achieves linear time complexity.",
        },
    )

    doc = adapter.acquire(cand, RetrievalRequest())
    assert doc.status == "SUCCESS"
    assert "2602.12345v1" in doc.raw_content
    assert "linear time complexity" in doc.raw_content

    frags = adapter.normalize(doc, cand, RetrievalRequest())
    assert len(frags) == 1
    frag = frags[0]
    assert frag.platform == "arxiv"
    assert "Alice Smith" in frag.author
    assert "linear time complexity" in frag.content
    assert frag.raw_metadata["source_domain"] == "arxiv.org"
