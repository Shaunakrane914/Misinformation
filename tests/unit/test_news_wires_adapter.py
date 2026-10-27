"""Unit tests for NewswireAdapter and UniversalFeedDiscovery."""

from backend.infrastructure.acquisition.adapters.news.feed_discovery import UniversalFeedDiscovery
from backend.infrastructure.acquisition.adapters.news.wires_adapter import NewswireAdapter
from backend.services.agent_reach.channels import (
    CandidateSource,
    FetchedDocument,
    RetrievalRequest,
)


def test_universal_feed_discovery_from_html():
    sample_html = """
    <html>
      <head>
        <link rel="alternate" type="application/rss+xml" title="RSS Feed" href="/custom-rss.xml" />
      </head>
      <body><h1>News Hub</h1></body>
    </html>
    """
    feeds = UniversalFeedDiscovery.discover_feed_urls("https://publisher.example.com/news", sample_html)
    assert "https://publisher.example.com/custom-rss.xml" in feeds


def test_universal_feed_discovery_parse():
    sample_xml = """<?xml version="1.0" encoding="utf-8"?>
    <rss version="2.0">
      <channel>
        <title>Tech Daily</title>
        <link>https://techdaily.example.com</link>
        <description>Daily tech news</description>
        <item>
          <title>Semiconductor Breakthrough Announced</title>
          <link>https://techdaily.example.com/news/1</link>
          <description>Researchers achieve high efficiency computing</description>
          <pubDate>Mon, 24 Oct 2026 12:00:00 GMT</pubDate>
        </item>
      </channel>
    </rss>
    """
    frags = UniversalFeedDiscovery.parse_feed_content(sample_xml, "https://techdaily.example.com/feed")
    assert len(frags) == 1
    f = frags[0]
    assert f.platform == "rss"
    assert "Semiconductor" in f.title
    assert "Researchers achieve" in f.content
    assert f.author == "Tech Daily"


def test_newswire_adapter_can_handle():
    adapter = NewswireAdapter()
    assert adapter.can_handle(CandidateSource(url="https://www.reuters.com/business/finance/article/")) is True
    assert adapter.can_handle(CandidateSource(url="https://apnews.com/article/financial-report")) is True
    assert adapter.can_handle(CandidateSource(url="https://pib.gov.in/PressReleasePage.aspx?PRID=123")) is True
    assert adapter.can_handle(CandidateSource(url="https://random-blog.example.com")) is False


def test_newswire_adapter_normalize():
    adapter = NewswireAdapter()
    cand = CandidateSource(
        url="https://www.reuters.com/business/article-1",
        title="Reuters News Report",
        snippet="Snippet text",
        metadata={"wire": "reuters"},
    )
    doc = FetchedDocument(
        url="https://www.reuters.com/business/article-1",
        status="SUCCESS",
        raw_content="<html><head><title>Official Reuters Dispatch</title></head><body>Full news body text with comprehensive details.</body></html>",
    )
    frags = adapter.normalize(doc, cand, RetrievalRequest())
    assert len(frags) == 1
    f = frags[0]
    assert f.platform == "news"
    assert f.raw_metadata["is_official_wire"] is True
    assert f.raw_metadata["wire"] == "reuters"
